"""DuckDB store layer tests (isolated per-test DB via DUCKDB_PATH)."""

import duckdb_store as store


def test_upsert_and_get_roundtrip(sample_claim):
    store.upsert_claim(sample_claim)
    got = store.get_claim("CLM-TEST-1")
    assert got is not None
    assert got["claim_value_usd"] == 12500.0
    assert got["predicted_denial_codes"] == ["CO-50"]
    assert bool(got["is_demo"]) is False


def test_upsert_replaces_existing(sample_claim):
    store.upsert_claim(sample_claim)
    store.upsert_claim(sample_claim | {"denial_probability": 0.9})
    claims = store.list_claims()
    assert len(claims) == 1
    assert claims[0]["denial_probability"] == 0.9


def test_get_claim_missing_returns_none():
    assert store.get_claim("NOPE") is None


def test_clear_claims(sample_claim):
    store.upsert_claim(sample_claim)
    store.clear_claims()
    assert store.list_claims() == []


def test_priority_queue_orders_by_expected_loss(sample_claim):
    store.upsert_claim(sample_claim | {"claim_id": "LOW", "expected_loss_usd": 100})
    store.upsert_claim(sample_claim | {"claim_id": "HIGH", "expected_loss_usd": 9000})
    store.upsert_claim(sample_claim | {"claim_id": "MID", "expected_loss_usd": 4000})
    queue = store.query_priority_queue(mode="expected_loss", limit=2)
    assert [c["claim_id"] for c in queue] == ["HIGH", "MID"]


def test_priority_queue_treasury_mode(sample_claim):
    store.upsert_claim(sample_claim | {"claim_id": "SLOW", "cash_flow_urgency": 999.0})
    store.upsert_claim(sample_claim | {"claim_id": "FAST", "cash_flow_urgency": 1.0})
    queue = store.query_priority_queue(mode="treasury", limit=5)
    assert queue[0]["claim_id"] == "SLOW"


def test_executive_metrics_aggregates(sample_claim):
    store.upsert_claim(sample_claim | {"claim_id": "A", "risk_level": "HIGH"})
    store.upsert_claim(sample_claim | {"claim_id": "B"})
    m = store.get_executive_metrics()
    assert m["total_claims"] == 2
    assert m["high_risk_count"] == 1
    assert m["total_pipeline_liquidity"] == 25000.0
    assert any(row["code"] == "CO-50" and row["count"] == 2 for row in m["denial_code_breakdown"])


def test_executive_metrics_empty():
    assert store.get_executive_metrics() == {}


def test_demo_flag_persisted(sample_claim):
    store.upsert_claim(sample_claim | {"claim_id": "DEMO-1", "is_demo": True})
    got = store.get_claim("DEMO-1")
    assert bool(got["is_demo"]) is True
