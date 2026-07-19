"""PostgreSQL claims store (org-scoped). Mirrors duckdb_store API."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required when STORAGE_BACKEND=postgres")
    return url


def _connect() -> psycopg.Connection:
    return psycopg.connect(_database_url(), row_factory=dict_row)


def _normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(record)
    for key in ("missing_elements", "predicted_denial_codes"):
        val = out.get(key)
        if isinstance(val, str):
            out[key] = json.loads(val or "[]")
        elif val is None:
            out[key] = []
    return out


def upsert_claim(claim: Dict[str, Any], org_id: str) -> None:
    missing = claim.get("missing_elements") or []
    codes = claim.get("predicted_denial_codes") or []
    with _connect() as con:
        con.execute(
            """
            INSERT INTO claims (
                org_id, claim_id, claim_value_usd, denial_probability, expected_loss_usd,
                risk_level, payer_id, icd_10_code, cpt_code,
                documentation_complete, clinical_justification_present, procedure_mismatch_flag,
                patient_chart_notes, agent_correction_draft, explanation, recommended_action,
                confidence, missing_elements, predicted_denial_codes,
                payer_days_to_pay, cash_flow_urgency, model_base_probability, is_demo, resolved
            ) VALUES (
                %(org_id)s, %(claim_id)s, %(claim_value_usd)s, %(denial_probability)s,
                %(expected_loss_usd)s, %(risk_level)s, %(payer_id)s, %(icd_10_code)s,
                %(cpt_code)s, %(documentation_complete)s, %(clinical_justification_present)s,
                %(procedure_mismatch_flag)s, %(patient_chart_notes)s, %(agent_correction_draft)s,
                %(explanation)s, %(recommended_action)s, %(confidence)s,
                %(missing_elements)s::jsonb, %(predicted_denial_codes)s::jsonb,
                %(payer_days_to_pay)s, %(cash_flow_urgency)s, %(model_base_probability)s,
                %(is_demo)s, %(resolved)s
            )
            ON CONFLICT (org_id, claim_id) DO UPDATE SET
                claim_value_usd = EXCLUDED.claim_value_usd,
                denial_probability = EXCLUDED.denial_probability,
                expected_loss_usd = EXCLUDED.expected_loss_usd,
                risk_level = EXCLUDED.risk_level,
                payer_id = EXCLUDED.payer_id,
                icd_10_code = EXCLUDED.icd_10_code,
                cpt_code = EXCLUDED.cpt_code,
                documentation_complete = EXCLUDED.documentation_complete,
                clinical_justification_present = EXCLUDED.clinical_justification_present,
                procedure_mismatch_flag = EXCLUDED.procedure_mismatch_flag,
                patient_chart_notes = EXCLUDED.patient_chart_notes,
                agent_correction_draft = EXCLUDED.agent_correction_draft,
                explanation = EXCLUDED.explanation,
                recommended_action = EXCLUDED.recommended_action,
                confidence = EXCLUDED.confidence,
                missing_elements = EXCLUDED.missing_elements,
                predicted_denial_codes = EXCLUDED.predicted_denial_codes,
                payer_days_to_pay = EXCLUDED.payer_days_to_pay,
                cash_flow_urgency = EXCLUDED.cash_flow_urgency,
                model_base_probability = EXCLUDED.model_base_probability,
                is_demo = EXCLUDED.is_demo,
                resolved = EXCLUDED.resolved,
                analyzed_at = now()
            """,
            {
                "org_id": org_id,
                "claim_id": claim["claim_id"],
                "claim_value_usd": claim.get("claim_value_usd", 0),
                "denial_probability": claim.get("denial_probability", 0),
                "expected_loss_usd": claim.get("expected_loss_usd", 0),
                "risk_level": claim.get("risk_level", "MEDIUM"),
                "payer_id": claim.get("payer_id", ""),
                "icd_10_code": claim.get("icd_10_code", ""),
                "cpt_code": claim.get("cpt_code", ""),
                "documentation_complete": claim.get("documentation_complete", 1),
                "clinical_justification_present": claim.get("clinical_justification_present", 1),
                "procedure_mismatch_flag": claim.get("procedure_mismatch_flag", 0),
                "patient_chart_notes": claim.get("patient_chart_notes", ""),
                "agent_correction_draft": claim.get("agent_correction_draft", ""),
                "explanation": claim.get("explanation", ""),
                "recommended_action": claim.get("recommended_action", ""),
                "confidence": claim.get("confidence", 0.82),
                "missing_elements": json.dumps(missing),
                "predicted_denial_codes": json.dumps(codes),
                "payer_days_to_pay": claim.get("payer_days_to_pay", 35),
                "cash_flow_urgency": claim.get("cash_flow_urgency", 0),
                "model_base_probability": claim.get("model_base_probability"),
                "is_demo": bool(claim.get("is_demo", False)),
                "resolved": bool(claim.get("resolved", False)),
            },
        )
        con.commit()


def resolve_claim(
    claim_id: str,
    org_id: str,
    resolved_by: Optional[str] = None,
) -> bool:
    with _connect() as con:
        row = con.execute(
            "SELECT 1 FROM claims WHERE org_id = %s AND claim_id = %s",
            (org_id, claim_id),
        ).fetchone()
        if not row:
            return False
        con.execute(
            """
            UPDATE claims
            SET resolved = TRUE, resolved_at = now(), resolved_by = %s
            WHERE org_id = %s AND claim_id = %s
            """,
            (resolved_by, org_id, claim_id),
        )
        con.commit()
    return True


def get_claim(claim_id: str, org_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as con:
        row = con.execute(
            "SELECT * FROM claims WHERE org_id = %s AND claim_id = %s",
            (org_id, claim_id),
        ).fetchone()
    if not row:
        return None
    return _normalize_record(row)


def clear_claims(org_id: str) -> None:
    with _connect() as con:
        con.execute("DELETE FROM claims WHERE org_id = %s", (org_id,))
        con.commit()


def clear_demo_claims(org_id: str) -> None:
    """Delete only synthetic demo claims for an org, leaving real analyzed
    claims intact."""
    with _connect() as con:
        con.execute(
            "DELETE FROM claims WHERE org_id = %s AND is_demo = TRUE",
            (org_id,),
        )
        con.commit()


def list_claims(org_id: str) -> List[Dict[str, Any]]:
    with _connect() as con:
        rows = con.execute(
            """
            SELECT * FROM claims
            WHERE org_id = %s AND resolved = FALSE
            ORDER BY analyzed_at DESC
            """,
            (org_id,),
        ).fetchall()
    return [_normalize_record(r) for r in rows]


def get_executive_metrics(org_id: str) -> Dict[str, Any]:
    with _connect() as con:
        count = con.execute(
            "SELECT COUNT(*) AS n FROM claims WHERE org_id = %s AND resolved = FALSE",
            (org_id,),
        ).fetchone()["n"]
        if count == 0:
            return {}

        totals = con.execute(
            """
            SELECT
                COUNT(*) AS total_claims,
                COALESCE(SUM(claim_value_usd), 0) AS total_pipeline_liquidity,
                COALESCE(SUM(expected_loss_usd), 0) AS predicted_revenue_leakage,
                COALESCE(AVG(denial_probability), 0) AS avg_denial_probability,
                SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_count
            FROM claims
            WHERE org_id = %s AND resolved = FALSE
            """,
            (org_id,),
        ).fetchone()

        code_rows = con.execute(
            """
            SELECT predicted_denial_codes FROM claims
            WHERE org_id = %s AND resolved = FALSE AND predicted_denial_codes IS NOT NULL
            """,
            (org_id,),
        ).fetchall()
        code_counts: Dict[str, int] = {}
        for row in code_rows:
            codes = row["predicted_denial_codes"]
            if isinstance(codes, str):
                codes = json.loads(codes or "[]")
            for code in codes or []:
                code_counts[code] = code_counts.get(code, 0) + 1
        denial_breakdown = [
            {"code": k, "count": v}
            for k, v in sorted(code_counts.items(), key=lambda x: -x[1])
        ]

        payer_rows = con.execute(
            """
            SELECT payer_id,
                   AVG(denial_probability) AS avg_prob,
                   COUNT(*) AS claim_count
            FROM claims
            WHERE org_id = %s AND resolved = FALSE
            GROUP BY payer_id
            ORDER BY avg_prob DESC
            """,
            (org_id,),
        ).fetchall()

    return {
        "total_claims": int(totals["total_claims"]),
        "total_pipeline_liquidity": round(float(totals["total_pipeline_liquidity"]), 2),
        "predicted_revenue_leakage": round(float(totals["predicted_revenue_leakage"]), 2),
        "avg_denial_probability": round(float(totals["avg_denial_probability"]), 3),
        "high_risk_count": int(totals["high_risk_count"]),
        "total_revenue_at_risk": round(float(totals["predicted_revenue_leakage"]), 2),
        "corrections_generated": count,
        "denial_code_breakdown": denial_breakdown,
        "payer_trends": [dict(r) for r in payer_rows],
    }
