"""Phase 3 feature engineering: build the versioned player_features table.

Merges the per-source player_season_stats rows into one feature vector per
player-season:
  - fbref_kaggle -> detailed counting stats (tackles, prog passes/carries, SCA…)
  - understat    -> xG suite (xg, xa, npxg, xg_chain, xg_buildup)
Aggregates across mid-season club moves, computes per-90 and rate features,
attaches context (age, club Elo, league strength, market-value target), and
writes player_features (JSONB feature vector + promoted context).

Run from repo root (after the load stage):  python -m ml.features.build
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import delete, select

from app.db.models import (
    Club,
    ClubStrength,
    League,
    MarketValue,
    Player,
    PlayerFeatures,
    PlayerSeasonStats,
    Season,
)
from app.db.session import SessionLocal, get_engine
from etl.load.db import log

FEATURE_SET_VERSION = "v1"

# fbref_kaggle counting stats -> summed across clubs, then per-90
FK_COUNTS = [
    "goals", "assists", "shots", "sot", "sca", "gca", "tackles", "tackles_won",
    "interceptions", "tkl_plus_int", "blocks", "clearances", "dribblers_challenged",
    "pass_cmp", "pass_att", "pass_prog", "prog_pass_dist", "pass_final_third",
    "key_passes", "ppa", "carries", "carries_prog", "carries_prog_dist",
    "take_ons_att", "take_ons_succ", "touches", "prog_rec", "recoveries",
    "aerials_won", "aerials_lost", "fouls", "fouled", "npxg", "xag",
]
# understat xG-flavour counting stats
US_COUNTS = ["xg", "xa", "np_xg", "xg_chain", "xg_buildup"]

# metrics turned into per-90 rates (value per 90 minutes)
PER90 = FK_COUNTS + US_COUNTS


def _pos_group(pos: str | None) -> str:
    p = (pos or "").lower()
    if "goalkeep" in p or p == "gk":
        return "GK"
    if "back" in p or "defend" in p or p.startswith("df") or p == "cb":
        return "DEF"
    if "midfield" in p or "mid" in p or p.startswith("mf"):
        return "MID"
    if any(k in p for k in ("forward", "wing", "striker", "attack", "fw")):
        return "FWD"
    return "UNK"


def _expand(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Expand the JSONB `stats` column into flat numeric columns for `keys`."""
    stats = pd.json_normalize(df["stats"]).reindex(columns=keys)
    out = df.drop(columns=["stats"]).reset_index(drop=True)
    return pd.concat([out, stats.reset_index(drop=True)], axis=1)


def _source_df(eng, source: str) -> pd.DataFrame:
    assert source in ("fbref_kaggle", "understat")  # literal, no injection risk
    q = (
        "select player_id, season_id, club_id, league_id, minutes, matches, "
        "goals, assists, xg, xa, position, stats "
        f"from player_season_stats where source = '{source}'"
    )
    return pd.read_sql(q, eng)


def build() -> None:
    eng = get_engine()

    # --- fbref_kaggle: detailed counting stats, aggregated per player-season ---
    fk = _source_df(eng, "fbref_kaggle")
    fk_json = [c for c in FK_COUNTS if c not in ("goals", "assists")]
    fk = _expand(fk, fk_json)
    # promoted goals/assists already columns; JSON has its own goals/assists too -> keep promoted
    fk_sum_cols = ["minutes", "matches", "goals", "assists"] + fk_json
    # primary club/league = the club-row with most minutes
    fk = fk.sort_values("minutes", ascending=False)
    primary = fk.drop_duplicates(subset=["player_id", "season_id"])[
        ["player_id", "season_id", "club_id", "league_id", "position"]
    ]
    fk_agg = fk.groupby(["player_id", "season_id"], as_index=False)[fk_sum_cols].sum(min_count=1)
    fk_agg = fk_agg.merge(primary, on=["player_id", "season_id"], how="left")

    # --- understat: xG suite ---
    us = _source_df(eng, "understat")
    us = _expand(us, ["np_xg", "xg_chain", "xg_buildup"])
    us["xg"] = pd.to_numeric(us["xg"], errors="coerce")
    us["xa"] = pd.to_numeric(us["xa"], errors="coerce")
    us_sum = ["xg", "xa", "np_xg", "xg_chain", "xg_buildup"]
    us_agg = us.groupby(["player_id", "season_id"], as_index=False)[us_sum].sum(min_count=1)

    df = fk_agg.merge(us_agg, on=["player_id", "season_id"], how="left")
    log.info("feature base: %d player-seasons (fbref_kaggle) + understat xG merged", len(df))

    # --- context: age, market value, club Elo, league strength ---
    with SessionLocal() as s:
        seasons = {row.id: row.start_year for row in s.scalars(select(Season))}
        births = {row.id: row.birth_year for row in s.scalars(select(Player))}
        mvals = pd.read_sql("select player_id, as_of, value_eur from market_values", eng)
        elo = pd.read_sql(
            "select club_id, snapshot_date, elo from club_strength where club_id is not null", eng
        )

    df["start_year"] = df["season_id"].map(seasons)
    df["birth_year"] = df["player_id"].map(births)
    df["age"] = df["start_year"] - df["birth_year"]

    # club Elo: snapshot in the summer after the season (start_year+1)
    elo["yr"] = pd.to_datetime(elo["snapshot_date"]).dt.year
    elo_lookup = {(r.club_id, r.yr): r.elo for r in elo.itertuples(index=False)}
    df["club_elo"] = [elo_lookup.get((c, y + 1)) for c, y in zip(df["club_id"], df["start_year"])]
    # league strength = mean club Elo of that league-season's primary clubs
    ls = df.groupby(["league_id", "season_id"])["club_elo"].transform("mean")
    df["league_strength"] = ls

    # market value: latest valuation within the season window [Aug start .. Jul next]
    mvals["as_of"] = pd.to_datetime(mvals["as_of"])
    mv_by_player: dict[int, pd.DataFrame] = {pid: g.sort_values("as_of")
                                             for pid, g in mvals.groupby("player_id")}

    def _mv(pid, sy):
        g = mv_by_player.get(pid)
        if g is None:
            return None
        lo, hi = pd.Timestamp(f"{sy}-08-01"), pd.Timestamp(f"{sy + 1}-07-31")
        win = g[(g["as_of"] >= lo) & (g["as_of"] <= hi)]
        row = win.iloc[-1] if len(win) else (g[g["as_of"] <= hi].iloc[-1] if (g["as_of"] <= hi).any() else None)
        return None if row is None else int(row["value_eur"]) if pd.notna(row["value_eur"]) else None

    df["market_value_eur"] = [_mv(p, y) for p, y in zip(df["player_id"], df["start_year"])]

    # youth-value / potential signals (value_v2)
    pl = pd.read_sql(
        "select id as player_id, international_caps, contract_expiration, "
        "highest_market_value_eur from players", eng)
    df = df.merge(pl, on="player_id", how="left")
    df["intl_caps"] = pd.to_numeric(df["international_caps"], errors="coerce")
    contract_yr = pd.to_datetime(df["contract_expiration"], errors="coerce").dt.year
    df["contract_years"] = (contract_yr - (df["start_year"] + 1)).clip(lower=0)
    df["highest_value_log"] = np.log1p(pd.to_numeric(df["highest_market_value_eur"], errors="coerce"))

    df["position_group"] = [_pos_group(p) for p in df["position"]]

    # --- base features (per-90 + rates), vectorized into a DataFrame ---
    n90 = (pd.to_numeric(df["minutes"], errors="coerce") / 90).where(lambda x: x > 0)
    feat = pd.DataFrame(index=df.index)
    for c in PER90:
        feat[f"{c}_p90"] = pd.to_numeric(df[c], errors="coerce") / n90

    def _ratio(a, b):
        bv = pd.to_numeric(df[b], errors="coerce")
        return pd.to_numeric(df[a], errors="coerce") / bv.where(bv > 0)

    feat["pass_cmp_pct"] = _ratio("pass_cmp", "pass_att")
    feat["shot_accuracy"] = _ratio("sot", "shots")
    feat["take_on_pct"] = _ratio("take_ons_succ", "take_ons_att")
    aw = pd.to_numeric(df["aerials_won"], errors="coerce")
    al = pd.to_numeric(df["aerials_lost"], errors="coerce")
    feat["aerial_win_pct"] = aw / (aw + al).where((aw + al) > 0)
    feat["np_g_per_shot"] = _ratio("goals", "shots")
    base_cols = list(feat.columns)

    # --- percentiles within (season, position_group) and (season, league) ---
    g = feat.copy()
    g["_season"], g["_pos"], g["_lg"] = df["season_id"], df["position_group"], df["league_id"]
    pct = pd.DataFrame(index=df.index)
    for c in base_cols:
        pct[f"{c}_pct_pos"] = g.groupby(["_season", "_pos"])[c].rank(pct=True)
        pct[f"{c}_pct_lg"] = g.groupby(["_season", "_lg"])[c].rank(pct=True)

    # --- assemble features JSONB per row (NaN -> None) ---
    def _r(x, nd):
        return round(float(x), nd) if pd.notna(x) else None

    youth_cols = ["intl_caps", "contract_years", "highest_value_log"]
    feats: list[dict] = []
    for i in df.index:
        row = {c: _r(feat.at[i, c], 4) for c in base_cols}
        row.update({c: _r(pct.at[i, c], 3) for c in pct.columns})
        row.update({c: _r(df.at[i, c], 3) for c in youth_cols})
        feats.append(row)
    df["features"] = feats
    log.info("features: %d base + %d percentile + %d youth keys per row",
             len(base_cols), len(pct.columns), len(youth_cols))

    # --- write player_features ---
    with SessionLocal() as s:
        s.execute(delete(PlayerFeatures).where(
            PlayerFeatures.feature_set_version == FEATURE_SET_VERSION))
        s.commit()
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "player_id": int(r["player_id"]), "season_id": int(r["season_id"]),
                "club_id": int(r["club_id"]) if pd.notna(r["club_id"]) else None,
                "league_id": int(r["league_id"]) if pd.notna(r["league_id"]) else None,
                "feature_set_version": FEATURE_SET_VERSION,
                "age": float(r["age"]) if pd.notna(r["age"]) else None,
                "minutes": int(r["minutes"]) if pd.notna(r["minutes"]) else None,
                "matches": int(r["matches"]) if pd.notna(r["matches"]) else None,
                "position": r["position"],
                "position_group": _pos_group(r["position"]),
                "club_elo": float(r["club_elo"]) if pd.notna(r["club_elo"]) else None,
                "league_strength": float(r["league_strength"]) if pd.notna(r["league_strength"]) else None,
                "market_value_eur": (int(r["market_value_eur"])
                                     if pd.notna(r["market_value_eur"]) else None),
                "features": r["features"],
            })
        s.bulk_insert_mappings(PlayerFeatures, rows)
        s.commit()
    log.info("player_features written: %d rows (version=%s, %d features each)",
             len(df), FEATURE_SET_VERSION, len(PER90) + 5)


if __name__ == "__main__":
    build()
