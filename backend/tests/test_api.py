"""API route tests via TestClient with the LLM agent mocked out."""

import pytest
from fastapi.testclient import TestClient

import main


AGENT_RESULT = {
    "documentation_complete": 0,
    "clinical_justification_present": 1,
    "procedure_mismatch_flag": 0,
    "agent_correction_draft": "Add explicit medical-necessity statement.",
    "explanation": "Documentation incomplete for level billed.",
    "confidence": 0.9,
    "missing_elements": ["time documentation"],
    "predicted_denial_codes": ["CO-16"],
}

CLAIM = {
    "claim_id": "CLM-API-1",
    "claim_value_usd": 5000,
    "payer_id": "UHC",
    "icd_10_code": "E11.9",
    "cpt_code": "99214",
    "patient_chart_notes": "45 y/o M with type 2 diabetes follow-up, labs reviewed, meds adjusted.",
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "analyze_clinical_notes", lambda **kw: dict(AGENT_RESULT))
    with TestClient(main.app) as c:
        yield c


def test_root_health(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_analyze_claim_returns_model_and_uplift(client):
    r = client.post("/api/analyze-claim", json=CLAIM)
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["model_base_probability"] <= 1
    # agent flagged missing documentation -> documented +0.15 uplift
    assert body["denial_probability"] == pytest.approx(
        min(body["model_base_probability"] + 0.15, 0.97), abs=0.002
    )
    assert body["is_demo"] is False
    assert body["expected_loss_usd"] == pytest.approx(
        CLAIM["claim_value_usd"] * body["denial_probability"], rel=0.01
    )


def test_analyze_claim_surfaces_carc_recovery_and_drivers(client):
    # AGENT_RESULT flags documentation_complete=0 -> CARC 16 (CO)
    body = client.post("/api/analyze-claim", json=CLAIM).json()
    assert body["carc_code"] == "16"
    assert body["carc_group"] == "CO"
    assert body["carc_reasons"][0]["rarc_code"] == "N706"
    # expected recovery = value x denial_prob x overturn assumption (<= expected loss)
    assert 0 < body["expected_recovery_usd"] <= body["expected_loss_usd"]
    assert len(body["top_drivers"]) >= 1
    assert body["top_drivers"][0]["direction"] in ("increases", "decreases")


def test_priority_queue_expected_recovery_mode(client):
    client.post("/api/analyze-claim", json=CLAIM)
    client.post("/api/analyze-claim", json=CLAIM | {"claim_id": "BIG", "claim_value_usd": 90000})
    r = client.get("/api/priority-queue?mode=expected_recovery&knapsack=false")
    claims = r.json()["claims"]
    assert claims[0]["claim_id"] == "BIG"
    # queue claims are enriched with derived CARC + drivers on read
    assert claims[0]["carc_code"] == "16"
    assert len(claims[0]["top_drivers"]) >= 1


def test_analyze_claim_validation_rejects_short_notes(client):
    bad = CLAIM | {"patient_chart_notes": "too short"}
    assert client.post("/api/analyze-claim", json=bad).status_code == 422


def test_claim_persisted_in_duckdb_only(client):
    client.post("/api/analyze-claim", json=CLAIM)
    from duckdb_store import get_claim

    stored = get_claim("CLM-API-1")
    assert stored is not None
    assert stored["payer_id"] == "UHC"
    # the old in-memory mirror is gone
    assert not hasattr(main, "claims_db")


def test_priority_queue_and_knapsack(client):
    client.post("/api/analyze-claim", json=CLAIM)
    client.post("/api/analyze-claim", json=CLAIM | {"claim_id": "CLM-API-2", "claim_value_usd": 90000})
    r = client.get("/api/priority-queue?capacity=1")
    body = r.json()
    assert body["claims"][0]["claim_id"] == "CLM-API-2"
    assert body["claims"][0]["knapsack_selected"] is True
    assert body["claims"][1]["knapsack_selected"] is False


def test_dashboard_metrics_empty_then_populated(client):
    assert client.get("/api/dashboard-metrics").json()["total_claims"] == 0
    client.post("/api/analyze-claim", json=CLAIM)
    m = client.get("/api/dashboard-metrics").json()
    assert m["total_claims"] == 1
    assert m["total_pipeline_liquidity"] == 5000


def test_seed_demo_labels_claims(client):
    r = client.post("/api/seed-demo")
    assert r.json()["is_demo"] is True
    from duckdb_store import list_claims

    assert all(bool(c["is_demo"]) for c in list_claims())


def test_clear_queue(client):
    client.post("/api/seed-demo")
    client.post("/api/clear-queue")
    assert client.get("/api/dashboard-metrics").json()["total_claims"] == 0


def test_resolve_claim_persists_and_drops_from_queue(client):
    client.post("/api/analyze-claim", json=CLAIM)
    assert client.get("/api/dashboard-metrics").json()["total_claims"] == 1
    r = client.post("/api/resolve-claim", json={"claim_id": "CLM-API-1"})
    assert r.status_code == 200 and r.json()["resolved"] is True
    # resolved claim persists as resolved -> drops out of queue + metrics
    assert client.get("/api/dashboard-metrics").json()["total_claims"] == 0
    assert client.get("/api/priority-queue").json()["claims"] == []


def test_resolve_unknown_claim_404(client):
    assert client.post("/api/resolve-claim", json={"claim_id": "NOPE"}).status_code == 404


def test_generate_appeal_404_for_unknown_claim(client):
    r = client.post("/api/generate-appeal?claim_id=NOPE")
    assert r.status_code == 404


def test_check_policy_requires_fields(client):
    r = client.post("/api/check-policy", json={})
    assert r.status_code == 400


def test_fhir_endpoint_is_labeled_demo(client):
    r = client.post("/api/fhir/claim", json={"id": "X", "cpt": "99214", "total": 100})
    body = r.json()
    assert body["demo"] is True
    assert body["fhir_claim"]["item"][0]["productOrService"]["coding"][0]["code"] == "99214"


def test_model_info_serves_real_metrics(client):
    m = client.get("/api/model-info").json()
    assert "CERT" in m["config"]["dataset"]
    assert m["results"]["test"][0]["n"] > 100000


def test_health_ready_when_model_loaded(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["model_loaded"] is True
    assert body["store_reachable"] is True


def test_me_returns_identity(client):
    # AUTH_DISABLED -> synthetic local admin
    body = client.get("/api/me").json()
    assert body["org_id"] == "local"
    assert body["role"] == "admin"
    assert "user_id" in body and "email" in body


def test_seed_demo_preserves_real_claims(client):
    client.post("/api/analyze-claim", json=CLAIM)  # real, is_demo=False
    client.post("/api/seed-demo")
    from duckdb_store import get_claim

    # real claim survives the re-seed; demo claims are added alongside it
    assert get_claim("CLM-API-1") is not None
    m = client.get("/api/dashboard-metrics").json()
    assert m["total_claims"] >= 7  # 1 real + 6 demo


def test_dashboard_metrics_includes_score_histogram(client):
    client.post("/api/analyze-claim", json=CLAIM)
    m = client.get("/api/dashboard-metrics").json()
    assert "score_histogram" in m
    assert sum(b["count"] for b in m["score_histogram"]) == m["total_claims"]
