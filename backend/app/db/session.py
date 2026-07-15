"""Engine and session factory, driven by the app settings DATABASE_URL."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    return _engine


def _session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _SessionLocal


def SessionLocal() -> Session:  # noqa: N802 - factory-style callable
    return _session_factory()()


def get_session() -> Iterator[Session]:
    """FastAPI dependency: yields a session and closes it after the request."""
    session = _session_factory()()
    try:
        yield session
    finally:
        session.close()
