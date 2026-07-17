from contextlib import asynccontextmanager

import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from agent import analyze_clinical_notes, check_payer_policy, generate_appeal_letter
from duckdb_store import (
    clear_claims,
    get_claim,
    get_executive_metrics,
    list_claims,
    resolve_claim,
    upsert_claim,
)
from carc import attach_carc, map_findings_to_carc
from model import (
    adjust_for_agent_findings,
    explain_claim,
    get_model_metrics,
    load_model,
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
from schemas import ClaimAnalysisResponse, ClaimInput, PolicyCheckRequest

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()  # fail fast if trained artifacts are missing
    print("ClaimGuard-AI backend started; model artifacts loaded")
    yield


app = FastAPI(
    title="ClaimGuard-AI API",
    description="Pre-submission claim denial-risk scoring on real CMS CERT data",
    version="3.0.0",
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
cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "ClaimGuard-AI API is running",
        "status": "healthy",
        "version": "3.0.0",
        "model": "xgboost + isotonic calibration, trained on CMS CERT 2021-2024",
    }


@app.get("/api/model-info")
async def model_info():
    """Real training metrics from backend/models/metrics.json (no fabrication)."""
    metrics = get_model_metrics()
    if not metrics:
        raise HTTPException(404, "metrics.json not found; run scripts/train.py")
    return metrics


def _analyze_and_store(claim: ClaimInput, is_demo: bool = False) -> ClaimAnalysisResponse:
    try:
        agent_result = analyze_clinical_notes(
            notes=claim.patient_chart_notes,
            icd_code=claim.icd_10_code,
            cpt_code=claim.cpt_code,
        )
    except Exception as e:
        print(f"Agent analysis failed, using conservative defaults: {e}")
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
        print(f"Driver explanation unavailable: {e}")
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
    upsert_claim(stored)
    return response


@app.post("/api/analyze-claim", response_model=ClaimAnalysisResponse)
async def analyze_claim(claim: ClaimInput):
    # _analyze_and_store makes a blocking LLM call; run it off the event loop
    # so one slow provider can't stall other concurrent requests.
    return await run_in_threadpool(_analyze_and_store, claim, False)


def _enrich_queue_claim(claim: dict) -> dict:
    """Add derived CARC codes + top model drivers to a stored claim on read."""
    attach_carc(claim)
    if not claim.get("top_drivers"):
        try:
            claim["top_drivers"] = explain_claim(str(claim.get("cpt_code", "")))
        except Exception:
            claim["top_drivers"] = []
    return claim


@app.get("/api/priority-queue")
async def get_priority_queue(
    mode: str = "expected_loss",
    capacity: int = DEFAULT_AUDITOR_CAPACITY,
    knapsack: bool = True,
):
    active = list_claims()
    if not active:
        return {"claims": [], "message": "No claims analyzed yet", "mode": mode}

    prioritized = prioritize_claims(
        [dict(c) for c in active],
        mode=mode,
        capacity=capacity if knapsack else None,
    )
    return {
        "claims": [_enrich_queue_claim(c) for c in prioritized[:15]],
        "mode": mode,
        "auditor_capacity": capacity,
        "knapsack_optimized": knapsack,
    }


@app.get("/api/dashboard-metrics")
async def get_dashboard_metrics():
    metrics = get_executive_metrics()
    if metrics:
        return metrics
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


@app.post("/api/seed-demo")
async def seed_demo_data(scenario: str = "default"):
    clear_claims()

    claims_to_add = DEMO_CLAIMS.copy()
    if scenario == "high-risk":
        claims_to_add = [c for c in DEMO_CLAIMS if c["claim_value_usd"] > 50000]

    seeded = []
    for claim_data in claims_to_add:
        seeded.append(
            await run_in_threadpool(_analyze_and_store, ClaimInput(**claim_data), True)
        )

    total_risk = round(sum(c.expected_loss_usd for c in seeded), 2)
    return {
        "seeded": len(seeded),
        "total_revenue_at_risk": total_risk,
        "is_demo": True,
        "message": "Synthetic demo claims loaded (labeled is_demo=true).",
    }


@app.post("/api/resolve-claim")
async def resolve_claim_endpoint(claim_id: str):
    """Mark a claim resolved so it drops out of the active worklist and
    metrics. Persists to DuckDB (unlike the old client-only 'Resolve')."""
    if not resolve_claim(claim_id):
        raise HTTPException(404, "Claim not found in current session")
    return {"claim_id": claim_id, "resolved": True}


@app.post("/api/clear-queue")
async def clear_queue():
    clear_claims()
    return {"message": "Queue cleared", "total_claims": 0}


@app.post("/api/generate-appeal")
async def create_appeal(claim_id: str, denial_reason: str = "Medical necessity not established"):
    claim = get_claim(claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found in current session")

    appeal = await run_in_threadpool(
        generate_appeal_letter,
        claim,
        {"explanation": claim.get("explanation", "")},
        denial_reason,
    )
    return {"claim_id": claim_id, **appeal}


@app.post("/api/check-policy")
async def policy_check(body: PolicyCheckRequest):
    claim_id = body.claim_id
    icd, cpt, payer, notes = body.icd, body.cpt, body.payer, body.notes
    if claim_id:
        claim = get_claim(claim_id)
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


@app.post("/api/fhir/claim")
async def fhir_endpoint(payload: dict):
    """Map a minimal FHIR R4 Claim shape to our internal fields.

    Demo-only mapper: it validates/echoes structure and shows how a FHIR
    integration would feed /api/analyze-claim. It does not run the ML or
    agent pipeline (FHIR Claim resources carry no chart notes).
    """
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


@app.get("/api/treasury-priority")
async def treasury_priority():
    active = list_claims()
    if not active:
        return {"claims": [], "mode": "treasury"}
    prioritized = prioritize_claims([dict(c) for c in active], mode="treasury")
    return {
        "claims": [_enrich_queue_claim(c) for c in prioritized[:12]],
        "mode": "treasury",
        "description": "Prioritized by risk + payer payment speed (cash flow urgency)",
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
