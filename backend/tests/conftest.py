import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(autouse=True)
def isolated_duckdb(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    """Point every test at its own throwaway DuckDB file."""
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "claims.duckdb"))
    yield


@pytest.fixture
def sample_claim() -> dict:
    return {
        "claim_id": "CLM-TEST-1",
        "claim_value_usd": 12500.0,
        "denial_probability": 0.42,
        "expected_loss_usd": 5250.0,
        "risk_level": "MEDIUM",
        "payer_id": "UHC",
        "icd_10_code": "M17.11",
        "cpt_code": "27447",
        "documentation_complete": 1,
        "clinical_justification_present": 1,
        "procedure_mismatch_flag": 0,
        "patient_chart_notes": "Patient with end-stage OA, failed conservative care.",
        "agent_correction_draft": "",
        "explanation": "test",
        "recommended_action": "Standard processing recommended",
        "confidence": 0.8,
        "missing_elements": [],
        "predicted_denial_codes": ["CO-50"],
        "payer_days_to_pay": 31,
        "cash_flow_urgency": 100.0,
        "model_base_probability": 0.1,
        "is_demo": False,
    }
