"""DuckDB analytical layer for expected-loss sorting and executive metrics."""

import json
import os
from typing import Any, Dict, List, Optional

import duckdb

DB_PATH = os.getenv("DUCKDB_PATH", "data/claims.duckdb")


def _connect() -> duckdb.DuckDBPyConnection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = duckdb.connect(DB_PATH)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS claims (
            claim_id VARCHAR PRIMARY KEY,
            claim_value_usd DOUBLE,
            denial_probability DOUBLE,
            expected_loss_usd DOUBLE,
            risk_level VARCHAR,
            payer_id VARCHAR,
            icd_10_code VARCHAR,
            cpt_code VARCHAR,
            documentation_complete INTEGER,
            clinical_justification_present INTEGER,
            procedure_mismatch_flag INTEGER,
            patient_chart_notes TEXT,
            agent_correction_draft TEXT,
            explanation TEXT,
            recommended_action VARCHAR,
            confidence DOUBLE,
            missing_elements JSON,
            predicted_denial_codes JSON,
            payer_days_to_pay INTEGER,
            cash_flow_urgency DOUBLE,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return con


def upsert_claim(claim: Dict[str, Any]) -> None:
    con = _connect()
    missing = json.dumps(claim.get("missing_elements") or [])
    codes = json.dumps(claim.get("predicted_denial_codes") or [])
    con.execute(
        """
        INSERT OR REPLACE INTO claims (
            claim_id, claim_value_usd, denial_probability, expected_loss_usd,
            risk_level, payer_id, icd_10_code, cpt_code,
            documentation_complete, clinical_justification_present, procedure_mismatch_flag,
            patient_chart_notes, agent_correction_draft, explanation, recommended_action,
            confidence, missing_elements, predicted_denial_codes,
            payer_days_to_pay, cash_flow_urgency
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            claim["claim_id"],
            claim.get("claim_value_usd", 0),
            claim.get("denial_probability", 0),
            claim.get("expected_loss_usd", 0),
            claim.get("risk_level", "MEDIUM"),
            claim.get("payer_id", ""),
            claim.get("icd_10_code", ""),
            claim.get("cpt_code", ""),
            claim.get("documentation_complete", 1),
            claim.get("clinical_justification_present", 1),
            claim.get("procedure_mismatch_flag", 0),
            claim.get("patient_chart_notes", ""),
            claim.get("agent_correction_draft", ""),
            claim.get("explanation", ""),
            claim.get("recommended_action", ""),
            claim.get("confidence", 0.82),
            missing,
            codes,
            claim.get("payer_days_to_pay", 35),
            claim.get("cash_flow_urgency", 0),
        ],
    )
    con.close()


def clear_claims() -> None:
    con = _connect()
    con.execute("DELETE FROM claims")
    con.close()


def list_claims() -> List[Dict[str, Any]]:
    con = _connect()
    rows = con.execute("SELECT * FROM claims ORDER BY analyzed_at DESC").fetchdf()
    con.close()
    if rows.empty:
        return []
    records = rows.to_dict(orient="records")
    for r in records:
        r["missing_elements"] = json.loads(r["missing_elements"] or "[]")
        r["predicted_denial_codes"] = json.loads(r["predicted_denial_codes"] or "[]")
    return records


def query_priority_queue(
    mode: str = "expected_loss",
    limit: int = 15,
    claim_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    con = _connect()
    order = (
        "cash_flow_urgency DESC"
        if mode == "treasury"
        else "expected_loss_usd DESC"
    )
    if claim_ids:
        placeholders = ", ".join(["?"] * len(claim_ids))
        sql = f"""
            SELECT * FROM claims
            WHERE claim_id IN ({placeholders})
            ORDER BY {order}
            LIMIT ?
        """
        rows = con.execute(sql, claim_ids + [limit]).fetchdf()
    else:
        rows = con.execute(
            f"SELECT * FROM claims ORDER BY {order} LIMIT ?", [limit]
        ).fetchdf()
    con.close()
    if rows.empty:
        return []
    records = rows.to_dict(orient="records")
    for r in records:
        r["missing_elements"] = json.loads(r["missing_elements"] or "[]")
        r["predicted_denial_codes"] = json.loads(r["predicted_denial_codes"] or "[]")
    return records


def get_executive_metrics() -> Dict[str, Any]:
    con = _connect()
    count = con.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    if count == 0:
        con.close()
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
        """
    ).fetchone()

    # Denial code breakdown from JSON arrays
    code_rows = con.execute(
        "SELECT predicted_denial_codes FROM claims WHERE predicted_denial_codes IS NOT NULL"
    ).fetchall()
    code_counts: Dict[str, int] = {}
    for (raw,) in code_rows:
        for code in json.loads(raw or "[]"):
            code_counts[code] = code_counts.get(code, 0) + 1
    denial_breakdown = [
        {"code": k, "count": v} for k, v in sorted(code_counts.items(), key=lambda x: -x[1])
    ]

    payer_rows = con.execute(
        """
        SELECT payer_id,
               AVG(denial_probability) AS avg_prob,
               COUNT(*) AS claim_count
        FROM claims
        GROUP BY payer_id
        ORDER BY avg_prob DESC
        """
    ).fetchdf()
    con.close()

    return {
        "total_claims": int(totals[0]),
        "total_pipeline_liquidity": round(float(totals[1]), 2),
        "predicted_revenue_leakage": round(float(totals[2]), 2),
        "avg_denial_probability": round(float(totals[3]), 3),
        "high_risk_count": int(totals[4]),
        "total_revenue_at_risk": round(float(totals[2]), 2),
        "corrections_generated": count,
        "denial_code_breakdown": denial_breakdown,
        "payer_trends": payer_rows.to_dict(orient="records"),
    }
