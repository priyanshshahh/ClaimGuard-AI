"""Feature engineering shared between training (scripts/train.py) and serving.

The model is trained on the CMS Medicare Fee-for-Service Comprehensive Error
Rate Testing (CERT) public dataset. Each row is a reviewed claim line with a
real audit outcome: Review Decision == "Disagree" means the CERT reviewer
determined the claim was improperly paid (insufficient documentation, medical
necessity, incorrect coding, ...). We use that determination as the training
label - a documented proxy for denial risk, since the same failure modes
drive both payer denials and improper-payment findings.

Raw columns used: Part, HCPCS Procedure Code, Provider Type, Type of Bill, DRG.
Encodings (smoothed target rates, frequency counts) are computed on the
TRAINING years only and shipped alongside the model in feature_maps.json.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict

import pandas as pd

# Order matters: this is the model's input schema.
FEATURE_COLUMNS = [
    "part_idx",
    "hcpcs_first_idx",
    "has_drg",
    "tob_present",
    "hcpcs_rate",
    "provider_rate",
    "tob_rate",
    "part_rate",
    "hcpcs_freq_log",
]

SMOOTHING_M = 50.0  # m-estimate smoothing for target encodings


def smoothed_rate(positives: float, count: float, prior: float, m: float = SMOOTHING_M) -> float:
    """m-estimate smoothed positive rate; falls back to prior for rare levels."""
    return (positives + m * prior) / (count + m)


def fit_feature_maps(df: pd.DataFrame, label_col: str = "label") -> Dict[str, Any]:
    """Compute all categorical encodings from the TRAINING split only."""
    prior = float(df[label_col].mean())
    maps: Dict[str, Any] = {"prior": prior}

    for col, key in [
        ("hcpcs", "hcpcs_rates"),
        ("provider_type", "provider_rates"),
        ("type_of_bill", "tob_rates"),
        ("part", "part_rates"),
    ]:
        grp = df.groupby(col)[label_col].agg(["sum", "count"])
        maps[key] = {
            str(level): smoothed_rate(row["sum"], row["count"], prior)
            for level, row in grp.iterrows()
        }

    maps["hcpcs_freq"] = df["hcpcs"].value_counts().to_dict()
    maps["part_levels"] = sorted(df["part"].dropna().unique().tolist())
    maps["hcpcs_first_levels"] = sorted(
        {str(h)[:1] for h in df["hcpcs"].dropna() if str(h)}
    )
    return maps


def apply_features(df: pd.DataFrame, maps: Dict[str, Any]) -> pd.DataFrame:
    """Vectorised feature construction for a normalised CERT frame."""
    prior = maps["prior"]
    part_index = {lvl: i for i, lvl in enumerate(maps["part_levels"])}
    first_index = {lvl: i for i, lvl in enumerate(maps["hcpcs_first_levels"])}

    out = pd.DataFrame(index=df.index)
    out["part_idx"] = df["part"].map(part_index).fillna(-1).astype(int)
    out["hcpcs_first_idx"] = (
        df["hcpcs"].astype(str).str[:1].map(first_index).fillna(-1).astype(int)
    )
    out["has_drg"] = (df["drg"].astype(str).str.strip() != "").astype(int)
    out["tob_present"] = (df["type_of_bill"].astype(str).str.strip() != "").astype(int)
    out["hcpcs_rate"] = df["hcpcs"].map(maps["hcpcs_rates"]).fillna(prior)
    out["provider_rate"] = df["provider_type"].map(maps["provider_rates"]).fillna(prior)
    out["tob_rate"] = df["type_of_bill"].map(maps["tob_rates"]).fillna(prior)
    out["part_rate"] = df["part"].map(maps["part_rates"]).fillna(prior)
    out["hcpcs_freq_log"] = (
        df["hcpcs"].map(maps["hcpcs_freq"]).fillna(0).astype(float).apply(math.log1p)
    )
    return out[FEATURE_COLUMNS]


def build_serving_row(
    maps: Dict[str, Any],
    hcpcs: str,
    part: str = "1. Part B",
    provider_type: str = "",
    type_of_bill: str = "",
    drg: str = "",
) -> pd.DataFrame:
    """Build a single-row feature frame for online scoring.

    The API receives professional claims keyed by CPT code (CPT is HCPCS
    Level I), so `part` defaults to Part B. Unknown provider type / type of
    bill fall back to the training prior via apply_features.
    """
    df = pd.DataFrame(
        [
            {
                "hcpcs": str(hcpcs).strip().upper(),
                "part": part,
                "provider_type": provider_type,
                "type_of_bill": type_of_bill,
                "drg": drg,
            }
        ]
    )
    return apply_features(df, maps)


def save_feature_maps(maps: Dict[str, Any], path: str) -> None:
    with open(path, "w") as f:
        json.dump(maps, f)


def load_feature_maps(path: str) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)
