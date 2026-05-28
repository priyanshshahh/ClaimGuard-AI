from contextlib import asynccontextmanager
from typing import Dict, List

import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent import analyze_clinical_notes, check_payer_policy, generate_appeal_letter
from duckdb_store import (
    clear_claims,
    get_executive_metrics,
    list_claims,
    query_priority_queue,
    upsert_claim,
)
from model import load_model, predict_denial_probability
from optimizer import (
    DEFAULT_AUDITOR_CAPACITY,
    PAYER_PAYMENT_SPEED,
    calculate_cash_flow_urgency,
    calculate_expected_loss,
    get_risk_level,
    prioritize_claims,
)
from schemas import ClaimAnalysisResponse, ClaimInput, PolicyCheckRequest

load_dotenv()

claims_db: List[Dict] = []


def _build_features(claim: ClaimInput, agent_result: dict) -> dict:
    doc = agent_result.get("documentation_complete", 1)
    mismatch = agent_result.get("procedure_mismatch_flag", 0)
    justification = agent_result.get("clinical_justification_present", 1)
    return {
        "claim_value_usd": claim.claim_value_usd,
        "payer_id": claim.payer_id,
        "icd_risk": 0.65 if doc == 0 else 0.25,
        "cpt_risk": 0.75 if mismatch == 1 else 0.25,
        "documentation_complete": doc,
        "clinical_justification_present": justification,
        "procedure_mismatch_flag": mismatch,
    }


def _store_claim(stored: Dict) -> None:
    claims_db.append(stored)
    upsert_claim(stored)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    print("ClaimGuard-AI Backend started successfully")
    yield


app = FastAPI(
    title="ClaimGuard-AI API",
    description="Agentic Pre-Submission Revenue Protection Platform",
    version="2.0.0",
    lifespan=lifespan,
)

cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,https://*.vercel.app",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "ClaimGuard-AI API is running", "status": "healthy", "version": "2.0.0", "llm": "nebius-token-factory"}


@app.post("/api/analyze-claim", response_model=ClaimAnalysisResponse)
async def analyze_claim(claim: ClaimInput):
    try:
        agent_result = analyze_clinical_notes(
            notes=claim.patient_chart_notes,
            icd_code=claim.icd_10_code,
            cpt_code=claim.cpt_code,
        )

        features = _build_features(claim, agent_result)
        denial_prob = predict_denial_probability(features)
        risk_level = get_risk_level(denial_prob)
        expected_loss = calculate_expected_loss(claim.claim_value_usd, denial_prob)
        payer_days = PAYER_PAYMENT_SPEED.get(claim.payer_id, 35)
        cash_urgency = calculate_cash_flow_urgency(
            claim.claim_value_usd, denial_prob, claim.payer_id
        )
        mismatch = agent_result.get("procedure_mismatch_flag", 0)

        response = ClaimAnalysisResponse(
            claim_id=claim.claim_id,
            claim_value_usd=claim.claim_value_usd,
            denial_probability=round(denial_prob, 3),
            risk_level=risk_level,
            expected_loss_usd=expected_loss,
            documentation_complete=agent_result.get("documentation_complete", 1),
            clinical_justification_present=agent_result.get(
                "clinical_justification_present", 1
            ),
            procedure_mismatch_flag=mismatch,
            procedure_mismatch=mismatch,
            agent_correction_draft=agent_result.get("agent_correction_draft", ""),
            explanation=agent_result.get("explanation", ""),
            recommended_action=(
                "Immediate manual review required"
                if risk_level == "HIGH"
                else "Standard processing recommended"
            ),
            confidence=agent_result.get("confidence", 0.82),
            missing_elements=agent_result.get("missing_elements", []),
            predicted_denial_codes=agent_result.get("predicted_denial_codes", []),
            payer_days_to_pay=payer_days,
            cash_flow_urgency=cash_urgency,
        )

        stored = response.model_dump()
        stored.update(
            {
                "payer_id": claim.payer_id,
                "icd_10_code": claim.icd_10_code,
                "cpt_code": claim.cpt_code,
                "patient_chart_notes": claim.patient_chart_notes,
            }
        )
        _store_claim(stored)
        return response

    except Exception as e:
        print(f"Analysis fallback triggered: {str(e)}")
        fallback = ClaimAnalysisResponse(
            claim_id=claim.claim_id,
            claim_value_usd=claim.claim_value_usd,
            denial_probability=0.55,
            risk_level="MEDIUM",
            expected_loss_usd=round(claim.claim_value_usd * 0.55, 2),
            documentation_complete=0,
            clinical_justification_present=0,
            procedure_mismatch_flag=0,
            procedure_mismatch=0,
            agent_correction_draft=(
                "Additional clinical documentation is recommended to support medical necessity."
            ),
            explanation="Automated analysis encountered an issue. Manual review advised.",
            recommended_action="Standard processing recommended",
            confidence=0.55,
            missing_elements=["Full clinical rationale", "Prior authorization details"],
            predicted_denial_codes=["CO-16"],
            payer_days_to_pay=PAYER_PAYMENT_SPEED.get(claim.payer_id, 35),
            cash_flow_urgency=0.0,
        )
        stored = fallback.model_dump()
        stored.update(
            {
                "payer_id": claim.payer_id,
                "icd_10_code": claim.icd_10_code,
                "cpt_code": claim.cpt_code,
                "patient_chart_notes": claim.patient_chart_notes,
            }
        )
        _store_claim(stored)
        return fallback


@app.get("/api/priority-queue")
async def get_priority_queue(
    mode: str = "expected_loss",
    capacity: int = DEFAULT_AUDITOR_CAPACITY,
    knapsack: bool = True,
):
    active = list_claims() or claims_db
    if not active:
        return {"claims": [], "message": "No claims analyzed yet", "mode": mode}

    prioritized = prioritize_claims(
        [dict(c) for c in active],
        mode=mode,
        capacity=capacity if knapsack else None,
    )
    if knapsack:
        selected_ids = query_priority_queue(mode=mode, limit=capacity)
        selected_set = {c["claim_id"] for c in selected_ids} if selected_ids else set()
        for c in prioritized:
            c["knapsack_selected"] = c["claim_id"] in selected_set or c.get(
                "knapsack_selected", False
            )

    return {
        "claims": prioritized[:15],
        "mode": mode,
        "auditor_capacity": capacity,
        "knapsack_optimized": knapsack,
    }


@app.get("/api/dashboard-metrics")
async def get_dashboard_metrics():
    metrics = get_executive_metrics()
    if metrics:
        return metrics

    if not claims_db:
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

    total_liquidity = sum(c["claim_value_usd"] for c in claims_db)
    total_leakage = sum(c["expected_loss_usd"] for c in claims_db)
    return {
        "total_claims": len(claims_db),
        "total_pipeline_liquidity": round(total_liquidity, 2),
        "predicted_revenue_leakage": round(total_leakage, 2),
        "total_revenue_at_risk": round(total_leakage, 2),
        "high_risk_count": len([c for c in claims_db if c["risk_level"] == "HIGH"]),
        "avg_denial_probability": round(
            sum(c["denial_probability"] for c in claims_db) / len(claims_db), 3
        ),
        "corrections_generated": len(
            [c for c in claims_db if c.get("agent_correction_draft")]
        ),
        "denial_code_breakdown": [],
        "payer_trends": [],
    }


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
    global claims_db
    claims_db = []
    clear_claims()

    claims_to_add = DEMO_CLAIMS.copy()
    if scenario == "high-risk":
        claims_to_add = [c for c in DEMO_CLAIMS if c["claim_value_usd"] > 50000]

    for claim_data in claims_to_add:
        claim = ClaimInput(**claim_data)
        await analyze_claim(claim)

    total_risk = sum(c["expected_loss_usd"] for c in claims_db)
    return {
        "seeded": len(claims_db),
        "total_revenue_at_risk": total_risk,
        "message": "Demo claims loaded successfully. Ready for pitch.",
    }


@app.post("/api/clear-queue")
async def clear_queue():
    global claims_db
    claims_db = []
    clear_claims()
    return {"message": "Queue cleared", "total_claims": 0}


@app.post("/api/generate-appeal")
async def create_appeal(claim_id: str, denial_reason: str = "Medical necessity not established"):
    active = list_claims() or claims_db
    claim = next((c for c in active if c["claim_id"] == claim_id), None)
    if not claim:
        raise HTTPException(404, "Claim not found in current session")

    appeal = generate_appeal_letter(
        claim_data=claim,
        original_analysis={"explanation": claim.get("explanation", "")},
        denial_reason=denial_reason,
    )
    return {"claim_id": claim_id, **appeal}


@app.post("/api/check-policy")
async def policy_check(body: PolicyCheckRequest):
    claim_id = body.claim_id
    icd, cpt, payer, notes = body.icd, body.cpt, body.payer, body.notes
    if claim_id:
        active = list_claims() or claims_db
        claim = next((c for c in active if c["claim_id"] == claim_id), None)
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

    return check_payer_policy(notes or "", icd, cpt, payer)


@app.post("/api/fhir/claim")
async def fhir_endpoint(payload: dict):
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
            "created": payload.get("created", "2026-05-28"),
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
            "fhir_claim": mapped,
            "claimguard_analysis": {
                "message": (
                    "FHIR payload accepted. In production this would trigger full agentic + ML pipeline."
                ),
                "recommendation": (
                    "Use /api/analyze-claim with enriched clinical data for full intelligence."
                ),
            },
        }
    except Exception as e:
        raise HTTPException(400, f"Invalid FHIR payload: {str(e)}")


@app.get("/api/treasury-priority")
async def treasury_priority():
    active = list_claims() or claims_db
    if not active:
        return {"claims": [], "mode": "treasury"}
    prioritized = prioritize_claims([dict(c) for c in active], mode="treasury")
    return {
        "claims": prioritized[:12],
        "mode": "treasury",
        "description": "Prioritized by risk + payer payment speed (cash flow urgency)",
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
