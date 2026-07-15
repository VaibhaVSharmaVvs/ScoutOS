"""Phase 2 load stage: raw parquet/CSV -> normalized PostgreSQL.

Imports the ORM models from the backend (`app.db.models`) and writes to the
same database the API reads. Run from the repo root so `.env` (DATABASE_URL,
localhost:5433) and the `app` package both resolve.

Steps (idempotent): dimensions -> clubs -> players (entity resolution) ->
facts. Orchestrated via `python -m etl.load --step <name>` (or `all`).
"""
