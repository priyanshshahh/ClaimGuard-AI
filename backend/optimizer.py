import os
from typing import Dict, List

PAYER_PAYMENT_SPEED = {
    "MEDICARE": 14,
    "MEDICAID": 22,
    "AETNA": 28,
    "UHC": 31,
    "BCBS": 42,
}

DEFAULT_AUDITOR_CAPACITY = 8

# ASSUMPTION (not a measured ClaimGuard outcome): the share of denied claims
# that are overturned on appeal / rework. Industry figures commonly land in the
# 40-60% range (e.g. KFF analyses of ACA-marketplace internal appeals found
# roughly half of appealed denials overturned). We use a mid-range 0.5 as a
# documented, tunable assumption via OVERTURN_RATE; expected *recovery* dollars
# = billed value x denial probability x this rate. It is labeled as an
# assumption everywhere it is surfaced.
ASSUMED_OVERTURN_RATE = float(os.getenv("OVERTURN_RATE", "0.5"))


def calculate_expected_loss(claim_value: float, denial_prob: float) -> float:
    return round(claim_value * denial_prob, 2)


def calculate_expected_recovery(
    claim_value: float, denial_prob: float, overturn_rate: float = ASSUMED_OVERTURN_RATE
) -> float:
    """Expected *recoverable* dollars from working a claim:
    billed value x P(denial) x P(overturn on appeal). The overturn rate is a
    documented assumption (see ASSUMED_OVERTURN_RATE), not a measured result."""
    return round(claim_value * denial_prob * overturn_rate, 2)


def calculate_cash_flow_urgency(
    claim_value: float, denial_prob: float, payer_id: str
) -> float:
    days = PAYER_PAYMENT_SPEED.get(payer_id, 35)
    expected_loss = calculate_expected_loss(claim_value, denial_prob)
    slowness_factor = (days / 14.0) ** 1.1
    urgency = (expected_loss * slowness_factor) / (days**0.5)
    return round(urgency, 2)


def bounded_knapsack_select(
    claims: List[Dict], capacity: int = DEFAULT_AUDITOR_CAPACITY
) -> List[str]:
    """
    0/1 bounded knapsack: maximize sum(EL_i) subject to sum(review_weight) <= K.
    Default review_weight = 1 per claim (auditor daily capacity in claim count).
    """
    if not claims or capacity <= 0:
        return []

    items = []
    for c in claims:
        el = c.get("expected_loss_usd") or calculate_expected_loss(
            c["claim_value_usd"], c["denial_probability"]
        )
        weight = max(int(c.get("review_weight", 1)), 1)
        items.append((c["claim_id"], int(el * 100), weight))

    n = len(items)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    keep = [[False] * (capacity + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        claim_id, value, weight = items[i - 1]
        for w in range(capacity + 1):
            dp[i][w] = dp[i - 1][w]
            if weight <= w and dp[i - 1][w - weight] + value > dp[i][w]:
                dp[i][w] = dp[i - 1][w - weight] + value
                keep[i][w] = True

    selected: List[str] = []
    w = capacity
    for i in range(n, 0, -1):
        if keep[i][w]:
            selected.append(items[i - 1][0])
            w -= items[i - 1][2]

    return selected


def prioritize_claims(
    claims: List[Dict], mode: str = "expected_loss", capacity: int | None = None
) -> List[Dict]:
    for claim in claims:
        claim["expected_loss_usd"] = calculate_expected_loss(
            claim["claim_value_usd"], claim["denial_probability"]
        )
        claim["expected_recovery_usd"] = calculate_expected_recovery(
            claim["claim_value_usd"], claim["denial_probability"]
        )
        payer = claim.get("payer_id", "UHC")
        claim["cash_flow_urgency"] = calculate_cash_flow_urgency(
            claim["claim_value_usd"], claim["denial_probability"], payer
        )
        claim["payer_days_to_pay"] = PAYER_PAYMENT_SPEED.get(payer, 35)

    if mode == "treasury":
        sorted_claims = sorted(
            claims, key=lambda x: x.get("cash_flow_urgency", 0), reverse=True
        )
    elif mode == "expected_recovery":
        sorted_claims = sorted(
            claims, key=lambda x: x.get("expected_recovery_usd", 0), reverse=True
        )
    else:
        sorted_claims = sorted(
            claims, key=lambda x: x["expected_loss_usd"], reverse=True
        )

    if capacity:
        selected_ids = set(
            bounded_knapsack_select(sorted_claims, capacity=capacity)
        )
        knapsack_claims = [c for c in sorted_claims if c["claim_id"] in selected_ids]
        other = [c for c in sorted_claims if c["claim_id"] not in selected_ids]
        for c in knapsack_claims:
            c["knapsack_selected"] = True
        for c in other:
            c["knapsack_selected"] = False
        return knapsack_claims + other

    return sorted_claims


def get_risk_level(probability: float) -> str:
    if probability >= 0.75:
        return "HIGH"
    if probability >= 0.45:
        return "MEDIUM"
    return "LOW"
