import os
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder

MODEL_PATH = "models/denial_model.pkl"
ENCODERS_PATH = "models/encoders.pkl"
MODEL_TYPE_PATH = "models/model_type.txt"

FEATURE_COLUMNS = [
    "claim_value_usd",
    "payer_encoded",
    "icd_risk",
    "cpt_risk",
    "documentation_complete",
    "clinical_justification_present",
    "procedure_mismatch_flag",
]

_xgb = None
try:
    import xgboost as xgb

    _xgb = xgb
except Exception:
    _xgb = None


def _make_classifier(pos: int, neg: int):
    scale_pos_weight = neg / max(pos, 1)
    if _xgb is not None:
        return _xgb.XGBClassifier(
            n_estimators=120,
            max_depth=5,
            learning_rate=0.08,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=42,
        ), "xgboost"
    return (
        HistGradientBoostingClassifier(
            max_iter=120,
            max_depth=5,
            learning_rate=0.08,
            random_state=42,
        ),
        "hist_gradient_boosting",
    )


def train_dummy_model():
    """Train classifier on synthetic imbalanced denial data (~10% positive class)."""
    np.random.seed(42)
    n_samples = 1000

    data = {
        "claim_value_usd": np.random.uniform(150, 25000, n_samples),
        "payer_id": np.random.choice(
            ["AETNA", "UHC", "BCBS", "MEDICARE", "MEDICAID"], n_samples
        ),
        "icd_risk": np.random.uniform(0, 1, n_samples),
        "cpt_risk": np.random.uniform(0, 1, n_samples),
        "documentation_complete": np.random.choice([0, 1], n_samples, p=[0.3, 0.7]),
        "clinical_justification_present": np.random.choice([0, 1], n_samples, p=[0.25, 0.75]),
        "procedure_mismatch_flag": np.random.choice([0, 1], n_samples, p=[0.2, 0.8]),
    }
    df = pd.DataFrame(data)

    denial_prob = (
        0.35 * (df["claim_value_usd"] > 8000).astype(int)
        + 0.25 * (df["documentation_complete"] == 0).astype(int)
        + 0.2 * (df["clinical_justification_present"] == 0).astype(int)
        + 0.15 * df["procedure_mismatch_flag"]
        + 0.05 * (df["icd_risk"] > 0.7).astype(int)
    )
    y = (denial_prob > 0.55).astype(int)

    le_payer = LabelEncoder()
    df["payer_encoded"] = le_payer.fit_transform(df["payer_id"])
    X = df[FEATURE_COLUMNS]

    pos = max(int(y.sum()), 1)
    neg = max(int(len(y) - y.sum()), 1)
    model, model_type = _make_classifier(pos, neg)

    sample_weight = np.where(y == 1, neg / pos, 1.0)
    model.fit(X, y, sample_weight=sample_weight)

    os.makedirs("models", exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump({"payer": le_payer}, ENCODERS_PATH)
    with open(MODEL_TYPE_PATH, "w") as f:
        f.write(model_type)
    return model, {"payer": le_payer}


def load_model():
    if os.path.exists(MODEL_PATH) and os.path.exists(ENCODERS_PATH):
        try:
            return joblib.load(MODEL_PATH), joblib.load(ENCODERS_PATH)
        except Exception:
            pass
    return train_dummy_model()


def predict_denial_probability(features: dict) -> float:
    model, encoders = load_model()
    payer_le: LabelEncoder = encoders["payer"]
    payer_id = features["payer_id"]
    if payer_id not in payer_le.classes_:
        payer_encoded = 0
    else:
        payer_encoded = int(payer_le.transform([payer_id])[0])

    X = pd.DataFrame(
        [
            {
                "claim_value_usd": features["claim_value_usd"],
                "payer_encoded": payer_encoded,
                "icd_risk": features.get("icd_risk", 0.5),
                "cpt_risk": features.get("cpt_risk", 0.5),
                "documentation_complete": features.get("documentation_complete", 1),
                "clinical_justification_present": features.get(
                    "clinical_justification_present", 1
                ),
                "procedure_mismatch_flag": features.get("procedure_mismatch_flag", 0),
            }
        ]
    )
    prob = model.predict_proba(X)[0][1]
    return float(prob)
