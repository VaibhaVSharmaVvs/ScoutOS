"""Phase 2c: load facts into the normalized schema, linked via entity_xref.

- player_season_stats: FBref (10 categories merged into a JSONB blob + promoted
  core metrics) and Understat (xG suite), one source-tagged row each.
- market_values / transfers: Transfermarkt, joined to canonical players via the
  TM xref (only players we resolved get facts).
- club_strength: ClubElo snapshots, joined to clubs by clubelo_name.

Idempotent: each fact table is truncated before load. Run after players:
    python -m etl.load --step facts
"""

from __future__ import annotations

import glob

import pandas as pd
from sqlalchemy import delete, select

from app.db.models import (
    Club,
    ClubStrength,
    EntityXref,
    League,
    MarketValue,
    PlayerSeasonStats,
    Season,
    Transfer,
)
from etl.load.db import SessionLocal, log
from etl.load.normalize import normalize_name

FBREF_CATS = [
    "standard", "shooting", "passing", "passing_types", "gca",
    "defense", "possession", "playing_time", "misc", "keeper",
]
FBREF_ID_COLS = {"league", "season", "team", "player", "nation", "pos", "age", "born"}
UNDERSTAT = "data/raw/understat/player_season.parquet"
CLUBELO_GLOB = "data/raw/clubelo/by_date/*.parquet"
TM_VALUATIONS = "data/raw/transfermarkt/player_valuations.csv"
TM_TRANSFERS = "data/raw/transfermarkt/transfers.csv"


def _dedup_pss(rows: list[dict]) -> list[dict]:
    """Collapse rows colliding on (player_id, season_id, club_id, source),
    keeping the one with the most minutes (matches the unique constraint)."""
    best: dict[tuple, dict] = {}
    for r in rows:
        k = (r["player_id"], r["season_id"], r["club_id"], r["source"])
        cur = best.get(k)
        if cur is None or (r["minutes"] or -1) > (cur["minutes"] or -1):
            best[k] = r
    return list(best.values())


def _clean(v):
    """JSON-safe scalar: NaN/NaT -> None, numpy -> native."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if hasattr(v, "item"):
        try:
            v = v.item()
        except Exception:  # noqa: BLE001
            pass
    if isinstance(v, float) and pd.isna(v):
        return None
    return v


def _lookups(session):
    fbref = {x.source_key: x.player_id
             for x in session.scalars(select(EntityXref).where(EntityXref.source == "fbref"))}
    understat = {x.source_id: x.player_id
                 for x in session.scalars(select(EntityXref).where(EntityXref.source == "understat"))}
    tm = {x.source_id: x.player_id
          for x in session.scalars(select(EntityXref).where(EntityXref.source == "transfermarkt"))}
    clubs = session.scalars(select(Club)).all()
    club_by_fbref = {c.fbref_name: c.id for c in clubs if c.fbref_name}
    club_by_understat = {c.understat_id: c.id for c in clubs if c.understat_id is not None}
    club_by_tm = {c.transfermarkt_id: c.id for c in clubs if c.transfermarkt_id is not None}
    club_by_elo = {c.clubelo_name: c.id for c in clubs if c.clubelo_name}
    leagues = {l.code: l.id for l in session.scalars(select(League))}
    seasons = {s.code: s.id for s in session.scalars(select(Season))}
    return dict(fbref=fbref, understat=understat, tm=tm, club_by_fbref=club_by_fbref,
                club_by_understat=club_by_understat, club_by_tm=club_by_tm,
                club_by_elo=club_by_elo, leagues=leagues, seasons=seasons)


# --- player_season_stats ------------------------------------------------------
def _load_player_season_stats(session, lk) -> None:
    # Merge the 10 FBref categories into one record per (player, season, team).
    merged: dict[tuple, dict] = {}
    for cat in FBREF_CATS:
        path = f"data/raw/fbref/player_season/{cat}.parquet"
        df = pd.read_parquet(path)
        stat_cols = [c for c in df.columns if c not in FBREF_ID_COLS]
        for d in df.to_dict(orient="records"):  # preserves column names with spaces
            if pd.isna(d.get("born")) or not d.get("player"):
                continue
            key = (normalize_name(d["player"]), int(d["born"]), d["team"], d["season"])
            rec = merged.setdefault(key, {"season": d["season"], "team": d["team"],
                                          "born": int(d["born"]), "norm": normalize_name(d["player"]),
                                          "pos": d.get("pos"), "stats": {}})
            for col in stat_cols:
                rec["stats"][f"{cat}:{col}"] = _clean(d[col])

    rows = []
    unresolved = 0
    for rec in merged.values():
        pid = lk["fbref"].get(f"{rec['norm']}|{rec['born']}")
        if pid is None:
            unresolved += 1
            continue
        st = rec["stats"]
        rows.append({
            "player_id": pid,
            "club_id": lk["club_by_fbref"].get(rec["team"]),
            "league_id": None,  # FBref combined rows lack a clean single league here
            "season_id": lk["seasons"].get(rec["season"]),
            "source": "fbref",
            "minutes": st.get("standard:Playing Time_Min"),
            "matches": st.get("standard:Playing Time_MP"),
            "goals": st.get("standard:Performance_Gls"),
            "assists": st.get("standard:Performance_Ast"),
            "xg": st.get("shooting:Expected_xG"),
            "xa": None,
            "position": rec["pos"],
            "stats": st,
        })
    rows = _dedup_pss(rows)
    session.bulk_insert_mappings(PlayerSeasonStats, rows)
    log.info("player_season_stats FBref: %d rows (%d unresolved players skipped)", len(rows), unresolved)

    # Understat
    us = pd.read_parquet(UNDERSTAT)
    us_rows = []
    us_unresolved = 0
    for r in us.itertuples(index=False):
        pid = lk["understat"].get(str(int(r.player_id)))
        if pid is None:
            us_unresolved += 1
            continue
        us_rows.append({
            "player_id": pid,
            "club_id": lk["club_by_understat"].get(int(r.team_id)),
            "league_id": lk["leagues"].get(r.league),
            "season_id": lk["seasons"].get(r.season),
            "source": "understat",
            "minutes": _clean(r.minutes), "matches": _clean(r.matches),
            "goals": _clean(r.goals), "assists": _clean(r.assists),
            "xg": _clean(r.xg), "xa": _clean(r.xa), "position": _clean(r.position),
            "stats": {k: _clean(getattr(r, k)) for k in
                      ("np_goals", "np_xg", "shots", "key_passes", "xg_chain", "xg_buildup",
                       "yellow_cards", "red_cards")},
        })
    us_rows = _dedup_pss(us_rows)
    session.bulk_insert_mappings(PlayerSeasonStats, us_rows)
    log.info("player_season_stats Understat: %d rows (%d unresolved skipped)", len(us_rows), us_unresolved)


# --- market values ------------------------------------------------------------
def _load_market_values(session, lk) -> None:
    mv = pd.read_csv(TM_VALUATIONS)
    mv = mv.dropna(subset=["player_id", "date"])
    mv["pid"] = mv["player_id"].astype(int).astype(str).map(lk["tm"])
    mv = mv.dropna(subset=["pid"]).drop_duplicates(subset=["pid", "date"])
    rows = [{
        "player_id": int(r.pid), "as_of": r.date,
        "value_eur": _clean(r.market_value_in_eur),
        "club_id": lk["club_by_tm"].get(int(r.current_club_id)) if pd.notna(r.current_club_id) else None,
    } for r in mv.itertuples(index=False)]
    session.bulk_insert_mappings(MarketValue, rows)
    log.info("market_values: %d rows for %d players", len(rows), mv["pid"].nunique())


# --- transfers ----------------------------------------------------------------
def _load_transfers(session, lk) -> None:
    tr = pd.read_csv(TM_TRANSFERS)
    tr["pid"] = tr["player_id"].astype("Int64").astype(str).map(lk["tm"])
    tr = tr.dropna(subset=["pid"])
    rows = [{
        "player_id": int(r.pid), "transfer_date": _clean(r.transfer_date),
        "season_label": _clean(r.transfer_season),
        "from_club_id": lk["club_by_tm"].get(int(r.from_club_id)) if pd.notna(r.from_club_id) else None,
        "to_club_id": lk["club_by_tm"].get(int(r.to_club_id)) if pd.notna(r.to_club_id) else None,
        "fee_eur": _clean(r.transfer_fee), "market_value_eur": _clean(r.market_value_in_eur),
    } for r in tr.itertuples(index=False)]
    session.bulk_insert_mappings(Transfer, rows)
    log.info("transfers: %d rows", len(rows))


# --- club strength (ClubElo) --------------------------------------------------
def _load_club_strength(session, lk) -> None:
    frames = [pd.read_parquet(f) for f in glob.glob(CLUBELO_GLOB)]
    ce = pd.concat(frames).drop_duplicates(subset=["team", "snapshot_date"])
    rows = [{
        "club_id": lk["club_by_elo"].get(r.team), "clubelo_name": r.team,
        "snapshot_date": r.snapshot_date, "elo": _clean(r.elo),
        "rank": int(r.rank) if pd.notna(r.rank) else None,
        "country": _clean(r.country), "league_code": _clean(r.league),
    } for r in ce.itertuples(index=False)]
    session.bulk_insert_mappings(ClubStrength, rows)
    matched = sum(1 for x in rows if x["club_id"] is not None)
    log.info("club_strength: %d rows (%d linked to a club)", len(rows), matched)


def run() -> None:
    session = SessionLocal()
    try:
        lk = _lookups(session)
        # idempotent: clear facts
        for model in (PlayerSeasonStats, MarketValue, Transfer, ClubStrength):
            session.execute(delete(model))
        session.commit()

        _load_player_season_stats(session, lk)
        _load_club_strength(session, lk)
        _load_market_values(session, lk)
        _load_transfers(session, lk)
        session.commit()
        log.info("facts loaded.")
    finally:
        session.close()
