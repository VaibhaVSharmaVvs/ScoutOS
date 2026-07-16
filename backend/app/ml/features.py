"""Build model inputs for a player from the stored player_features rows.

`latest_feature_row` returns the player's most recent feature-season as a flat
dict (JSONB style features + promoted context), which is exactly the shape the
value/potential/position explainers expect.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import text

from app.db.session import get_engine

FEATURE_SET_VERSION = "v1"

_ROW_SQL = text(
    "select s.start_year, s.label as season, pf.league_id, pf.club_id, "
    "pf.position_group, pf.age, pf.minutes, pf.matches, pf.club_elo, "
    "pf.league_strength, pl.foot, "
    "nullif(pf.market_value_eur, 'NaN')::numeric as market_value_eur, pf.features "
    "from player_features pf join seasons s on s.id = pf.season_id "
    "join players pl on pl.id = pf.player_id "
    "where pf.feature_set_version = :v and pf.player_id = :pid "
    "order by s.start_year desc limit 1"
)


def latest_feature_row(player_id: int, version: str = FEATURE_SET_VERSION) -> dict | None:
    """Latest-season features + context as one flat dict, or None if the player
    has no feature row. Adds ``cur_value_log`` (potential-model input) when a
    market value is known."""
    df = pd.read_sql(_ROW_SQL, get_engine(), params={"v": version, "pid": player_id})
    if df.empty:
        return None
    row = df.iloc[0]
    out: dict = dict(row["features"] or {})
    mv = pd.to_numeric(row["market_value_eur"], errors="coerce")
    out.update(
        age=row["age"], minutes=row["minutes"], matches=row["matches"],
        club_elo=row["club_elo"], league_strength=row["league_strength"],
        position_group=row["position_group"], league_id=row["league_id"],
        club_id=None if pd.isna(row["club_id"]) else int(row["club_id"]),
        foot=row["foot"], season=row["season"], start_year=int(row["start_year"]),
        market_value_eur=None if pd.isna(mv) else float(mv),
        cur_value_log=None if pd.isna(mv) else float(np.log1p(float(mv))),
    )
    return out


def position_frame(feature_row: dict, meta: dict) -> pd.DataFrame:
    """One-row DataFrame matching a position model's feature contract.

    Style columns are coerced numeric; `foot` (side model only) is filled from
    the feature row, defaulting to 'unknown'.
    """
    cols = meta["feature_cols"]
    cats = meta.get("cats", [])
    X = pd.DataFrame([feature_row]).reindex(columns=cols)
    for c in cols:
        if c in cats:
            X[c] = X[c].fillna("unknown").astype(str)
        else:
            X[c] = pd.to_numeric(X[c], errors="coerce")
    return X
