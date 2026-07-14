# Scout OS — ETL Pipeline (Phase 1 & 2)

Downloads raw football data, normalizes it, and loads PostgreSQL (the single
source of truth). Nothing implemented yet — this directory is scaffolded for
Phase 1 (ingest) and Phase 2 (transform + load).

Planned layout:

```
etl/
├── ingest/     # source downloaders: fbref, statsbomb, understat, transfermarkt
├── transform/  # raw -> staging -> normalized
├── load/        # SQLAlchemy models + Alembic migrations
└── run.py       # `python -m etl.run` rebuilds the DB
```
