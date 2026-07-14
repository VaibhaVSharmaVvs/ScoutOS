# Scout OS — Football Scout AI ⚽

An AI-powered football scouting platform: player similarity, market-value
prediction, position fit, potential growth, and club fit — with LLM-generated
explanations. See [`PLAN.md`](./PLAN.md) for the full phase-by-phase roadmap.

## Architecture

```
Data sources (FBref, StatsBomb, Understat, Transfermarkt)
        → ETL (Python) → PostgreSQL (source of truth)
        → Feature engineering → ML models → FastAPI → React
        → LLM explanation layer
```

## Monorepo layout

```
backend/    FastAPI API (Phase 5)
etl/        Data pipeline (Phase 1–2)
ml/         Feature engineering + models (Phase 3–4)
frontend/   React + Vite + TS + Tailwind (Phase 7)
data/       Raw + processed data (gitignored)
```

## Quick start (Phase 0 scaffold)

Bring up the whole stack with Docker:

```bash
cp .env.example .env        # then edit secrets
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend:  http://localhost:8000  (docs at `/docs`, health at `/health`)
- Postgres: localhost:5432
- Redis:    localhost:6379

### Run pieces individually

Backend:
```bash
cd backend && pip install ".[dev]" && uvicorn app.main:app --reload
pytest
```

Frontend:
```bash
cd frontend && npm install && npm run dev
```

## Status

Phase 0 (scaffolding) complete. Next: Phase 1 — data acquisition. See `PLAN.md`.
