"""Backfill one FBref league into the existing per-stat-type parquets.

FBref parquets hold all leagues combined in a single file per stat type. If a
league is missing, re-running the whole ingest would refetch everything. This
fetches via the "Big 5 European Leagues Combined" page, filters to the requested
league, and concatenates it onto each existing file.

Why combined rather than per-league: soccerdata's per-league path for some
leagues (e.g. ITA-Serie A) fails in read_seasons ("No objects to concatenate"),
which is exactly how Serie A got silently dropped from the batch run. The
combined page uses a different, working code path and includes Serie A. (Note
the combined page can itself omit a league — it dropped Bundesliga in testing —
so we only trust it for the one league we filter to, and keep the rest from the
per-league data already on disk.)

Column alignment is checked per file; a mismatch skips that file rather than
corrupting it. Idempotent: files that already contain the league are skipped.

    python -m etl.backfill_league --league "ITA-Serie A"

Also useful later for global expansion (adding leagues beyond the Big-5).
"""

from __future__ import annotations

import argparse

import pandas as pd

from etl.config import (
    DEFAULT_SEASONS,
    FBREF_PLAYER_STAT_TYPES,
    SOURCE_DIRS,
)
from etl.ingest._fbref_patch import FBrefExtended
from etl.ingest.base import Artifact, Manifest, log, rel, utcnow_iso


def _flatten(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join(str(c) for c in col if c != "").strip("_") for col in df.columns]
    return df.reset_index()


def _merge_into(path, league: str, fetched: pd.DataFrame, manifest, dataset, key) -> None:
    existing = pd.read_parquet(path)
    if "league" in existing.columns and (existing["league"] == league).any():
        log.info("skip %s/%s: %s already present", dataset, key, league)
        return
    incoming = _flatten(fetched)
    if "league" not in incoming.columns:
        log.error("no league column in %s/%s fetch -> skip", dataset, key)
        return
    incoming = incoming[incoming["league"] == league]
    if incoming.empty:
        log.error("%s not present in combined %s/%s fetch -> skip", league, dataset, key)
        return
    missing = set(existing.columns) - set(incoming.columns)
    if missing:
        # Aborting: existing columns absent from the fetch would misalign data.
        log.error("MISMATCH %s/%s: fetch missing cols %s -> skip", dataset, key, missing)
        return
    extra = set(incoming.columns) - set(existing.columns)
    if extra:
        # Harmless: extra fetch columns (e.g. keeper's '90s') are dropped to match.
        log.info("dropping %d extra col(s) from %s/%s: %s", len(extra), dataset, key, extra)
    incoming = incoming[existing.columns]
    combined = pd.concat([existing, incoming], ignore_index=True)
    tmp = path.with_suffix(".parquet.tmp")
    combined.to_parquet(tmp, index=False)
    tmp.replace(path)
    manifest.add(Artifact("fbref", dataset, key, rel(path), len(combined), utcnow_iso()))
    log.info("merged %s/%s: %d -> %d (+%d %s)", dataset, key,
             len(existing), len(combined), len(incoming), league)


def run(league: str, seasons: list[str] | None = None, proxy: str | None = None) -> None:
    seasons = seasons or DEFAULT_SEASONS
    cache = SOURCE_DIRS["fbref"] / "_cache"
    # Combined page (not per-league) — per-league read_seasons fails for some
    # leagues; we filter the combined result to `league` inside _merge_into.
    fb = FBrefExtended(
        leagues="Big 5 European Leagues Combined",
        seasons=seasons, data_dir=cache, proxy=proxy,
    )
    manifest = Manifest()

    for st in FBREF_PLAYER_STAT_TYPES:
        path = SOURCE_DIRS["fbref"] / "player_season" / f"{st}.parquet"
        if not path.exists():
            log.warning("no existing player_season/%s.parquet; run full ingest first", st)
            continue
        try:
            _merge_into(path, league, fb.read_player_season_stats(st), manifest, "player_season", st)
        except Exception as exc:  # noqa: BLE001
            log.error("FAILED player_season/%s: %s", st, exc)

    log.info("Backfill of %s done. Manifest counts: %s", league, manifest.summary())


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill one FBref league into existing parquets")
    parser.add_argument("--league", required=True, help='soccerdata league ID, e.g. "ITA-Serie A"')
    parser.add_argument("--seasons", nargs="+", default=None, help="season codes (default: config)")
    parser.add_argument("--proxy", default=None)
    args = parser.parse_args()
    run(league=args.league, seasons=args.seasons, proxy=args.proxy)


if __name__ == "__main__":
    main()
