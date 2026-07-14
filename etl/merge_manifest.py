"""Merge an external raw-data manifest into the local one.

Use when raw data is downloaded on another machine (e.g. FBref, to dodge a
Cloudflare IP block) and copied back. After dropping the files into
`data/raw/<source>/`, merge that machine's manifest so `validate` and
idempotency see the new artifacts:

    python -m etl.merge_manifest path/to/other/manifest.json

Entries are keyed by source:dataset:key, so the merge is a safe union; the
incoming manifest wins on any key collision.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from etl.config import MANIFEST_PATH


def main(other_path: str) -> int:
    other_file = Path(other_path)
    if not other_file.exists():
        print(f"No manifest at {other_file}")
        return 1

    with other_file.open(encoding="utf-8") as fh:
        incoming = json.load(fh)

    local: dict[str, dict] = {}
    if MANIFEST_PATH.exists():
        with MANIFEST_PATH.open(encoding="utf-8") as fh:
            local = json.load(fh)

    before = len(local)
    local.update(incoming)

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(local, fh, indent=2, sort_keys=True)
    tmp.replace(MANIFEST_PATH)

    print(f"Merged {len(incoming)} incoming entries; manifest {before} -> {len(local)}.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m etl.merge_manifest <other_manifest.json>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
