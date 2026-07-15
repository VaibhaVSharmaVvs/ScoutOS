"""Load orchestrator. Run from repo root:

    python -m etl.load --step dimensions
    python -m etl.load --step clubs
    python -m etl.load --step players
    python -m etl.load --step all
"""

from __future__ import annotations

import argparse

STEPS = ["dimensions", "clubs", "players"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Scout OS load stage (raw -> Postgres)")
    parser.add_argument("--step", choices=[*STEPS, "all"], required=True)
    args = parser.parse_args()

    steps = STEPS if args.step == "all" else [args.step]
    for step in steps:
        if step == "dimensions":
            from etl.load import dimensions
            dimensions.run()
        elif step == "clubs":
            from etl.load import clubs
            clubs.run()
        elif step == "players":
            from etl.load import players
            players.run()


if __name__ == "__main__":
    main()
