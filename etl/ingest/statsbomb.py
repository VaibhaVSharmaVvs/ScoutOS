"""StatsBomb open-data ingestion via statsbombpy.

StatsBomb's free data is event-level (passes, shots, pressures) for a curated
set of competitions/seasons — not comprehensive top-5 coverage, but the richest
free source for tactical/event features. Pure GitHub JSON: no browser, no
Cloudflare, no credentials.

Default run downloads the competition catalog and match lists. Event data is
large, so it is opt-in via `with_events=True`.
"""

from __future__ import annotations

from statsbombpy import sb

from etl.config import SOURCE_DIRS
from etl.ingest.base import Artifact, Manifest, log, rel, save_parquet, utcnow_iso

SOURCE = "statsbomb"


def run(
    competitions: list[tuple[int, int]] | None = None,
    with_events: bool = False,
    force: bool = False,
) -> None:
    """Download StatsBomb open data.

    competitions: list of (competition_id, season_id). If None, every open-data
    competition/season is downloaded (match lists only).
    """
    manifest = Manifest()

    # 1. Competition catalog (always).
    if force or not manifest.has(SOURCE, "competitions", "all"):
        comps = sb.competitions()
        path = SOURCE_DIRS[SOURCE] / "competitions.parquet"
        rows = save_parquet(comps, path)
        manifest.add(Artifact(SOURCE, "competitions", "all", rel(path), rows, utcnow_iso()))
        log.info("saved competitions (%d rows)", rows)
    else:
        comps = sb.competitions()
        log.info("skip competitions (in manifest)")

    # 2. Resolve which (competition_id, season_id) pairs to pull.
    if competitions is None:
        competitions = list(
            comps[["competition_id", "season_id"]].itertuples(index=False, name=None)
        )
    log.info("StatsBomb: %d competition-seasons", len(competitions))

    # 3. Match lists (and optionally events) per competition-season.
    for comp_id, season_id in competitions:
        key = f"{comp_id}_{season_id}"
        if not (manifest.has(SOURCE, "matches", key) and not force):
            try:
                matches = sb.matches(competition_id=comp_id, season_id=season_id)
            except Exception as exc:  # noqa: BLE001
                log.error("FAILED matches %s: %s", key, exc)
                continue
            path = SOURCE_DIRS[SOURCE] / "matches" / f"{key}.parquet"
            rows = save_parquet(matches, path)
            manifest.add(Artifact(SOURCE, "matches", key, rel(path), rows, utcnow_iso()))
            log.info("saved matches %s (%d rows)", key, rows)

        if with_events and not (manifest.has(SOURCE, "events", key) and not force):
            try:
                events = sb.competition_events(
                    country=None, division=None, season=None,
                    competition_id=comp_id, season_id=season_id,
                )
            except TypeError:
                # older/newer signature: fetch per-match and concat is heavy;
                # skip gracefully and let the caller pull events explicitly.
                log.warning("competition_events signature mismatch for %s; skipping events", key)
                continue
            except Exception as exc:  # noqa: BLE001
                log.error("FAILED events %s: %s", key, exc)
                continue
            path = SOURCE_DIRS[SOURCE] / "events" / f"{key}.parquet"
            rows = save_parquet(events, path)
            manifest.add(Artifact(SOURCE, "events", key, rel(path), rows, utcnow_iso()))
            log.info("saved events %s (%d rows)", key, rows)

    log.info("StatsBomb done. Manifest counts: %s", manifest.summary())
