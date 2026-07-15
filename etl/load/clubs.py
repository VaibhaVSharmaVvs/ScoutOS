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
from rapidfuzz import fuzz, process
from sqlalchemy import select

from app.db.models import Club
from etl.load.db import SessionLocal, log
from etl.load.dimensions import LEAGUES
from etl.load.normalize import normalize_name

CLUB_FUZZY_THRESHOLD = 85  # token_set_ratio within same country

# ClubElo uses abbreviations with little/no token overlap with FBref names, so
# fuzzy can't reach them. Map ClubElo name -> FBref normalized_name.
CLUBELO_ALIASES = {
    "Man City": "manchester city",
    "Man United": "manchester utd",
    "Forest": "nottingham",
    "Bilbao": "athletic club",
    "Paris SG": "paris saint germain",
    "Bielefeld": "arminia",
    "Fuerth": "greuther furth",
}

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

        # per-country FBref canonical norms for fuzzy fallback
        by_country: dict[str, list[str]] = {}
        for (norm, country), club in canon.items():
            if club.fbref_name:
                by_country.setdefault(country, []).append(norm)

        def _fuzzy(norm: str, country: str):
            """Unique FBref-canonical club in this country above threshold, else None."""
            pool = by_country.get(country, [])
            if not pool:
                return None
            hits = process.extract(norm, pool, scorer=fuzz.token_set_ratio, limit=2,
                                   score_cutoff=CLUB_FUZZY_THRESHOLD)
            if len(hits) == 1 or (len(hits) >= 2 and hits[0][1] - hits[1][1] >= 5):
                return canon.get((hits[0][0], country))
            return None

        # 2. Understat teams — exact, then fuzzy, else alias row
        us = pd.read_parquet(UNDERSTAT, columns=["team", "team_id", "league"]).drop_duplicates(
            subset=["team", "league"]
        )
        us_exact = us_fuzzy = us_only = 0
        for team, team_id, league in us.itertuples(index=False):
            country = LEAGUES.get(league, (None, "", None))[1]
            key = (normalize_name(team), country)
            if key in canon:
                canon[key].understat_id = int(team_id); us_exact += 1
            elif (m := _fuzzy(key[0], country)) is not None:
                m.understat_id = int(team_id); us_fuzzy += 1
            else:
                club = Club(name=team, normalized_name=key[0], country=country,
                            understat_id=int(team_id))
                session.add(club)
                canon[key] = club
                us_only += 1

        # 3. ClubElo — exact then fuzzy within Big-5 (no new rows)
        ce = pd.concat(
            [pd.read_parquet(f, columns=["team", "league"]) for f in glob.glob(CLUBELO_GLOB)]
        ).drop_duplicates()
        ce_exact = ce_fuzzy = ce_alias = 0
        for team, league in ce.itertuples(index=False):
            if league not in LEAGUES:
                continue
            country = LEAGUES[league][1]
            alias_key = (CLUBELO_ALIASES.get(team, ""), country)
            key = (normalize_name(team), country)
            if alias_key in canon:
                canon[alias_key].clubelo_name = team; ce_alias += 1
            elif key in canon:
                canon[key].clubelo_name = team; ce_exact += 1
            elif (m := _fuzzy(key[0], country)) is not None:
                m.clubelo_name = team; ce_fuzzy += 1

        session.commit()
        log.info("clubs: %d canonical | fbref new=%d | understat exact=%d fuzzy=%d alias(new)=%d | "
                 "clubelo exact=%d fuzzy=%d alias=%d", len(canon), fb_n, us_exact, us_fuzzy, us_only,
                 ce_exact, ce_fuzzy, ce_alias)
    finally:
        session.close()
