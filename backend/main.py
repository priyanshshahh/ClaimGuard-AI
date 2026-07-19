from contextlib import asynccontextmanager

import logging
import math
import os
import uuid
import uvicorn
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent import analyze_clinical_notes, check_payer_policy, generate_appeal_letter
from auth import CurrentUser, get_current_user, require_admin
import store
from carc import attach_carc, map_findings_to_carc
from model import (
    adjust_for_agent_findings,
    explain_claim,
    get_feature_importance,
    get_model_metrics,
    load_model,
    model_is_loaded,
    predict_base_probability,
)
from optimizer import (
    DEFAULT_AUDITOR_CAPACITY,
    PAYER_PAYMENT_SPEED,
    calculate_cash_flow_urgency,
    calculate_expected_loss,
    calculate_expected_recovery,
    get_risk_level,
    prioritize_claims,
)
from schemas import ClaimAnalysisResponse, ClaimInput, PolicyCheckRequest, ResolveClaimRequest

load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("claimguard")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()  # fail fast if trained artifacts are missing
    logger.info("ClaimGuard-AI backend started; model artifacts loaded")
    yield


app = FastAPI(
    title="ClaimGuard-AI API",
    description="Pre-submission claim denial-risk scoring on real CMS CERT data",
    version="3.1.0",
    lifespan=lifespan,
)

# CORS: exact origins come from CORS_ORIGINS (comma-separated); Vercel preview
# deployments are matched via regex because Starlette only exact-matches
# entries in allow_origins (a literal "https://*.vercel.app" never matches).
cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", "")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Last-resort handler: log the failure with the request id for tracing and
    return a generic 500 so internal details never leak to clients."""
    request_id = getattr(request.state, "request_id", "-")
    logger.error(
        "Unhandled error [request_id=%s] on %s %s: %s",
        request_id,
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


api = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


@app.get("/")
async def root():
    return {
        "message": "ClaimGuard-AI API is running",
        "status": "healthy",
        "version": "3.1.0",
        "model": "xgboost + isotonic calibration, trained on CMS CERT 2021-2024",
    }


@app.get("/health")
async def health():
    """Readiness probe: verifies the trained model is loaded and the storage
    backend is reachable. Returns 503 (not 200) when the model is missing so
    orchestrators do not route traffic to a non-functional instance."""
    model_ok = model_is_loaded()
    try:
        store_ok = await run_in_threadpool(store.ping)
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("Health check store ping failed: %s", e)
        store_ok = False

    status_ok = model_ok and store_ok
    payload = {
        "status": "ready" if status_ok else "not_ready",
        "model_loaded": model_ok,
        "store_reachable": store_ok,
    }
    if not model_ok:
        return JSONResponse(status_code=503, content=payload)
    return payload


@app.get("/api/model-info")
async def model_info():
    """Real training metrics from backend/models/metrics.json (no fabrication)."""
    metrics = get_model_metrics()
    if not metrics:
        raise HTTPException(404, "metrics.json not found; run scripts/train.py")
    return metrics


def _analyze_and_store(claim: ClaimInput, user: CurrentUser, is_demo: bool = False) -> ClaimAnalysisResponse:
    try:
        agent_result = analyze_clinical_notes(
            notes=claim.patient_chart_notes,
            icd_code=claim.icd_10_code,
            cpt_code=claim.cpt_code,
        )
    except Exception as e:
        logger.warning("Agent analysis failed, using conservative defaults: %s", e)
        agent_result = {}

    doc = agent_result.get("documentation_complete", 1)
    justification = agent_result.get("clinical_justification_present", 1)
    mismatch = agent_result.get("procedure_mismatch_flag", 0)

    base_prob = predict_base_probability(claim.cpt_code)
    denial_prob = adjust_for_agent_findings(
        base_prob,
        documentation_complete=doc,
        clinical_justification_present=justification,
        procedure_mismatch_flag=mismatch,
    )
    risk_level = get_risk_level(denial_prob)
    expected_loss = calculate_expected_loss(claim.claim_value_usd, denial_prob)
    expected_recovery = calculate_expected_recovery(claim.claim_value_usd, denial_prob)
    payer_days = PAYER_PAYMENT_SPEED.get(claim.payer_id, 35)
    cash_urgency = calculate_cash_flow_urgency(
        claim.claim_value_usd, denial_prob, claim.payer_id
    )
    carc_reasons = map_findings_to_carc(doc, justification, mismatch)
    carc_primary = carc_reasons[0] if carc_reasons else None
    try:
        drivers = explain_claim(claim.cpt_code)
    except Exception as e:
        logger.warning("Driver explanation unavailable: %s", e)
        drivers = []

    response = ClaimAnalysisResponse(
        claim_id=claim.claim_id,
        claim_value_usd=claim.claim_value_usd,
        denial_probability=round(denial_prob, 3),
        model_base_probability=round(base_prob, 4),
        risk_level=risk_level,
        expected_loss_usd=expected_loss,
        documentation_complete=doc,
        clinical_justification_present=justification,
        procedure_mismatch_flag=mismatch,
        agent_correction_draft=agent_result.get("agent_correction_draft", ""),
        explanation=agent_result.get(
            "explanation",
            "Model risk from CMS CERT-trained classifier; agent analysis unavailable.",
        ),
        recommended_action=(
            "Immediate manual review required"
            if risk_level == "HIGH"
            else "Standard processing recommended"
        ),
        confidence=agent_result.get("confidence", 0.5),
        missing_elements=agent_result.get("missing_elements", []),
        predicted_denial_codes=agent_result.get("predicted_denial_codes", []),
        payer_days_to_pay=payer_days,
        cash_flow_urgency=cash_urgency,
        expected_recovery_usd=expected_recovery,
        carc_code=carc_primary["carc_code"] if carc_primary else None,
        carc_group=carc_primary["group_code"] if carc_primary else None,
        cert_category=carc_primary["cert_category"] if carc_primary else None,
        carc_reasons=carc_reasons,
        top_drivers=drivers,
        is_demo=is_demo,
    )

    stored = response.model_dump()
    stored.update(
        {
            "payer_id": claim.payer_id,
            "icd_10_code": claim.icd_10_code,
            "cpt_code": claim.cpt_code,
            "patient_chart_notes": claim.patient_chart_notes,
            "is_demo": is_demo,
        }
    )
    store.upsert_claim(stored, org_id=user.org_id)
    return response





def _coerce_nan(value):
    """Return None for NaN/inf floats so downstream math and JSON stay valid."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _apply_score_mode(claims: list[dict], score_mode: str) -> list[dict]:
    if score_mode != "base":
        return claims
    out = []
    for claim in claims:
        c = dict(claim)
        base = _coerce_nan(c.get("model_base_probability"))
        if base is not None:
            value = _coerce_nan(c.get("claim_value_usd")) or 0
            # In base mode, rank + display on the raw model probability. Keep
            # model_base_probability untouched; surface the ranking probability
            # as denial_probability for display consistency and recompute the
            # expected loss from the base probability.
            c["denial_probability"] = base
            c["ranking_probability"] = base
            c["expected_loss_usd"] = calculate_expected_loss(value, base)
        out.append(c)
    return out


def _score_histogram(claims: list[dict], bins: int = 10) -> list[dict]:
    if not claims:
        return []
    probs = [float(c.get("denial_probability") or 0) for c in claims]
    step = 1.0 / bins
    hist = []
    for i in range(bins):
        lo = round(i * step, 2)
        hi = round((i + 1) * step, 2)
        count = sum(1 for p in probs if (lo <= p < hi) or (i == bins - 1 and p == 1.0))
        hist.append({"bin_start": lo, "bin_end": hi, "count": count})
    return hist


def _enrich_queue_claim(claim: dict) -> dict:
    attach_carc(claim)
    if not claim.get("top_drivers"):
        try:
            claim["top_drivers"] = explain_claim(str(claim.get("cpt_code", "")))
        except Exception:
            claim["top_drivers"] = []
    return claim


@api.post("/analyze-claim", response_model=ClaimAnalysisResponse)
async def analyze_claim(claim: ClaimInput, user: CurrentUser = Depends(get_current_user)):
    return await run_in_threadpool(_analyze_and_store, claim, user, False)



@api.get("/priority-queue")
async def get_priority_queue(
    user: CurrentUser = Depends(get_current_user),
    mode: str = "expected_loss",
    score_mode: str = Query("uplifted", pattern="^(base|uplifted)$"),
    capacity: int = Query(DEFAULT_AUDITOR_CAPACITY, ge=1, le=1000),
    knapsack: bool = True,
):
    active = store.list_claims(org_id=user.org_id)
    if not active:
        return {"claims": [], "message": "No claims analyzed yet", "mode": mode}
    working = _apply_score_mode([dict(c) for c in active], score_mode)
    prioritized = prioritize_claims(
        working,
        mode=mode,
        capacity=capacity if knapsack else None,
    )
    return {
        "claims": [_enrich_queue_claim(c) for c in prioritized[:15]],
        "mode": mode,
        "score_mode": score_mode,
        "auditor_capacity": capacity,
        "knapsack_optimized": knapsack,
    }



@api.get("/me")
async def get_me(user: CurrentUser = Depends(get_current_user)):
    """Return the authenticated principal's identity and tenancy."""
    return {
        "user_id": user.user_id,
        "org_id": user.org_id,
        "role": user.role,
        "email": user.email,
    }


@api.get("/dashboard-metrics")
async def get_dashboard_metrics(user: CurrentUser = Depends(get_current_user)):
    metrics = store.get_executive_metrics(org_id=user.org_id)
    if not metrics:
        return {
            "total_claims": 0,
            "total_pipeline_liquidity": 0,
            "predicted_revenue_leakage": 0,
            "total_revenue_at_risk": 0,
            "high_risk_count": 0,
            "avg_denial_probability": 0,
            "corrections_generated": 0,
            "denial_code_breakdown": [],
            "payer_trends": [],
            "score_histogram": [],
        }
    # Authenticated dashboards get the live per-org score distribution; the
    # public /api/model-health endpoint stays limited to offline metrics.
    metrics["score_histogram"] = _score_histogram(store.list_claims(org_id=user.org_id))
    return metrics



@app.get("/api/model-health")
async def model_health():
    """Public offline model health for the model card (no session required)."""
    metrics = get_model_metrics() or {}
    ops_metrics = metrics.get("ops_metrics")
    feature_importance = metrics.get("feature_importance")
    if not feature_importance:
        try:
            feature_importance = get_feature_importance()
        except Exception as e:
            logger.warning("Feature importance unavailable: %s", e)
            feature_importance = []
    return {
        "score_histogram": [],
        "ops_metrics": ops_metrics,
        "feature_importance": feature_importance,
        "active_claims": 0,
        "note": "Offline metrics from metrics.json.",
    }


# Synthetic demonstration claims. Every claim seeded from here is stored and
# returned with is_demo=true - they are illustrative, not real patients.
DEMO_CLAIMS = [
    {
        "claim_id": "CLM-ORTHO-8821",
        "claim_value_usd": 28450,
        "payer_id": "UHC",
        "icd_10_code": "M17.11",
        "cpt_code": "27447",
        "patient_chart_notes": (
            "67 y/o F with end-stage OA right knee. Severe medial joint space narrowing, "
            "osteophytes, varus deformity. Failed 9 months conservative care including PT, "
            "intra-articular injections, and NSAIDs. Pain 8/10, ambulation limited to <2 blocks. "
            "TKA indicated."
        ),
    },
    {
        "claim_id": "CLM-ONC-3914",
        "claim_value_usd": 187500,
        "payer_id": "AETNA",
        "icd_10_code": "C50.911",
        "cpt_code": "19303",
        "patient_chart_notes": (
            "52 y/o F with newly diagnosed invasive ductal carcinoma left breast, ER/PR+, HER2-. "
            "2.8cm mass on MRI. Multidisciplinary tumor board recommends neoadjuvant chemo "
            "followed by mastectomy with sentinel node biopsy. Pre-authorization requested."
        ),
    },
    {
        "claim_id": "CLM-CARD-7742",
        "claim_value_usd": 92500,
        "payer_id": "MEDICARE",
        "icd_10_code": "I25.10",
        "cpt_code": "93458",
        "patient_chart_notes": (
            "71 y/o M with progressive angina, positive stress test showing reversible ischemia "
            "in LAD territory. Cardiac cath recommended for further evaluation and possible PCI. "
            "History of diabetes and prior NSTEMI 2019."
        ),
    },
    {
        "claim_id": "CLM-SPINE-5529",
        "claim_value_usd": 67300,
        "payer_id": "BCBS",
        "icd_10_code": "M54.16",
        "cpt_code": "63030",
        "patient_chart_notes": (
            "48 y/o M with 14-month history of right L5 radiculopathy. MRI demonstrates large "
            "right paracentral disc herniation at L4-5 with foraminal stenosis. Failed epidural "
            "injections x2, PT, and gabapentin. Microdiscectomy indicated."
        ),
    },
    {
        "claim_id": "CLM-EM-99214",
        "claim_value_usd": 285,
        "payer_id": "UHC",
        "icd_10_code": "E11.9",
        "cpt_code": "99214",
        "patient_chart_notes": (
            "45 y/o M with type 2 diabetes follow-up. Reviewed labs. Adjusted metformin dose. "
            "Brief visit, no time documented."
        ),
    },
    {
        "claim_id": "CLM-GEN-1187",
        "claim_value_usd": 12400,
        "payer_id": "MEDICAID",
        "icd_10_code": "K40.90",
        "cpt_code": "49505",
        "patient_chart_notes": (
            "34 y/o M with symptomatic right inguinal hernia, reducible but painful with heavy "
            "lifting at warehouse job. No prior abdominal surgery. Open hernia repair with mesh "
            "recommended."
        ),
    },
]


@api.post("/seed-demo")
async def seed_demo_data(
    scenario: str = "default",
    user: CurrentUser = Depends(require_admin),
):
    # Only clear previously-seeded demo claims so real analyzed claims survive
    # a re-seed. Demo rows are labeled is_demo=true.
    store.clear_demo_claims(org_id=user.org_id)
    claims_to_add = DEMO_CLAIMS.copy()
    if scenario == "high-risk":
        claims_to_add = [c for c in DEMO_CLAIMS if c["claim_value_usd"] > 50000]
    seeded = []
    for claim_data in claims_to_add:
        seeded.append(
            await run_in_threadpool(_analyze_and_store, ClaimInput(**claim_data), user, True)
        )
    total_risk = round(sum(c.expected_loss_usd for c in seeded), 2)
    return {
        "seeded": len(seeded),
        "total_revenue_at_risk": total_risk,
        "is_demo": True,
        "message": "Synthetic demo claims loaded (labeled is_demo=true).",
    }



@api.post("/resolve-claim")
async def resolve_claim_endpoint(
    body: ResolveClaimRequest,
    user: CurrentUser = Depends(get_current_user),
):
    if not store.resolve_claim(body.claim_id, org_id=user.org_id, resolved_by=user.user_id):
        raise HTTPException(404, "Claim not found in current session")
    return {"claim_id": body.claim_id, "resolved": True}



@api.post("/clear-queue")
async def clear_queue(user: CurrentUser = Depends(require_admin)):
    store.clear_claims(org_id=user.org_id)
    return {"message": "Queue cleared", "total_claims": 0}



@api.post("/generate-appeal")
async def create_appeal(
    claim_id: str,
    user: CurrentUser = Depends(get_current_user),
    denial_reason: str = "Medical necessity not established",
):
    claim = store.get_claim(claim_id, org_id=user.org_id)
    if not claim:
        raise HTTPException(404, "Claim not found in current session")
    appeal = await run_in_threadpool(
        generate_appeal_letter,
        claim,
        {"explanation": claim.get("explanation", "")},
        denial_reason,
    )
    return {"claim_id": claim_id, **appeal}



@api.post("/check-policy")
async def policy_check(
    body: PolicyCheckRequest,
    user: CurrentUser = Depends(get_current_user),
):
    claim_id = body.claim_id
    icd, cpt, payer, notes = body.icd, body.cpt, body.payer, body.notes
    if claim_id:
        claim = store.get_claim(claim_id, org_id=user.org_id)
        if not claim:
            raise HTTPException(404, "Claim not found")
        icd, cpt, payer, notes = (
            claim["icd_10_code"],
            claim["cpt_code"],
            claim["payer_id"],
            claim.get("patient_chart_notes", ""),
        )
    elif not all([icd, cpt, payer, notes]):
        raise HTTPException(400, "Provide either claim_id or full icd/cpt/payer/notes")
    return await run_in_threadpool(check_payer_policy, notes or "", icd, cpt, payer)



@api.post("/fhir/claim")
async def fhir_endpoint(payload: dict, user: CurrentUser = Depends(get_current_user)):
    del user
    try:
        mapped = {
            "resourceType": "Claim",
            "id": payload.get("id", "demo-claim"),
            "status": "active",
            "type": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/claim-type",
                        "code": "institutional",
                    }
                ]
            },
            "patient": {"reference": f"Patient/{payload.get('patient_id', 'unknown')}"},
            "created": payload.get("created", ""),
            "provider": {"reference": "Organization/our-hospital"},
            "item": [
                {
                    "sequence": 1,
                    "productOrService": {
                        "coding": [
                            {
                                "system": "http://www.ama-assn.org/go/cpt",
                                "code": payload.get("cpt", "00000"),
                            }
                        ]
                    },
                    "net": {"value": payload.get("total", 0), "currency": "USD"},
                }
            ],
        }
        return {
            "demo": True,
            "fhir_claim": mapped,
            "note": (
                "Structure-mapping demo only; POST /api/analyze-claim with clinical "
                "notes to run the scoring pipeline."
            ),
        }
    except Exception as e:
        raise HTTPException(400, f"Invalid FHIR payload: {str(e)}")



@api.get("/treasury-priority")
async def treasury_priority(user: CurrentUser = Depends(get_current_user)):
    active = store.list_claims(org_id=user.org_id)
    if not active:
        return {"claims": [], "mode": "treasury"}
    prioritized = prioritize_claims([dict(c) for c in active], mode="treasury")
    return {
        "claims": [_enrich_queue_claim(c) for c in prioritized[:12]],
        "mode": "treasury",
        "description": "Prioritized by risk + payer payment speed (cash flow urgency)",
    }



app.include_router(api)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
