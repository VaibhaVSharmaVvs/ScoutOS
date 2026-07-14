"""Shared ingest helpers: manifest tracking, atomic saves, paths.

The manifest (`data/raw/manifest.json`) is the ledger of every artifact we have
downloaded. Downloaders consult it to skip completed work (idempotency) and
append to it after each successful save (resumability).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def _stringify_cell(v: object) -> object:
    """Coerce a value pyarrow can't type-infer into a stable string.

    Preserves None/NaN; JSON-encodes lists/dicts; str()'s everything else.
    Used only as a fallback when a column has mixed/unsupported types so raw
    data is preserved losslessly as text for downstream parsing.
    """
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, (list, dict)):
        return json.dumps(v, default=str, ensure_ascii=False)
    return str(v)

from etl.config import MANIFEST_PATH, RAW_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("etl.ingest")


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Artifact:
    """One downloaded file, identified by (source, dataset, key)."""

    source: str
    dataset: str
    key: str  # e.g. "ENG-Premier League/2425" or "competitions"
    path: str  # repo-relative
    rows: int
    downloaded_at: str

    @property
    def manifest_id(self) -> str:
        return f"{self.source}:{self.dataset}:{self.key}"


class Manifest:
    """JSON-backed ledger of downloaded artifacts."""

    def __init__(self, path: Path = MANIFEST_PATH):
        self.path = path
        self._entries: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            with self.path.open(encoding="utf-8") as fh:
                self._entries = json.load(fh)

    def has(self, source: str, dataset: str, key: str) -> bool:
        return f"{source}:{dataset}:{key}" in self._entries

    def add(self, artifact: Artifact) -> None:
        self._entries[artifact.manifest_id] = asdict(artifact)
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self._entries, fh, indent=2, sort_keys=True)
        tmp.replace(self.path)

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self._entries.values():
            counts[entry["source"]] = counts.get(entry["source"], 0) + 1
        return counts


def rel(path: Path) -> str:
    """Repo-relative path string for storing in the manifest."""
    try:
        return path.relative_to(RAW_DIR.parent.parent).as_posix()
    except ValueError:
        return path.as_posix()


def save_parquet(df: pd.DataFrame, path: Path) -> int:
    """Atomically write a DataFrame to parquet. Returns row count.

    MultiIndex columns (common in FBref frames) are flattened so parquet
    accepts them; the raw soccerdata cache still holds the untouched source.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = ["_".join(str(c) for c in col if c != "").strip("_") for col in out.columns]
    out = out.reset_index()
    tmp = path.with_suffix(".parquet.tmp")
    try:
        out.to_parquet(tmp, index=False)
    except Exception:  # noqa: BLE001 - retry once with object cols stringified
        for col in out.columns:
            if out[col].dtype == object:
                out[col] = out[col].map(_stringify_cell)
        out.to_parquet(tmp, index=False)
    tmp.replace(path)
    return len(out)
