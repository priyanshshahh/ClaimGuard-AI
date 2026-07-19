"""DuckDB analytical layer for expected-loss sorting and executive metrics.

Org scoping: DuckDB is the single-tenant local/CI backend. `org_id` is stored
and, when a caller passes one, used to filter reads/writes so behaviour matches
the multi-tenant Postgres backend. When `org_id` is None (e.g. AUTH_DISABLED or
direct unit tests) no org filter is applied.
"""

import json
import math
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
            org_id VARCHAR,
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
    if "org_id" not in existing:
        con.execute("ALTER TABLE claims ADD COLUMN org_id VARCHAR")
    if "model_base_probability" not in existing:
        con.execute("ALTER TABLE claims ADD COLUMN model_base_probability DOUBLE")
    if "is_demo" not in existing:
        con.execute("ALTER TABLE claims ADD COLUMN is_demo BOOLEAN DEFAULT FALSE")
    if "resolved" not in existing:
        con.execute("ALTER TABLE claims ADD COLUMN resolved BOOLEAN DEFAULT FALSE")
    return con


def _native(value: Any) -> Any:
    """Coerce numpy scalars (from pandas .to_dict) to native Python types and
    turn NaN into None so JSON serialization and arithmetic stay safe."""
    if value is None:
        return None
    if hasattr(value, "item"):  # numpy scalar -> python scalar
        try:
            value = value.item()
        except (ValueError, TypeError):
            return value
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _row_to_record(record: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: _native(v) for k, v in record.items()}
    out["missing_elements"] = json.loads(out.get("missing_elements") or "[]")
    out["predicted_denial_codes"] = json.loads(out.get("predicted_denial_codes") or "[]")
    return out


def _org_clause(org_id: Optional[str], extra: str = "") -> tuple[str, list]:
    """Build a WHERE clause fragment + params, appending an org filter only when
    an org_id is supplied."""
    clauses = []
    params: list = []
    if extra:
        clauses.append(extra)
    if org_id is not None:
        clauses.append("org_id = ?")
        params.append(org_id)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def upsert_claim(claim: Dict[str, Any], org_id: Optional[str] = None) -> None:
    con = _connect()
    missing = json.dumps(claim.get("missing_elements") or [])
    codes = json.dumps(claim.get("predicted_denial_codes") or [])
    con.execute(
        """
        INSERT OR REPLACE INTO claims (
            claim_id, org_id, claim_value_usd, denial_probability, expected_loss_usd,
            risk_level, payer_id, icd_10_code, cpt_code,
            documentation_complete, clinical_justification_present, procedure_mismatch_flag,
            patient_chart_notes, agent_correction_draft, explanation, recommended_action,
            confidence, missing_elements, predicted_denial_codes,
            payer_days_to_pay, cash_flow_urgency, model_base_probability, is_demo, resolved
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            claim["claim_id"],
            org_id,
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


def resolve_claim(
    claim_id: str,
    org_id: Optional[str] = None,
    resolved_by: Optional[str] = None,
) -> bool:
    """Mark a claim resolved (removed from the active worklist). Returns
    False if the claim does not exist."""
    del resolved_by  # DuckDB schema has no resolved_by column; kept for API parity
    con = _connect()
    where, params = _org_clause(org_id, "claim_id = ?")
    exists = con.execute(
        f"SELECT 1 FROM claims{where}", [claim_id, *params]
    ).fetchone()
    if not exists:
        con.close()
        return False
    con.execute(
        f"UPDATE claims SET resolved = TRUE{where}", [claim_id, *params]
    )
    con.close()
    return True


def get_claim(claim_id: str, org_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    con = _connect()
    where, params = _org_clause(org_id, "claim_id = ?")
    rows = con.execute(
        f"SELECT * FROM claims{where}", [claim_id, *params]
    ).fetchdf()
    con.close()
    if rows.empty:
        return None
    return _row_to_record(rows.to_dict(orient="records")[0])


def clear_claims(org_id: Optional[str] = None) -> None:
    con = _connect()
    where, params = _org_clause(org_id)
    con.execute(f"DELETE FROM claims{where}", params)
    con.close()


def clear_demo_claims(org_id: Optional[str] = None) -> None:
    """Delete only synthetic demo claims (is_demo = TRUE), leaving real
    analyzed claims intact. Scoped by org when an org_id is supplied."""
    con = _connect()
    where, params = _org_clause(org_id, "is_demo = TRUE")
    con.execute(f"DELETE FROM claims{where}", params)
    con.close()


def list_claims(org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    con = _connect()
    where, params = _org_clause(org_id, "resolved = FALSE")
    rows = con.execute(
        f"SELECT * FROM claims{where} ORDER BY analyzed_at DESC", params
    ).fetchdf()
    con.close()
    if rows.empty:
        return []
    return [_row_to_record(r) for r in rows.to_dict(orient="records")]


def get_executive_metrics(org_id: Optional[str] = None) -> Dict[str, Any]:
    con = _connect()
    where, params = _org_clause(org_id, "resolved = FALSE")
    count = con.execute(
        f"SELECT COUNT(*) FROM claims{where}", params
    ).fetchone()[0]
    if count == 0:
        con.close()
        return {}

    totals = con.execute(
        f"""
        SELECT
            COUNT(*) AS total_claims,
            COALESCE(SUM(claim_value_usd), 0) AS total_pipeline_liquidity,
            COALESCE(SUM(expected_loss_usd), 0) AS predicted_revenue_leakage,
            COALESCE(AVG(denial_probability), 0) AS avg_denial_probability,
            SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_count
        FROM claims{where}
        """,
        params,
    ).fetchone()

    # Denial code breakdown from JSON arrays
    code_where, code_params = _org_clause(
        org_id, "resolved = FALSE AND predicted_denial_codes IS NOT NULL"
    )
    code_rows = con.execute(
        f"SELECT predicted_denial_codes FROM claims{code_where}", code_params
    ).fetchall()
    code_counts: Dict[str, int] = {}
    for (raw,) in code_rows:
        for code in json.loads(raw or "[]"):
            code_counts[code] = code_counts.get(code, 0) + 1
    denial_breakdown = [
        {"code": k, "count": v} for k, v in sorted(code_counts.items(), key=lambda x: -x[1])
    ]

    payer_rows = con.execute(
        f"""
        SELECT payer_id,
               AVG(denial_probability) AS avg_prob,
               COUNT(*) AS claim_count
        FROM claims{where}
        GROUP BY payer_id
        ORDER BY avg_prob DESC
        """,
        params,
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
        "payer_trends": [
            {k: _native(v) for k, v in r.items()}
            for r in payer_rows.to_dict(orient="records")
        ],
    }
