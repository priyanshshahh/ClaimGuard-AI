"""Property tests for the expected-loss math and knapsack selection."""

from optimizer import (
    ASSUMED_OVERTURN_RATE,
    bounded_knapsack_select,
    calculate_cash_flow_urgency,
    calculate_expected_loss,
    calculate_expected_recovery,
    get_risk_level,
    prioritize_claims,
)


def _claim(cid, value, prob, weight=1):
    return {
        "claim_id": cid,
        "claim_value_usd": value,
        "denial_probability": prob,
        "review_weight": weight,
    }


def test_expected_loss_is_value_times_probability():
    assert calculate_expected_loss(10000, 0.25) == 2500.0
    assert calculate_expected_loss(0, 0.9) == 0.0


def test_expected_recovery_applies_overturn_rate():
    assert calculate_expected_recovery(10000, 0.5, overturn_rate=0.5) == 2500.0
    # default uses the documented assumption
    assert calculate_expected_recovery(10000, 0.5) == round(
        10000 * 0.5 * ASSUMED_OVERTURN_RATE, 2
    )


def test_prioritize_sets_expected_recovery_and_orders_by_it():
    claims = [
        _claim("small", 1000, 0.5),   # recovery 250
        _claim("big", 40000, 0.5),    # recovery 10000
    ]
    out = prioritize_claims(claims, mode="expected_recovery")
    assert out[0]["claim_id"] == "big"
    assert all("expected_recovery_usd" in c for c in out)


def test_cash_flow_urgency_higher_for_slower_payers():
    fast = calculate_cash_flow_urgency(10000, 0.5, "MEDICARE")  # 14 days
    slow = calculate_cash_flow_urgency(10000, 0.5, "BCBS")  # 42 days
    assert slow > fast


def test_risk_level_thresholds():
    assert get_risk_level(0.80) == "HIGH"
    assert get_risk_level(0.75) == "HIGH"
    assert get_risk_level(0.50) == "MEDIUM"
    assert get_risk_level(0.10) == "LOW"


def test_knapsack_respects_capacity():
    claims = [_claim(f"C{i}", 1000 * (i + 1), 0.5) for i in range(10)]
    selected = bounded_knapsack_select(claims, capacity=3)
    assert len(selected) == 3


def test_knapsack_picks_highest_expected_loss_at_unit_weight():
    claims = [
        _claim("small", 1000, 0.5),   # EL 500
        _claim("medium", 8000, 0.5),  # EL 4000
        _claim("large", 20000, 0.9),  # EL 18000
    ]
    selected = set(bounded_knapsack_select(claims, capacity=2))
    assert selected == {"large", "medium"}


def test_knapsack_with_weights_prefers_value_density():
    # one heavy high-value claim vs two light claims whose sum is greater
    claims = [
        _claim("heavy", 10000, 1.0, weight=2),  # EL 10000, weight 2
        _claim("light1", 6000, 1.0, weight=1),  # EL 6000
        _claim("light2", 6000, 1.0, weight=1),  # EL 6000
    ]
    selected = set(bounded_knapsack_select(claims, capacity=2))
    assert selected == {"light1", "light2"}


def test_knapsack_empty_and_zero_capacity():
    assert bounded_knapsack_select([], capacity=5) == []
    assert bounded_knapsack_select([_claim("a", 100, 0.5)], capacity=0) == []


def test_prioritize_marks_knapsack_selection():
    claims = [_claim(f"C{i}", 1000 * (i + 1), 0.5) for i in range(5)]
    out = prioritize_claims(claims, capacity=2)
    flags = [c["knapsack_selected"] for c in out]
    assert flags.count(True) == 2
    # selected claims are ordered first
    assert flags[:2] == [True, True]


def test_prioritize_treasury_orders_by_urgency():
    claims = [
        _claim("bcbs", 10000, 0.5) | {"payer_id": "BCBS"},
        _claim("medicare", 10000, 0.5) | {"payer_id": "MEDICARE"},
    ]
    out = prioritize_claims(claims, mode="treasury")
    assert out[0]["claim_id"] == "bcbs"
