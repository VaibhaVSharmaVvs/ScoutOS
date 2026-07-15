"""Database layer: SQLAlchemy models, session, and metadata.

This package is the single source of truth for the normalized schema. The
backend queries it; the ETL load stage (etl/load) writes to it via the same
models. Migrations are managed by Alembic (backend/alembic).
"""

from app.db.base import Base
from app.db.session import SessionLocal, get_engine, get_session

__all__ = ["Base", "SessionLocal", "get_engine", "get_session"]
