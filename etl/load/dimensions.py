"""Load reference dimensions: leagues and seasons. Idempotent (upsert by key)."""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import League, Season
from etl.load.db import SessionLocal, log

# soccerdata league code -> (display name, country, Transfermarkt competition code)
LEAGUES = {
    "ENG-Premier League": ("Premier League", "England", "GB1"),
    "ESP-La Liga": ("La Liga", "Spain", "ES1"),
    "ITA-Serie A": ("Serie A", "Italy", "IT1"),
    "GER-Bundesliga": ("Bundesliga", "Germany", "L1"),
    "FRA-Ligue 1": ("Ligue 1", "France", "FR1"),
}

# soccerdata season code -> (label, start_year).
# THIS MAP IS THE ACTIVE-SEASON ALLOW-LIST: only seasons listed here get a
# season row, and facts._dedup_pss drops any stat rows for a season not here.
# 2025-26 ("2526") is intentionally OMITTED: its detailed FBref stats are not
# yet published (the Kaggle re-publisher's 2025-26 file lacks the passing/
# defense/possession columns), so including it produced hollow feature vectors
# and broken radars. Re-add "2526" here (and to etl.config.DEFAULT_SEASONS)
# once a complete detailed 2025-26 source exists — the rest of the 2526 wiring
# (fbref_kaggle.DATASETS, ClubElo 2026 snapshot) is already in place.
SEASONS = {
    "2021": ("2020-21", 2020),
    "2122": ("2021-22", 2021),
    "2223": ("2022-23", 2022),
    "2324": ("2023-24", 2023),
    "2425": ("2024-25", 2024),
}


def _load_leagues(session: Session) -> None:
    for code, (name, country, tm) in LEAGUES.items():
        row = session.scalar(select(League).where(League.code == code))
        if row is None:
            session.add(League(code=code, name=name, country=country, tier=1,
                               transfermarkt_code=tm))
        else:
            row.name, row.country, row.transfermarkt_code = name, country, tm
    log.info("leagues: %d", len(LEAGUES))


def _load_seasons(session: Session) -> None:
    for code, (label, start) in SEASONS.items():
        row = session.scalar(select(Season).where(Season.code == code))
        if row is None:
            session.add(Season(code=code, label=label, start_year=start))
        else:
            row.label, row.start_year = label, start
    log.info("seasons: %d", len(SEASONS))


def _prune_stale_seasons(session: Session) -> None:
    """Remove season rows no longer in the allow-list, plus their facts.

    _load_seasons is an idempotent UPSERT — it never DELETEs — so a season that
    used to be active (e.g. 2025-26 after we rolled back) would otherwise linger,
    keep a valid season_id, and get its stat/feature rows reloaded. Pruning here
    keeps the seasons dimension the single source of truth for active seasons.
    The season_id FKs have no ON DELETE CASCADE, so clear dependents first."""
    stale = session.scalars(select(Season).where(~Season.code.in_(SEASONS))).all()
    if not stale:
        return
    ids = [s.id for s in stale]
    for tbl in ("player_features", "team_tactical_profiles", "player_season_stats"):
        session.execute(text(f"delete from {tbl} where season_id = any(:ids)"), {"ids": ids})
    for s in stale:
        session.delete(s)
    log.info("pruned %d stale season(s): %s", len(stale), [s.code for s in stale])


def run() -> None:
    session = SessionLocal()
    try:
        _load_leagues(session)
        _load_seasons(session)
        _prune_stale_seasons(session)
        session.commit()
        log.info("dimensions loaded (leagues=%d, seasons=%d)", len(LEAGUES), len(SEASONS))
    finally:
        session.close()
