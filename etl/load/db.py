"""ETL DB access — reuses the backend's engine/session (same DATABASE_URL)."""

from __future__ import annotations

import logging

from app.db.session import SessionLocal, get_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("etl.load")

__all__ = ["SessionLocal", "get_engine", "log"]
