"""DuckDB analytical layer for expected-loss sorting and executive metrics."""

import json
import os
from typing import Any, Dict, List, Optional

import duckdb

def _db_path() -> str:
    # resolved per-call so tests can point DUCKDB_PATH at a temp file
    return os.getenv("DUCKDB_PATH", "data/claims.duckdb")


def _connect() -> duckdb.DuckDBPyConnection:
    db_path = _db_path()
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    con = duckdb.connect(db_path)
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
            model_base_probability DOUBLE,
            is_demo BOOLEAN DEFAULT FALSE,
            resolved BOOLEAN DEFAULT FALSE,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Migrate pre-existing local DBs. Guarded by an explicit column check:
    # re-running ADD COLUMN IF NOT EXISTS ... DEFAULT on DuckDB resets the
    # existing column values to the default on reconnect.
    existing = {r[1] for r in con.execute("PRAGMA table_info('claims')").fetchall()}
    if "model_base_probability" not in existing:
        con.execute("ALTER TABLE claims ADD COLUMN model_base_probability DOUBLE")
    if "is_demo" not in existing:
        con.execute("ALTER TABLE claims ADD COLUMN is_demo BOOLEAN DEFAULT FALSE")
    if "resolved" not in existing:
        con.execute("ALTER TABLE claims ADD COLUMN resolved BOOLEAN DEFAULT FALSE")
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
            payer_days_to_pay, cash_flow_urgency, model_base_probability, is_demo, resolved
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            claim.get("model_base_probability"),
            bool(claim.get("is_demo", False)),
            bool(claim.get("resolved", False)),
        ],
    )
    con.close()


def resolve_claim(claim_id: str) -> bool:
    """Mark a claim resolved (removed from the active worklist). Returns
    False if the claim does not exist."""
    con = _connect()
    exists = con.execute(
        "SELECT 1 FROM claims WHERE claim_id = ?", [claim_id]
    ).fetchone()
    if not exists:
        con.close()
        return False
    con.execute("UPDATE claims SET resolved = TRUE WHERE claim_id = ?", [claim_id])
    con.close()
    return True


def get_claim(claim_id: str) -> Optional[Dict[str, Any]]:
    con = _connect()
    rows = con.execute(
        "SELECT * FROM claims WHERE claim_id = ?", [claim_id]
    ).fetchdf()
    con.close()
    if rows.empty:
        return None
    record = rows.to_dict(orient="records")[0]
    record["missing_elements"] = json.loads(record["missing_elements"] or "[]")
    record["predicted_denial_codes"] = json.loads(record["predicted_denial_codes"] or "[]")
    return record


def clear_claims() -> None:
    con = _connect()
    con.execute("DELETE FROM claims")
    con.close()


def list_claims() -> List[Dict[str, Any]]:
    con = _connect()
    rows = con.execute(
        "SELECT * FROM claims WHERE resolved = FALSE ORDER BY analyzed_at DESC"
    ).fetchdf()
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
    count = con.execute(
        "SELECT COUNT(*) FROM claims WHERE resolved = FALSE"
    ).fetchone()[0]
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
        WHERE resolved = FALSE
        """
    ).fetchone()

    # Denial code breakdown from JSON arrays
    code_rows = con.execute(
        "SELECT predicted_denial_codes FROM claims "
        "WHERE resolved = FALSE AND predicted_denial_codes IS NOT NULL"
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
        WHERE resolved = FALSE
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
