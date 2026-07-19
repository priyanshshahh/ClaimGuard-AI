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


def test_resolve_claim_excludes_from_worklist(sample_claim):
    store.upsert_claim(sample_claim)
    assert store.resolve_claim("CLM-TEST-1") is True
    # resolved claim leaves the active worklist and metrics...
    assert store.list_claims() == []
    assert store.get_executive_metrics() == {}
    # ...but is still retrievable by id (audit trail)
    assert store.get_claim("CLM-TEST-1") is not None


def test_resolve_missing_claim_returns_false():
    assert store.resolve_claim("NOPE") is False


def test_demo_flag_persisted(sample_claim):
    store.upsert_claim(sample_claim | {"claim_id": "DEMO-1", "is_demo": True})
    got = store.get_claim("DEMO-1")
    assert bool(got["is_demo"]) is True


def test_clear_demo_claims_preserves_real(sample_claim):
    store.upsert_claim(sample_claim | {"claim_id": "REAL-1", "is_demo": False})
    store.upsert_claim(sample_claim | {"claim_id": "DEMO-1", "is_demo": True})
    store.clear_demo_claims()
    remaining = {c["claim_id"] for c in store.list_claims()}
    assert remaining == {"REAL-1"}
    assert store.get_claim("DEMO-1") is None
