"""Shared dataset loading for Phase 4 models.

Loads player_features (a given feature-set version) into a flat DataFrame:
context columns + expanded feature vector + target(s). Time-based split helper
avoids leakage (train on earlier seasons, test on the latest).
"""

from __future__ import annotations

import pandas as pd

from app.db.session import get_engine

ARTIFACT_ROOT = "ml/artifacts"


def load_features(version: str = "v1") -> pd.DataFrame:
    """One row per player-season with context + flattened feature vector.

    market_value_eur numeric-NaN (missing valuation) is coerced to NULL here.
    """
    eng = get_engine()
    df = pd.read_sql(
        "select pf.player_id, pf.season_id, s.start_year, s.label as season_label, "
        "pf.league_id, pf.position_group, pf.age, pf.minutes, pf.matches, "
        "pf.club_elo, pf.league_strength, "
        "nullif(pf.market_value_eur, 'NaN')::numeric as market_value_eur, pf.features "
        f"from player_features pf join seasons s on s.id = pf.season_id "
        f"where pf.feature_set_version = '{version}'",
        eng,
    )
    feats = pd.json_normalize(df["features"]).apply(pd.to_numeric, errors="coerce")
    out = pd.concat([df.drop(columns=["features"]), feats], axis=1)
    out["market_value_eur"] = pd.to_numeric(out["market_value_eur"], errors="coerce")
    return out


# the 5 base rate features (everything else base is a *_p90 count)
RATE_FEATURES = {
    "pass_cmp_pct", "shot_accuracy", "take_on_pct", "aerial_win_pct", "np_g_per_shot",
}


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Base per-90/rate feature columns only.

    Inclusion-based (match *_p90 or a known rate) so model-added columns
    (labels, dates, targets, context) can never leak in as features. Percentile
    columns end in _pct_pos/_pct_lg and so are excluded by the _p90 test.
    """
    return [c for c in df.columns if c.endswith("_p90") or c in RATE_FEATURES]


def time_split(df: pd.DataFrame, test_start_year: int, val_start_year: int | None = None):
    """Split by season start_year. Returns (train, val, test); val may be empty."""
    test = df[df["start_year"] == test_start_year]
    if val_start_year is not None:
        val = df[df["start_year"] == val_start_year]
        train = df[df["start_year"] < val_start_year]
    else:
        val = df.iloc[0:0]
        train = df[df["start_year"] < test_start_year]
    return train, val, test
