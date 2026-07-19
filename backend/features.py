"""Feature engineering shared between training (scripts/train.py) and serving."""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List

import pandas as pd

LEGACY_FEATURE_COLUMNS = [
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

FEATURE_COLUMNS = LEGACY_FEATURE_COLUMNS + [
    "hcpcs_family_idx",
    "provider_freq_log",
    "tob_freq_log",
    "hcpcs_part_rate",
]

SMOOTHING_M = 50.0


def active_feature_columns(maps: Dict[str, Any]) -> List[str]:
    stored = maps.get("feature_columns")
    if stored:
        return list(stored)
    if "hcpcs_family_levels" in maps:
        return FEATURE_COLUMNS
    return LEGACY_FEATURE_COLUMNS


def smoothed_rate(positives: float, count: float, prior: float, m: float = SMOOTHING_M) -> float:
    return (positives + m * prior) / (count + m)


def fit_feature_maps(df: pd.DataFrame, label_col: str = "label") -> Dict[str, Any]:
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
    maps["provider_freq"] = df["provider_type"].value_counts().to_dict()
    maps["tob_freq"] = df["type_of_bill"].value_counts().to_dict()
    maps["part_levels"] = sorted(df["part"].dropna().unique().tolist())
    maps["hcpcs_first_levels"] = sorted({str(h)[:1] for h in df["hcpcs"].dropna() if str(h)})
    maps["hcpcs_family_levels"] = sorted({str(h)[:2] for h in df["hcpcs"].dropna() if str(h)})
    maps["feature_columns"] = FEATURE_COLUMNS
    return maps


def _build_feature_frame(df: pd.DataFrame, maps: Dict[str, Any]) -> pd.DataFrame:
    prior = maps["prior"]
    part_index = {lvl: i for i, lvl in enumerate(maps["part_levels"])}
    first_index = {lvl: i for i, lvl in enumerate(maps["hcpcs_first_levels"])}

    out = pd.DataFrame(index=df.index)
    out["part_idx"] = df["part"].map(part_index).fillna(-1).astype(int)
    out["hcpcs_first_idx"] = df["hcpcs"].astype(str).str[:1].map(first_index).fillna(-1).astype(int)
    out["has_drg"] = (df["drg"].astype(str).str.strip() != "").astype(int)
    out["tob_present"] = (df["type_of_bill"].astype(str).str.strip() != "").astype(int)
    out["hcpcs_rate"] = df["hcpcs"].map(maps["hcpcs_rates"]).fillna(prior)
    out["provider_rate"] = df["provider_type"].map(maps["provider_rates"]).fillna(prior)
    out["tob_rate"] = df["type_of_bill"].map(maps["tob_rates"]).fillna(prior)
    out["part_rate"] = df["part"].map(maps["part_rates"]).fillna(prior)
    out["hcpcs_freq_log"] = df["hcpcs"].map(maps["hcpcs_freq"]).fillna(0).astype(float).apply(math.log1p)

    if "hcpcs_family_levels" in maps:
        family_index = {lvl: i for i, lvl in enumerate(maps["hcpcs_family_levels"])}
        out["hcpcs_family_idx"] = df["hcpcs"].astype(str).str[:2].map(family_index).fillna(-1).astype(int)
        out["provider_freq_log"] = df["provider_type"].map(maps.get("provider_freq", {})).fillna(0).astype(float).apply(math.log1p)
        out["tob_freq_log"] = df["type_of_bill"].map(maps.get("tob_freq", {})).fillna(0).astype(float).apply(math.log1p)
        out["hcpcs_part_rate"] = out["hcpcs_rate"] * out["part_rate"]

    return out


def apply_features(df: pd.DataFrame, maps: Dict[str, Any]) -> pd.DataFrame:
    cols = active_feature_columns(maps)
    frame = _build_feature_frame(df, maps)
    return frame[cols]


def build_serving_row(
    maps: Dict[str, Any],
    hcpcs: str,
    part: str = "1. Part B",
    provider_type: str = "",
    type_of_bill: str = "",
    drg: str = "",
) -> pd.DataFrame:
    df = pd.DataFrame([{
        "hcpcs": str(hcpcs).strip().upper(),
        "part": part,
        "provider_type": provider_type,
        "type_of_bill": type_of_bill,
        "drg": drg,
    }])
    return apply_features(df, maps)


def save_feature_maps(maps: Dict[str, Any], path: str) -> None:
    with open(path, "w") as f:
        json.dump(maps, f)


def load_feature_maps(path: str) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)
