"""Load reference dimensions: leagues and seasons. Idempotent (upsert by key)."""

from __future__ import annotations

from sqlalchemy import select
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

# soccerdata season code -> (label, start_year)
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


def run() -> None:
    session = SessionLocal()
    try:
        _load_leagues(session)
        _load_seasons(session)
        session.commit()
        log.info("dimensions loaded (leagues=%d, seasons=%d)", len(LEAGUES), len(SEASONS))
    finally:
        session.close()
