"""Load canonical clubs from the Big-5 stat sources (FBref + Understat).

Conservative: canonical clubs are keyed by (normalized_name, country). FBref is
the spine; Understat/ClubElo attach by EXACT normalized-name match. Names that
don't match exactly are reported (they're the alias cases to fix later via a
small override map, mirroring the player-resolution approach). Transfermarkt
club matching is deferred (verbose formal names → low exact-match rate).
"""

from __future__ import annotations

import glob

import pandas as pd
from sqlalchemy import select

from app.db.models import Club
from etl.load.db import SessionLocal, log
from etl.load.dimensions import LEAGUES
from etl.load.normalize import normalize_name

FBREF_STD = "data/raw/fbref/player_season/standard.parquet"
UNDERSTAT = "data/raw/understat/player_season.parquet"
CLUBELO_GLOB = "data/raw/clubelo/by_date/*.parquet"


def run() -> None:
    session = SessionLocal()
    try:
        canon: dict[tuple[str, str], Club] = {}

        # existing (idempotent re-run)
        for c in session.scalars(select(Club)).all():
            canon[(c.normalized_name, c.country or "")] = c

        # 1. FBref teams = spine
        fb = pd.read_parquet(FBREF_STD, columns=["team", "league"]).drop_duplicates()
        fb_n = 0
        for team, league in fb.itertuples(index=False):
            country = LEAGUES.get(league, (None, "", None))[1]
            key = (normalize_name(team), country)
            if key not in canon:
                club = Club(name=team, normalized_name=key[0], country=country, fbref_name=team)
                session.add(club)
                canon[key] = club
                fb_n += 1
            elif canon[key].fbref_name is None:
                canon[key].fbref_name = team

        # 2. Understat teams — attach id on exact match, else create (alias case)
        us = pd.read_parquet(UNDERSTAT, columns=["team", "team_id", "league"]).drop_duplicates(
            subset=["team", "league"]
        )
        us_matched = us_only = 0
        for team, team_id, league in us.itertuples(index=False):
            country = LEAGUES.get(league, (None, "", None))[1]
            key = (normalize_name(team), country)
            if key in canon:
                canon[key].understat_id = int(team_id)
                us_matched += 1
            else:
                club = Club(name=team, normalized_name=key[0], country=country,
                            understat_id=int(team_id))
                session.add(club)
                canon[key] = club
                us_only += 1

        # 3. ClubElo — attach name on exact match within Big-5 (no new rows)
        ce = pd.concat(
            [pd.read_parquet(f, columns=["team", "league"]) for f in glob.glob(CLUBELO_GLOB)]
        ).drop_duplicates()
        ce_matched = 0
        for team, league in ce.itertuples(index=False):
            if league not in LEAGUES:
                continue
            country = LEAGUES[league][1]
            key = (normalize_name(team), country)
            if key in canon:
                canon[key].clubelo_name = team
                ce_matched += 1

        session.commit()
        total = session.scalar(select(Club).with_only_columns(Club.id).order_by(Club.id.desc())) or 0
        n = len(canon)
        log.info("clubs: %d canonical | fbref new=%d | understat matched=%d, alias(new)=%d | "
                 "clubelo matched=%d", n, fb_n, us_matched, us_only, ce_matched)
        if us_only:
            log.info("NOTE: %d Understat teams didn't exact-match a FBref club "
                     "(alias cases -> override map later)", us_only)
    finally:
        session.close()
