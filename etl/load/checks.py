"""Phase 2d data-quality checks over the loaded PostgreSQL database.

Asserts invariants a healthy load must satisfy and prints a PASS/WARN/FAIL
report. Run after loading:  python -m etl.load --step checks
Exit code is non-zero if any FAIL, so it can gate CI later.
"""

from __future__ import annotations

import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    EntityXref,
    MarketValue,
    Player,
    PlayerSeasonStats,
    TeamTacticalProfile,
)
from etl.load.db import SessionLocal, log

_results: list[tuple[str, str, str]] = []


def _check(name: str, ok: bool, detail: str, warn_only: bool = False) -> None:
    status = "PASS" if ok else ("WARN" if warn_only else "FAIL")
    _results.append((status, name, detail))


def run() -> None:
    s: Session = SessionLocal()
    try:
        n_players = s.scalar(select(func.count()).select_from(Player))
        _check("players_exist", n_players > 5000, f"{n_players} canonical players")

        # every player has an fbref xref (the pool anchor)
        no_fbref = s.scalar(
            select(func.count()).select_from(Player).where(
                ~Player.id.in_(select(EntityXref.player_id).where(EntityXref.source == "fbref"))
            )
        )
        _check("all_players_have_fbref_xref", no_fbref == 0, f"{no_fbref} players w/o fbref xref")

        # cross-source link rates
        for src, floor in (("transfermarkt", 0.90), ("understat", 0.90), ("fbref_kaggle", 0.0)):
            linked = s.scalar(
                select(func.count(func.distinct(EntityXref.player_id))).where(
                    EntityXref.source == src
                )
            )
            _check(f"{src}_link_rate", linked / n_players >= floor,
                   f"{linked}/{n_players} = {linked/n_players:.1%}", warn_only=(src == "fbref_kaggle"))

        # facts present per source
        for src in ("fbref", "understat", "fbref_kaggle"):
            c = s.scalar(select(func.count()).select_from(PlayerSeasonStats).where(
                PlayerSeasonStats.source == src))
            _check(f"pss_{src}_rows", c > 5000, f"{c} rows")

        # detailed stats actually populated (the whole point of the Kaggle route)
        with_tkl = s.scalar(select(func.count()).select_from(PlayerSeasonStats).where(
            PlayerSeasonStats.source == "fbref_kaggle",
            PlayerSeasonStats.stats["tackles"].isnot(None)))
        det = s.scalar(select(func.count()).select_from(PlayerSeasonStats).where(
            PlayerSeasonStats.source == "fbref_kaggle"))
        _check("detailed_tackles_populated", det > 0 and with_tkl / det > 0.95,
               f"{with_tkl}/{det} fbref_kaggle rows have tackles")

        # market value coverage
        mv_players = s.scalar(select(func.count(func.distinct(MarketValue.player_id))))
        _check("market_value_coverage", mv_players / n_players >= 0.85,
               f"{mv_players}/{n_players} = {mv_players/n_players:.1%}")

        # team profiles present and non-trivial
        n_prof = s.scalar(select(func.count()).select_from(TeamTacticalProfile))
        _check("team_profiles", n_prof > 300, f"{n_prof} club-seasons")

        # no negative/insane minutes
        bad_min = s.scalar(select(func.count()).select_from(PlayerSeasonStats).where(
            PlayerSeasonStats.minutes < 0))
        _check("no_negative_minutes", bad_min == 0, f"{bad_min} rows with negative minutes")

    finally:
        s.close()

    log.info("=== DATA-QUALITY REPORT ===")
    for status, name, detail in _results:
        log.info("[%s] %-28s %s", status, name, detail)
    fails = [r for r in _results if r[0] == "FAIL"]
    log.info("%d checks, %d FAIL, %d WARN", len(_results),
             len(fails), sum(1 for r in _results if r[0] == "WARN"))
    if fails:
        sys.exit(1)


if __name__ == "__main__":
    run()
