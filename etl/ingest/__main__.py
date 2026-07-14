"""CLI for raw data ingestion.

Examples:
    python -m etl.ingest --source statsbomb
    python -m etl.ingest --source understat --seasons 2223 2324 2425
    python -m etl.ingest --source fbref --force
    python -m etl.ingest --source all
"""

from __future__ import annotations

import argparse

from etl.config import BIG5_LEAGUES, DEFAULT_SEASONS
from etl.ingest import fbref, statsbomb, transfermarkt, understat

SOURCES = {
    "fbref": fbref.run,
    "understat": understat.run,
    "statsbomb": statsbomb.run,
    "transfermarkt": transfermarkt.run,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Scout OS raw data ingestion")
    parser.add_argument(
        "--source",
        choices=[*SOURCES, "all"],
        required=True,
        help="Which source to download (or 'all').",
    )
    parser.add_argument(
        "--seasons",
        nargs="+",
        default=DEFAULT_SEASONS,
        help="soccerdata season codes, e.g. 2223 2324 (FBref/Understat only).",
    )
    parser.add_argument(
        "--leagues",
        nargs="+",
        default=BIG5_LEAGUES,
        help="soccerdata league IDs (FBref/Understat only).",
    )
    parser.add_argument(
        "--with-events",
        action="store_true",
        help="StatsBomb: also download event data (large).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if present in the manifest.",
    )
    args = parser.parse_args()

    targets = list(SOURCES) if args.source == "all" else [args.source]

    for name in targets:
        if name == "fbref":
            fbref.run(seasons=args.seasons, leagues=args.leagues, force=args.force)
        elif name == "understat":
            understat.run(seasons=args.seasons, leagues=args.leagues, force=args.force)
        elif name == "statsbomb":
            statsbomb.run(with_events=args.with_events, force=args.force)
        elif name == "transfermarkt":
            transfermarkt.run(force=args.force)


if __name__ == "__main__":
    main()
