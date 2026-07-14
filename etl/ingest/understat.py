"""Understat ingestion via soccerdata.

Understat's value is xG/xA-based player and team stats plus shot-level events.
Covers the Big-5 domestic leagues. Lighter scraping than FBref (embedded JSON),
so this is usually the most reliable soccerdata source to run live.
"""

from __future__ import annotations

import soccerdata as sd

from etl.config import BIG5_LEAGUES, DEFAULT_SEASONS, SOURCE_DIRS
from etl.ingest.base import Artifact, Manifest, log, rel, save_parquet, utcnow_iso

SOURCE = "understat"


def run(
    seasons: list[str] | None = None,
    leagues: list[str] | None = None,
    force: bool = False,
) -> None:
    seasons = seasons or DEFAULT_SEASONS
    leagues = leagues or BIG5_LEAGUES

    cache_dir = SOURCE_DIRS[SOURCE] / "_cache"
    us = sd.Understat(leagues=leagues, seasons=seasons, data_dir=cache_dir)
    manifest = Manifest()

    log.info("Understat: %d leagues x %d seasons", len(leagues), len(seasons))

    datasets = {
        "player_season": us.read_player_season_stats,
        "team_match": us.read_team_match_stats,
        "schedule": us.read_schedule,
    }

    for dataset, fetch in datasets.items():
        if manifest.has(SOURCE, dataset, "all") and not force:
            log.info("skip %s (in manifest)", dataset)
            continue
        try:
            df = fetch()
        except Exception as exc:  # noqa: BLE001
            log.error("FAILED %s: %s", dataset, exc)
            continue
        path = SOURCE_DIRS[SOURCE] / f"{dataset}.parquet"
        rows = save_parquet(df, path)
        manifest.add(Artifact(SOURCE, dataset, "all", rel(path), rows, utcnow_iso()))
        log.info("saved %s (%d rows)", dataset, rows)

    log.info("Understat done. Manifest counts: %s", manifest.summary())
