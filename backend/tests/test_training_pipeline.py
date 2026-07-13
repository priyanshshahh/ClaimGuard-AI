"""Training pipeline functions exercised on a real 2000-row CERT fixture.

The fixture is a stratified sample of the actual CERT 2024 public file
(backend/tests/fixtures/cert_sample_2024.csv), so these tests verify the
pipeline end-to-end on genuine data without network access.
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts"),
)

from features import FEATURE_COLUMNS, apply_features, fit_feature_maps  # noqa: E402
from train import COLUMN_MAP, evaluate  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "cert_sample_2024.csv")


@pytest.fixture(scope="module")
def cert_df() -> pd.DataFrame:
    df = pd.read_csv(FIXTURE, dtype=str, keep_default_na=False)
    df = df.rename(columns=COLUMN_MAP)[list(COLUMN_MAP.values())]
    df["label"] = (df["review_decision"] == "Disagree").astype(int)
    df["hcpcs"] = df["hcpcs"].str.strip().str.upper()
    return df


def test_fixture_is_real_cert_shape(cert_df):
    assert len(cert_df) == 2000
    assert set(cert_df["review_decision"]) <= {"Agree", "Disagree"}
    assert 0.15 < cert_df["label"].mean() < 0.25  # stratified 20% positive


def test_feature_maps_fit_and_apply(cert_df):
    maps = fit_feature_maps(cert_df)
    X = apply_features(cert_df, maps)
    assert list(X.columns) == FEATURE_COLUMNS
    assert len(X) == len(cert_df)
    assert X.notna().all().all()
    assert ((X["hcpcs_rate"] >= 0) & (X["hcpcs_rate"] <= 1)).all()


def test_unseen_levels_fall_back_to_prior(cert_df):
    maps = fit_feature_maps(cert_df)
    unseen = pd.DataFrame(
        [{"hcpcs": "NOPE1", "part": "9. Unknown", "provider_type": "??", "type_of_bill": "", "drg": ""}]
    )
    X = apply_features(unseen, maps)
    assert X.loc[0, "hcpcs_rate"] == pytest.approx(maps["prior"])
    assert X.loc[0, "part_idx"] == -1


def test_smoothing_pulls_rare_levels_toward_prior(cert_df):
    from features import smoothed_rate

    prior = cert_df["label"].mean()
    # a level seen once with a positive label should NOT get rate 1.0
    rate = smoothed_rate(positives=1, count=1, prior=prior)
    assert prior < rate < 0.1 + prior


def test_train_tiny_model_on_fixture(cert_df):
    from xgboost import XGBClassifier

    train, test = cert_df.iloc[:1500], cert_df.iloc[1500:]
    maps = fit_feature_maps(train)  # fitted on train slice only
    clf = XGBClassifier(n_estimators=30, max_depth=3, random_state=42)
    clf.fit(apply_features(train, maps), train["label"])
    probs = clf.predict_proba(apply_features(test, maps))[:, 1]
    report = evaluate("tiny", test["label"].values, probs)
    assert report["roc_auc"] > 0.55  # real signal, small sample
    assert report["n"] == 500


def test_evaluate_reports_required_metrics(cert_df):
    import numpy as np

    y = cert_df["label"].values
    rng = np.random.default_rng(42)
    p = np.clip(y * 0.6 + rng.uniform(0, 0.4, len(y)), 0, 1)
    r = evaluate("check", y, p)
    assert {"roc_auc", "pr_auc", "brier", "log_loss", "reliability"} <= set(r)
