"""Spot-check downloaded raw data.

Reads the manifest, confirms each artifact exists on disk, reports row counts,
and flags empty or missing files. Run after an ingest to sanity-check coverage:

    python -m etl.validate
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from etl.config import MANIFEST_PATH, REPO_ROOT


def main() -> int:
    if not MANIFEST_PATH.exists():
        print("No manifest found. Run `python -m etl.ingest --source <source>` first.")
        return 1

    with MANIFEST_PATH.open(encoding="utf-8") as fh:
        entries = json.load(fh)

    if not entries:
        print("Manifest is empty.")
        return 1

    by_source: dict[str, list[dict]] = {}
    for entry in entries.values():
        by_source.setdefault(entry["source"], []).append(entry)

    problems = 0
    print(f"{'SOURCE':<14} {'DATASET':<16} {'KEY':<28} {'ROWS':>10}  STATUS")
    print("-" * 78)
    for source in sorted(by_source):
        for entry in sorted(by_source[source], key=lambda e: (e["dataset"], e["key"])):
            path = REPO_ROOT / entry["path"]
            if not path.exists():
                status = "MISSING FILE"
                problems += 1
            elif entry["rows"] == 0:
                status = "EMPTY"
                problems += 1
            else:
                status = "ok"
            print(
                f"{entry['source']:<14} {entry['dataset']:<16} "
                f"{entry['key'][:28]:<28} {entry['rows']:>10}  {status}"
            )

    print("-" * 78)
    total_rows = sum(e["rows"] for e in entries.values())
    print(f"{len(entries)} artifacts, {total_rows:,} total rows across "
          f"{len(by_source)} source(s).")
    if problems:
        print(f"\n[WARN] {problems} problem(s) found (missing/empty artifacts).")
        return 1
    print("\n[OK] All artifacts present and non-empty.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
