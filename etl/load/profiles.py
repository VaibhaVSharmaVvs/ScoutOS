"""Phase 2d: team_tactical_profiles, aggregated from FBref player stats.

The detailed team tables were deferred in ingest (comment-wrapped), so we build
per club-season tactical profiles by summing counting metrics across a club's
players and converting to per-90 team rates. This is the input to the Club Fit
engine (Phase 4.5). Idempotent: table truncated before load.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import delete, select

from app.db.models import PlayerSeasonStats, TeamTacticalProfile
from etl.load.db import SessionLocal, log

# profile metric -> JSONB key in the fbref_kaggle canonical stats blob.
# (soccerdata's FBref detail was hollow; the real detail comes from Kaggle.)
SOURCE = "fbref_kaggle"
METRICS = {
    "goals": "goals",
    "assists": "assists",
    "shots": "shots",
    "passes_completed": "pass_cmp",
    "prog_passes": "pass_prog",
    "prog_pass_dist": "prog_pass_dist",
    "key_passes": "key_passes",
    "prog_carries": "carries_prog",
    "tackles": "tackles",
    "tackles_won": "tackles_won",
    "interceptions": "interceptions",
    "clearances": "clearances",
    "sca": "sca",
    "gca": "gca",
}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def run() -> None:
    session = SessionLocal()
    try:
        session.execute(delete(TeamTacticalProfile))
        session.commit()

        # league_id per (club, season) from Understat rows (FBref rows lack it)
        league_by_cs: dict[tuple[int, int], int] = {}
        for cid, sid, lid in session.execute(
            select(PlayerSeasonStats.club_id, PlayerSeasonStats.season_id,
                   PlayerSeasonStats.league_id).where(PlayerSeasonStats.source == "understat")
        ):
            if cid and sid and lid:
                league_by_cs.setdefault((cid, sid), lid)

        groups: dict[tuple[int, int], list] = defaultdict(list)
        for row in session.scalars(
            select(PlayerSeasonStats).where(PlayerSeasonStats.source == SOURCE)
        ):
            if row.club_id and row.season_id:
                groups[(row.club_id, row.season_id)].append(row)

        rows = []
        for (club_id, season_id), players in groups.items():
            team_minutes = sum((p.minutes or 0) for p in players)
            team_90 = team_minutes / 90 if team_minutes else 0
            profile = {"n_players": len(players), "team_minutes": team_minutes}
            for name, key in METRICS.items():
                total = sum(_num((p.stats or {}).get(key)) for p in players)
                profile[f"{name}_total"] = round(total, 2)
                profile[f"{name}_per90"] = round(total / team_90, 3) if team_90 else None
            rows.append({
                "club_id": club_id, "season_id": season_id,
                "league_id": league_by_cs.get((club_id, season_id)),
                "profile": profile,
            })

        session.bulk_insert_mappings(TeamTacticalProfile, rows)
        session.commit()
        log.info("team_tactical_profiles: %d club-seasons", len(rows))
    finally:
        session.close()
