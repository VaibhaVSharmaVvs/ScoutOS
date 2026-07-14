"""Transfermarkt ingestion via a Kaggle dataset dump.

Transfermarkt is the source of truth for market values & transfer history (the
target for the Phase 4 value model). Scraping the site directly is brittle and
ToS-sensitive, so we use the maintained Kaggle dump `davidcariboo/player-scores`
(players, appearances, transfers, market value valuations, clubs, games).

Requires Kaggle credentials: set KAGGLE_USERNAME / KAGGLE_KEY, or place
kaggle.json in ~/.kaggle/. If kagglehub is unavailable, download the dataset
manually and drop the CSVs in data/raw/transfermarkt/.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from etl.config import SOURCE_DIRS, TRANSFERMARKT_KAGGLE_DATASET
from etl.ingest.base import Artifact, Manifest, log, rel, utcnow_iso

SOURCE = "transfermarkt"


def run(force: bool = False) -> None:
    manifest = Manifest()
    dest = SOURCE_DIRS[SOURCE]
    dest.mkdir(parents=True, exist_ok=True)

    try:
        import kagglehub
    except ImportError:
        log.error(
            "kagglehub not installed. Either `pip install kagglehub` (needs Kaggle "
            "credentials) or manually download %s and place the CSVs in %s",
            TRANSFERMARKT_KAGGLE_DATASET, dest,
        )
        return

    try:
        cache_path = Path(kagglehub.dataset_download(TRANSFERMARKT_KAGGLE_DATASET))
    except Exception as exc:  # noqa: BLE001
        log.error(
            "Kaggle download failed (%s). Set KAGGLE_USERNAME/KAGGLE_KEY or place "
            "kaggle.json in ~/.kaggle/, or download manually into %s",
            exc, dest,
        )
        return

    for csv in sorted(cache_path.glob("*.csv")):
        key = csv.stem
        if manifest.has(SOURCE, "table", key) and not force:
            log.info("skip %s (in manifest)", key)
            continue
        target = dest / csv.name
        shutil.copy2(csv, target)
        # Row count without loading everything into memory.
        with target.open(encoding="utf-8", errors="ignore") as fh:
            rows = sum(1 for _ in fh) - 1
        manifest.add(Artifact(SOURCE, "table", key, rel(target), max(rows, 0), utcnow_iso()))
        log.info("copied %s (%d rows)", csv.name, max(rows, 0))

    log.info("Transfermarkt done. Manifest counts: %s", manifest.summary())
