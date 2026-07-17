"""Serving-layer tests against the committed real-data model artifacts."""

import pytest

from model import (
    FEATURE_LABELS,
    PROB_CAP,
    adjust_for_agent_findings,
    explain_claim,
    get_model_metrics,
    load_model,
    predict_base_probability,
    predict_denial_probability,
)


def test_artifacts_load():
    model, calibrator, maps = load_model()
    assert hasattr(model, "predict_proba")
    assert "prior" in maps and 0 < maps["prior"] < 1


def test_base_probability_in_unit_interval():
    for cpt in ["99214", "27447", "K0739", "TOTALLY-UNKNOWN"]:
        p = predict_base_probability(cpt)
        assert 0.0 <= p <= 1.0


def test_unknown_code_falls_back_near_prior():
    _, _, maps = load_model()
    p = predict_base_probability("ZZZZZ-NOT-A-CODE")
    # unseen codes get prior-encoded features, prediction should be sane
    assert 0.0 < p < 0.7


def test_agent_flags_increase_probability_monotonically():
    base = predict_base_probability("99214")
    flagged = adjust_for_agent_findings(base, 0, 0, 1)
    partially = adjust_for_agent_findings(base, 0, 1, 0)
    assert flagged > partially > base


def test_uplift_capped():
    assert adjust_for_agent_findings(0.95, 0, 0, 1) == PROB_CAP


def test_predict_denial_probability_entry_point():
    p_clean = predict_denial_probability({"cpt_code": "99214"})
    p_flagged = predict_denial_probability(
        {"cpt_code": "99214", "documentation_complete": 0}
    )
    assert 0 <= p_clean <= 1
    assert p_flagged == pytest.approx(p_clean + 0.15, abs=1e-6)


def test_explain_claim_returns_ranked_plain_language_drivers():
    drivers = explain_claim("99214", top_n=5)
    assert 1 <= len(drivers) <= 5
    # returned in descending magnitude order
    mags = [abs(d["contribution"]) for d in drivers]
    assert mags == sorted(mags, reverse=True)
    for d in drivers:
        assert d["direction"] in ("increases", "decreases")
        assert d["label"] == FEATURE_LABELS[d["feature"]]


def test_metrics_json_reports_real_run():
    m = get_model_metrics()
    assert m is not None
    assert m["config"]["dataset"].startswith("CMS Medicare FFS CERT")
    for split in ("val", "test"):
        models = {r["model"] for r in m["results"][split]}
        assert {"logreg_baseline", "xgboost", "xgboost_isotonic"} <= models
        for r in m["results"][split]:
            assert 0.5 < r["roc_auc"] < 1.0
            assert 0 < r["pr_auc"] < 1.0
            assert len(r["reliability"]) >= 5
