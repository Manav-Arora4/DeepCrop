"""
Sensor-only features for the tomato disease models (one of the three scorers in the fusion).

Every feature at observation t uses only that plant's readings at or before t, so a model can
never see the future. Columns that would leak the label are never used: treatment_applied
(only applied to plants already diseased), notes, severity, leaf counts, and the derived
future_* / *_observation_date columns.
"""

from pathlib import Path

import numpy as np
import pandas as pd

OBSERVATIONS = Path("data/user_collected/tomato/observations.csv")

GROWTH_STAGES = ["seedling", "vegetative", "flowering", "fruit_development", "maturity"]

FEATURES = [
    "temperature_c", "humidity_pct", "soil_moisture_pct", "vpd_kpa",
    "humidity_mean_3", "humidity_max_3", "hours_humid_proxy_3", "temperature_mean_3",
    "moisture_mean_3", "moisture_change_1", "ph_mv_vs_baseline",
    "watered_last_24h", "growth_stage_idx",
]


def vpd_kpa(temp_c: pd.Series, rh: pd.Series) -> pd.Series:
    """Vapour pressure deficit (kPa), Tetens formula. Low VPD = humid leaf surface, favours fungi."""
    es = 0.61078 * np.exp(17.27 * temp_c / (temp_c + 237.3))
    return es * (1 - rh / 100)


def load_observations(path: Path = OBSERVATIONS) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["ts"] = pd.to_datetime(df["timestamp"])
    return df.sort_values(["plant_id", "ts"]).reset_index(drop=True)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add FEATURES columns; rolling windows are per plant over the last 3 observations incl. t."""
    out = df.copy()
    out["vpd_kpa"] = vpd_kpa(out["temperature_c"], out["humidity_pct"])
    g = out.groupby("plant_id", group_keys=False)
    roll = lambda col, fn: g[col].apply(lambda s: getattr(s.rolling(3, min_periods=1), fn)())
    out["humidity_mean_3"] = roll("humidity_pct", "mean")
    out["humidity_max_3"] = roll("humidity_pct", "max")
    # Count of the last 3 observations above 85% RH: a proxy for leaf-wetness duration
    out["hours_humid_proxy_3"] = g["humidity_pct"].apply(lambda s: (s > 85).astype(float).rolling(3, min_periods=1).sum())
    out["temperature_mean_3"] = roll("temperature_c", "mean")
    out["moisture_mean_3"] = roll("soil_moisture_pct", "mean")
    out["moisture_change_1"] = g["soil_moisture_pct"].diff().fillna(0.0)
    # pH probe is uncalibrated: use each plant's deviation from its own running mean of past readings
    out["ph_mv_vs_baseline"] = g["soil_ph_mv"].apply(lambda s: s - s.expanding().mean().shift(1).fillna(s.iloc[0]))
    out["watered_last_24h"] = (out["watered_last_24h"].astype(str).str.lower() == "yes").astype(float)
    out["growth_stage_idx"] = out["growth_stage"].map({s: i for i, s in enumerate(GROWTH_STAGES)}).astype(float)
    return out


def detection_set(df: pd.DataFrame):
    """Task 1: is the plant diseased now? (unsure rows excluded)"""
    d = df[df["disease_status"].isin(["healthy", "diseased"])]
    return d, (d["disease_status"] == "diseased").astype(int)


def risk_set(df: pd.DataFrame, horizon: int = 7):
    """Task 2: will a currently healthy plant be observed diseased within `horizon` days? (blank labels excluded)"""
    col = f"future_disease_{horizon}d"
    d = df[(df["disease_status"] == "healthy") & df[col].notna()]
    return d, d[col].astype(int)
