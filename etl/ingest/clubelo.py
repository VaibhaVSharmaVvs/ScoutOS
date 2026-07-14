"""ClubElo ingestion via soccerdata.

ClubElo publishes Elo strength ratings for clubs worldwide. We snapshot all
clubs on a set of dates (one per season end), giving a per-season club-strength
signal that spans every league we touch (it's global). Feeds the "club strength"
feature for the market-value model and the Club Fit engine.

Lightweight HTTP (no browser), so it's reliable and safe to run anytime.
"""

from __future__ import annotations

import soccerdata as sd

from etl.config import CLUBELO_SNAPSHOT_DATES, SOURCE_DIRS
from etl.ingest.base import Artifact, Manifest, log, rel, save_parquet, utcnow_iso

SOURCE = "clubelo"


def run(dates: list[str] | None = None, proxy: str | None = None, force: bool = False) -> None:
    dates = dates or CLUBELO_SNAPSHOT_DATES
    cache_dir = SOURCE_DIRS[SOURCE] / "_cache"
    ce = sd.ClubElo(data_dir=cache_dir, proxy=proxy)
    manifest = Manifest()

    log.info("ClubElo: %d snapshot dates", len(dates))
    for date in dates:
        if manifest.has(SOURCE, "by_date", date) and not force:
            log.info("skip %s (in manifest)", date)
            continue
        try:
            df = ce.read_by_date(date)
        except Exception as exc:  # noqa: BLE001
            log.error("FAILED %s: %s", date, exc)
            continue
        df = df.copy()
        df["snapshot_date"] = date
        path = SOURCE_DIRS[SOURCE] / "by_date" / f"{date}.parquet"
        rows = save_parquet(df, path)
        manifest.add(Artifact(SOURCE, "by_date", date, rel(path), rows, utcnow_iso()))
        log.info("saved %s (%d clubs)", date, rows)

    log.info("ClubElo done. Manifest counts: %s", manifest.summary())
