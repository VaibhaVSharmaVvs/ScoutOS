"""FBref ingestion via soccerdata.

Pulls player-season and team-season stat tables plus schedules for the
configured leagues/seasons. One parquet per stat category (each already spans
all requested leagues & seasons). soccerdata keeps the untouched HTML cache
under `data/raw/fbref/_cache/`.

Note: modern FBref scraping drives a headless browser (Cloudflare). This needs
Chrome/Chromium available and is deliberately slow (rate-limited). Run it as a
long job, not in CI.
"""

from __future__ import annotations

import time

import soccerdata as sd

from etl.config import (
    BIG5_LEAGUES,
    DEFAULT_SEASONS,
    FBREF_PLAYER_STAT_TYPES,
    FBREF_TEAM_STAT_TYPES,
    REQUEST_DELAY_SECONDS,
    SOURCE_DIRS,
)
from etl.ingest.base import Artifact, Manifest, log, rel, save_parquet, utcnow_iso

SOURCE = "fbref"


def run(
    seasons: list[str] | None = None,
    leagues: list[str] | None = None,
    player_stat_types: list[str] | None = None,
    team_stat_types: list[str] | None = None,
    force: bool = False,
) -> None:
    seasons = seasons or DEFAULT_SEASONS
    leagues = leagues or BIG5_LEAGUES
    player_stat_types = player_stat_types or FBREF_PLAYER_STAT_TYPES
    team_stat_types = team_stat_types or FBREF_TEAM_STAT_TYPES

    cache_dir = SOURCE_DIRS[SOURCE] / "_cache"
    fb = sd.FBref(leagues=leagues, seasons=seasons, data_dir=cache_dir)
    manifest = Manifest()

    log.info("FBref: %d leagues x %d seasons", len(leagues), len(seasons))

    def _pull(dataset: str, key: str, fetch, subdir: str) -> None:
        if manifest.has(SOURCE, dataset, key) and not force:
            log.info("skip %s/%s (in manifest)", dataset, key)
            return
        try:
            df = fetch()
        except Exception as exc:  # noqa: BLE001 - keep the run going
            log.error("FAILED %s/%s: %s", dataset, key, exc)
            return
        path = SOURCE_DIRS[SOURCE] / subdir / f"{key}.parquet"
        rows = save_parquet(df, path)
        manifest.add(Artifact(SOURCE, dataset, key, rel(path), rows, utcnow_iso()))
        log.info("saved %s/%s (%d rows)", dataset, key, rows)
        time.sleep(REQUEST_DELAY_SECONDS)

    for stat_type in player_stat_types:
        _pull("player_season", stat_type, lambda st=stat_type: fb.read_player_season_stats(st),
              "player_season")

    for stat_type in team_stat_types:
        _pull("team_season", stat_type, lambda st=stat_type: fb.read_team_season_stats(st),
              "team_season")

    _pull("schedule", "all", fb.read_schedule, ".")

    log.info("FBref done. Manifest counts: %s", manifest.summary())
