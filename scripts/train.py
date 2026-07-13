#!/usr/bin/env python
"""Train the ClaimGuard denial-risk model on real CMS CERT audit data.

Dataset: Medicare Fee-for-Service Comprehensive Error Rate Testing (CERT),
published by CMS at data.cms.gov (public, no auth). Each row is a claim line
from a random sample of FFS claims audited by CERT reviewers.

Label (real, not synthetic): Review Decision == "Disagree" -> the reviewer
determined the claim was improperly paid (insufficient documentation, medical
necessity, incorrect coding, no documentation, other). "Agree" and appeals
that were "Overturned" count as 0. This is a documented proxy for denial
risk - see README for the honest framing.

Split (temporal, no leakage):
  train = 2021 + 2022 + 2023, validation = 2024, test = 2025.
Claim lines from the same claim never cross split boundaries because CERT
report years contain disjoint claim samples. All categorical encodings are
fitted on the training years only.

Models: XGBoost (primary) vs LogisticRegression (baseline), plus isotonic
calibration of the XGBoost scores fitted on the validation year.

Weights & Biases: enabled when WANDB_API_KEY or WANDB_MODE is set; defaults
to offline mode so the script runs without a login (sync later with
`wandb sync`). Disable entirely with WANDB_MODE=disabled.

Usage:
  python scripts/train.py [--data-dir data/cert] [--out backend/models]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import urllib.request
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from features import (  # noqa: E402
    FEATURE_COLUMNS,
    apply_features,
    fit_feature_maps,
    save_feature_maps,
)

SEED = 42

CERT_URLS = {
    2021: "https://data.cms.gov/sites/default/files/2022-01/4267ffed-b89a-402a-8c70-a048b32ae642/2021%20PartAPartB%20Public%20Data.csv",
    2022: "https://data.cms.gov/sites/default/files/2022-12/16676776-b9f0-4740-8345-5cc3f84e63db/2022%20PartAPartB%20Public%20Data.csv",
    2023: "https://data.cms.gov/sites/default/files/2023-12/8e1e39c7-859f-455b-9eab-6bb3d63e516c/2023%20PartAPartB%20Public%20Data.csv",
    2024: "https://data.cms.gov/sites/default/files/2024-11/9512fdeb-578d-428e-bddb-458338517cfb/2024%20PartAPartB%20Public%20Data.csv",
    2025: "https://data.cms.gov/sites/default/files/2026-01/53600220-96ac-49b3-bee7-83452b2b1df9/2025%20PartAPartB%20Public%20Data.csv",
}

TRAIN_YEARS = [2021, 2022, 2023]
VAL_YEAR = 2024
TEST_YEAR = 2025

COLUMN_MAP = {
    "claim_control_number": "claim_id",
    "Part": "part",
    "DRG": "drg",
    "HCPCS Procedure Code": "hcpcs",
    "Provider Type": "provider_type",
    "Type of Bill": "type_of_bill",
    "Review Decision": "review_decision",
    "Error Code": "error_code",
}


def download_year(year: int, data_dir: str) -> str:
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, f"cert_{year}.csv")
    if not os.path.exists(path):
        print(f"downloading CERT {year} ...")
        urllib.request.urlretrieve(CERT_URLS[year], path)
    return path


def load_year(year: int, data_dir: str) -> pd.DataFrame:
    path = download_year(year, data_dir)
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    df = df.rename(columns=COLUMN_MAP)[list(COLUMN_MAP.values())]
    df["year"] = year
    df["label"] = (df["review_decision"] == "Disagree").astype(int)
    df["hcpcs"] = df["hcpcs"].str.strip().str.upper()
    return df


def reliability_bins(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> list:
    frac_pos, mean_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy="quantile")
    return [
        {"mean_predicted": round(float(p), 4), "fraction_positive": round(float(t), 4)}
        for p, t in zip(mean_pred, frac_pos)
    ]


def evaluate(name: str, y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    return {
        "model": name,
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4),
        "brier": round(float(brier_score_loss(y_true, y_prob)), 4),
        "log_loss": round(float(log_loss(y_true, y_prob)), 4),
        "base_rate": round(float(np.mean(y_true)), 4),
        "n": int(len(y_true)),
        "reliability": reliability_bins(y_true, y_prob),
    }


def init_wandb(config: dict):
    mode = os.getenv("WANDB_MODE")
    if mode is None and not os.getenv("WANDB_API_KEY"):
        os.environ["WANDB_MODE"] = "offline"
    if os.getenv("WANDB_MODE") == "disabled":
        return None
    try:
        import wandb

        return wandb.init(
            project=os.getenv("WANDB_PROJECT", "claimguard-denial-model"),
            config=config,
            tags=["cert", "xgboost"],
        )
    except Exception as e:  # never let tracking break training
        print(f"wandb disabled ({e})")
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/cert")
    ap.add_argument("--out", default="backend/models")
    args = ap.parse_args()

    np.random.seed(SEED)

    print("loading CERT years ...")
    train_df = pd.concat([load_year(y, args.data_dir) for y in TRAIN_YEARS], ignore_index=True)
    val_df = load_year(VAL_YEAR, args.data_dir)
    test_df = load_year(TEST_YEAR, args.data_dir)

    maps = fit_feature_maps(train_df)  # training years only - no leakage
    X_tr, y_tr = apply_features(train_df, maps), train_df["label"].values
    X_va, y_va = apply_features(val_df, maps), val_df["label"].values
    X_te, y_te = apply_features(test_df, maps), test_df["label"].values

    config = {
        "dataset": "CMS Medicare FFS CERT (data.cms.gov)",
        "train_years": TRAIN_YEARS,
        "val_year": VAL_YEAR,
        "test_year": TEST_YEAR,
        "n_train": len(y_tr),
        "n_val": len(y_va),
        "n_test": len(y_te),
        "features": FEATURE_COLUMNS,
        "seed": SEED,
        "label": "CERT Review Decision == Disagree (improper payment)",
    }
    run = init_wandb(config)

    # --- baseline: logistic regression ---
    logreg = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=SEED)),
        ]
    )
    logreg.fit(X_tr, y_tr)

    # --- primary: XGBoost with early stopping on the validation year ---
    xgb = XGBClassifier(
        n_estimators=600,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        min_child_weight=5,
        eval_metric="aucpr",
        early_stopping_rounds=40,
        random_state=SEED,
        n_jobs=4,
    )
    xgb.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)

    # --- isotonic calibration of XGBoost scores, fitted on validation ---
    val_raw = xgb.predict_proba(X_va)[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.001, y_max=0.999)
    iso.fit(val_raw, y_va)

    results = {"val": [], "test": []}
    for split, X, y in [("val", X_va, y_va), ("test", X_te, y_te)]:
        p_lr = logreg.predict_proba(X)[:, 1]
        p_xgb = xgb.predict_proba(X)[:, 1]
        p_cal = iso.predict(p_xgb)
        results[split].append(evaluate("logreg_baseline", y, p_lr))
        results[split].append(evaluate("xgboost", y, p_xgb))
        results[split].append(evaluate("xgboost_isotonic", y, p_cal))

    metrics = {
        "config": config,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "results": results,
        "best_iteration": int(xgb.best_iteration),
    }

    os.makedirs(args.out, exist_ok=True)
    joblib.dump(xgb, os.path.join(args.out, "denial_model.joblib"))
    joblib.dump(iso, os.path.join(args.out, "calibrator.joblib"))
    save_feature_maps(maps, os.path.join(args.out, "feature_maps.json"))
    with open(os.path.join(args.out, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    if run is not None:
        import wandb

        for split in ("val", "test"):
            for r in results[split]:
                wandb.log(
                    {
                        f"{split}/{r['model']}/roc_auc": r["roc_auc"],
                        f"{split}/{r['model']}/pr_auc": r["pr_auc"],
                        f"{split}/{r['model']}/brier": r["brier"],
                        f"{split}/{r['model']}/log_loss": r["log_loss"],
                    }
                )
        art = wandb.Artifact("claimguard-denial-model", type="model")
        for fname in ("denial_model.joblib", "calibrator.joblib", "feature_maps.json", "metrics.json"):
            art.add_file(os.path.join(args.out, fname))
        run.log_artifact(art)
        run.finish()

    print(json.dumps({k: v for k, v in metrics.items() if k != "config"}, indent=2)[:2000])
    print(f"\nartifacts written to {args.out}/")


if __name__ == "__main__":
    main()
