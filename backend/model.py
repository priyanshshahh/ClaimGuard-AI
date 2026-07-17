"""Serving layer for the denial-risk model trained on real CMS CERT data.

Artifacts (produced by scripts/train.py, committed in backend/models/):
  - denial_model.joblib   XGBoost classifier
  - calibrator.joblib     isotonic calibration fitted on the validation year
  - feature_maps.json     categorical encodings fitted on training years
  - metrics.json          full evaluation report from the real training run

The model scores claim attributes (HCPCS/CPT code, Medicare part, provider
type, type of bill). LLM-agent documentation findings are applied afterwards
as an explicit, documented heuristic uplift - they are NOT model features,
because the CERT public file contains no chart-note fields. See
`adjust_for_agent_findings` for the exact rule.
"""

from __future__ import annotations

import json
import os
from typing import Optional, Tuple

import joblib

import xgboost as xgb

from features import FEATURE_COLUMNS, build_serving_row, load_feature_maps

# Plain-language labels for the 9 model features, for per-claim explanations.
FEATURE_LABELS = {
    "part_idx": "Medicare part",
    "hcpcs_first_idx": "Procedure-code family",
    "has_drg": "DRG present on claim",
    "tob_present": "Type-of-bill present",
    "hcpcs_rate": "Historical improper-payment rate for this procedure code",
    "provider_rate": "Historical improper-payment rate for this provider type",
    "tob_rate": "Historical improper-payment rate for this type of bill",
    "part_rate": "Historical improper-payment rate for this Medicare part",
    "hcpcs_freq_log": "How frequently this procedure code appears in CERT",
}

MODELS_DIR = os.getenv("MODELS_DIR", os.path.join(os.path.dirname(__file__), "models"))

# Heuristic uplifts applied on top of the model's calibrated probability when
# the LLM agent flags documentation problems. Insufficient/no documentation is
# the largest improper-payment category in CERT, so missing documentation
# carries the largest uplift. These constants are a documented business rule,
# not model output; the API reports the model's base probability separately.
UPLIFT_DOC_MISSING = 0.15
UPLIFT_NO_JUSTIFICATION = 0.10
UPLIFT_PROCEDURE_MISMATCH = 0.12
PROB_CAP = 0.97

_cache: dict = {}


def load_model() -> Tuple[object, object, dict]:
    """Load and cache (model, calibrator, feature_maps)."""
    if "model" not in _cache:
        model_path = os.path.join(MODELS_DIR, "denial_model.joblib")
        cal_path = os.path.join(MODELS_DIR, "calibrator.joblib")
        maps_path = os.path.join(MODELS_DIR, "feature_maps.json")
        if not (os.path.exists(model_path) and os.path.exists(maps_path)):
            raise RuntimeError(
                f"Model artifacts not found in {MODELS_DIR}. Run: python scripts/train.py"
            )
        _cache["model"] = joblib.load(model_path)
        _cache["calibrator"] = joblib.load(cal_path) if os.path.exists(cal_path) else None
        _cache["maps"] = load_feature_maps(maps_path)
    return _cache["model"], _cache["calibrator"], _cache["maps"]


def get_model_metrics() -> Optional[dict]:
    path = os.path.join(MODELS_DIR, "metrics.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def predict_base_probability(
    cpt_code: str,
    part: str = "1. Part B",
    provider_type: str = "",
    type_of_bill: str = "",
    drg: str = "",
) -> float:
    """Calibrated P(improper payment) for the claim attributes alone."""
    model, calibrator, maps = load_model()
    row = build_serving_row(
        maps,
        hcpcs=cpt_code,
        part=part,
        provider_type=provider_type,
        type_of_bill=type_of_bill,
        drg=drg,
    )
    raw = float(model.predict_proba(row)[0][1])
    if calibrator is not None:
        raw = float(calibrator.predict([raw])[0])
    return max(min(raw, 1.0), 0.0)


def explain_claim(
    cpt_code: str,
    part: str = "1. Part B",
    provider_type: str = "",
    type_of_bill: str = "",
    drg: str = "",
    top_n: int = 5,
) -> list[dict]:
    """Per-claim top feature contributions using XGBoost's native SHAP-style
    `pred_contribs` (no extra dependency). Contributions are in log-odds/margin
    space; we return the top-N by magnitude with a plain-language label and
    direction. This explains the model's base probability only — the agent
    documentation uplift is a separate, already-visible business rule."""
    model, _, maps = load_model()
    row = build_serving_row(
        maps,
        hcpcs=cpt_code,
        part=part,
        provider_type=provider_type,
        type_of_bill=type_of_bill,
        drg=drg,
    )
    booster = model.get_booster()
    contribs = booster.predict(xgb.DMatrix(row), pred_contribs=True)[0]
    # last entry is the bias term; drop it
    feature_contribs = list(zip(FEATURE_COLUMNS, contribs[:-1]))
    feature_contribs.sort(key=lambda kv: abs(kv[1]), reverse=True)
    drivers = []
    for name, value in feature_contribs[:top_n]:
        drivers.append(
            {
                "feature": name,
                "label": FEATURE_LABELS.get(name, name),
                "contribution": round(float(value), 4),
                "direction": "increases" if value >= 0 else "decreases",
            }
        )
    return drivers


def adjust_for_agent_findings(
    base_prob: float,
    documentation_complete: int = 1,
    clinical_justification_present: int = 1,
    procedure_mismatch_flag: int = 0,
) -> float:
    """Documented heuristic: add fixed uplifts for agent-flagged issues.

    Kept separate from the model so the statistical estimate stays honest;
    callers should surface both numbers.
    """
    prob = base_prob
    if documentation_complete == 0:
        prob += UPLIFT_DOC_MISSING
    if clinical_justification_present == 0:
        prob += UPLIFT_NO_JUSTIFICATION
    if procedure_mismatch_flag == 1:
        prob += UPLIFT_PROCEDURE_MISMATCH
    return round(min(prob, PROB_CAP), 4)


def predict_denial_probability(features: dict) -> float:
    """Backward-compatible entry point used by the API layer.

    Expects at minimum {"cpt_code": ...}; agent flags are optional.
    """
    base = predict_base_probability(str(features.get("cpt_code", "")))
    return adjust_for_agent_findings(
        base,
        documentation_complete=int(features.get("documentation_complete", 1)),
        clinical_justification_present=int(
            features.get("clinical_justification_present", 1)
        ),
        procedure_mismatch_flag=int(features.get("procedure_mismatch_flag", 0)),
    )
