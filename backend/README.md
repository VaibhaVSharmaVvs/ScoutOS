# Scout OS — Backend (FastAPI)

## Local dev (without Docker)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install ".[dev]"
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Tests

```bash
pytest
```

## Structure

```
app/
├── main.py        # app factory, middleware, router registration
├── config.py      # env-driven settings (pydantic-settings)
└── api/           # routers (health now; feature routers land in Phase 5)
```
