# Scout OS — Phase-by-Phase Build Plan

An AI-powered football scouting platform. This plan turns `Proposal.txt` into an ordered, executable roadmap. Each phase produces something runnable before the next begins.

---

## 🎯 Goal Hierarchy (ProtrackLite framing)

- **🎯 Goal:** A deployed scouting platform that answers position-fit, club-fit, similarity, market-value, and growth questions for any professional player — with LLM-generated explanations.
- **✅ Tasks:** One per phase below (each phase = one deliverable).
- **📌 Activities:** The checklists inside each phase.

---

## Phase 0 — Project Scaffolding & Dev Environment (½–1 day)

**Deliverable:** A monorepo skeleton that runs locally with one command.

```
ScoutOS/
├── backend/          # FastAPI app
├── etl/              # Data pipeline (Python)
├── ml/               # Training code, notebooks, saved models
├── frontend/         # React app (Vite + TypeScript)
├── data/
│   └── raw/          # fbref/ statsbomb/ understat/ transfermarkt/  (gitignored)
├── docker-compose.yml   # postgres + redis + backend + frontend
├── .github/workflows/   # CI (added Phase 8)
├── .env.example
└── PLAN.md
```

- [ ] `docker-compose.yml` with PostgreSQL 16 + Redis 7
- [ ] Python workspace: `uv` (or pip + venv), `ruff`, `pytest`
- [ ] FastAPI "hello world" + `/health` endpoint
- [ ] React app scaffold (Vite + TS + Tailwind)
- [ ] `.gitignore` (raw data, models, .env, node_modules)
- [ ] First commit + push to GitHub

---

## Phase 1 — Data Acquisition (Initial Import) (3–5 days)

**Deliverable:** 5–10 seasons of raw data for top-5 European leagues + UCL/UEL sitting untouched in `data/raw/`.

**Recommended sources (practical + legal):**
| Proposal source | Practical route |
|---|---|
| FBref | `soccerdata` Python package (rate-limited scraping) |
| StatsBomb | `statsbombpy` — free open data |
| Understat | `soccerdata` (Understat module) |
| Transfermarkt | Kaggle "transfermarkt-datasets" dump (avoids scraping ToS issues) |

- [ ] Downloader scripts per source in `etl/ingest/` — idempotent, resumable, rate-limited
- [ ] Raw files stored as-is (parquet/CSV/JSON) under `data/raw/<source>/<season>/`
- [ ] Manifest file logging what was downloaded and when
- [ ] Spot-check notebook validating row counts per league/season

⚠️ Raw player data contains PII (names, DOB, nationality). Keep `data/raw/` out of git and out of any shared artifacts per SOC2/ISO 27001.

---

## Phase 2 — ETL → PostgreSQL (Single Source of Truth) (4–6 days)

**Deliverable:** Normalized Postgres DB rebuilt from raw data with one command (`python -m etl.run`).

**Schema (SQLAlchemy + Alembic migrations):**
- `players` (identity, position, DOB, nationality)
- `clubs`, `leagues`, `seasons`
- `player_season_stats` (per-90 raw stats, one row per player-season-competition)
- `market_values` (time series per player)
- `transfers` (history)
- `team_tactical_profiles` (pressing intensity, possession %, line height, etc.)
- `entity_xref` — **cross-source ID mapping** (FBref ↔ Transfermarkt ↔ Understat). This is the hardest ETL problem; use fuzzy name+DOB+club matching with a manual-override CSV.

- [ ] Alembic migration chain from empty DB
- [ ] Transform jobs: raw → staging → normalized tables
- [ ] Data-quality checks (nulls, duplicates, orphan FKs) that fail loudly
- [ ] `pytest` suite over transforms with fixture data

---

## Phase 3 — Feature Engineering (3–4 days)

**Deliverable:** A `player_features` table + versioned feature pipeline shared by all models.

- [ ] Per-90 normalization (goals, xG, progressive passes/carries, pressures, tackles, interceptions)
- [ ] Rate features (passing %, dribble success %, aerial win %)
- [ ] Position percentiles and league percentiles (computed per season)
- [ ] League-strength adjustment coefficients
- [ ] Scaler/encoder artifacts saved with the feature set version (so serving matches training)
- [ ] Feature documentation table (name, definition, source columns)

---

## Phase 4 — ML Models (2–3 weeks; models are independent → parallelizable)

**Deliverable:** Five trained, evaluated, serialized models in `ml/models/` with a model registry manifest (version, metrics, feature-set version).

### 4.1 Player Similarity
- PyTorch autoencoder → player embeddings; FAISS index for nearest-neighbor search
- Output: top-N similar players + similarity score
- Sanity metric: known-similar pairs rank highly (qualitative eval sheet)

### 4.2 Market Value Prediction
- LightGBM regression on age, league, minutes, performance stats, intl caps, position, club strength
- Eval: MAE / RMSE on held-out seasons (time-based split, **not** random split — avoids leakage)
- SHAP values persisted for the explanation layer

### 4.3 Position Prediction
- CatBoost classifier → CAM / LW / CM / CDM / ST / …
- Eval: accuracy + confusion matrix; per-class F1

### 4.4 Potential Growth
- LightGBM regression predicting value/performance at +1y, +3y, +5y
- Training pairs built from historical player trajectories in the DB

### 4.5 Club Fit Engine (no ML)
- Weighted scoring: tactical profile match, age profile, financial feasibility, squad need, league suitability
- Weights in a config file → tunable without redeploys
- Output: Tactical Fit, Financial Fit, Squad Fit, Overall Score

---

## Phase 5 — FastAPI Backend (1–1.5 weeks)

**Deliverable:** Documented REST API serving DB queries + model inference, with Redis caching and auth.

**Endpoints:** `/search`, `/player/{id}`, `/similar`, `/predict/value`, `/predict/position`, `/predict/potential`, `/club-fit`, `/squad-analysis`, `/career-simulation`

- [x] Layered structure: routers (`app/api/`) → serving layer (`app/ml/`) → DB; Pydantic schemas throughout (`app/schemas.py`)
- [x] Models loaded once at startup (lifespan `warmup()`); FAISS indexes resident in memory (`similarity._load_mode` cached)
- [x] Redis caching for hot players/search (`ResponseCacheMiddleware`, TTL 300s) — degrades to no-op when Redis is down
- [x] Auth: JWT register/login/me, single role (`users` table, bcrypt); `get_current_user` dependency ready to gate routes
- [x] Rate limiting on public endpoints (`RateLimitMiddleware`, fixed-window per-IP)
- [x] OpenAPI docs auto-generated (/docs); integration tests per endpoint (18 backend tests, skip cleanly without DB)

**DONE** — all endpoints live + verified over real HTTP (Phase 5.1 @ 62e0c2d, 5.2 @ 7fcb17b). Every prediction returns `explain.*` driving factors for the LLM layer. Run from repo root: `PYTHONPATH=. uvicorn app.main:app --app-dir backend`.

---

## Phase 6 — LLM Explanation Layer (3–4 days)

**Deliverable:** `/explain` capability that turns model outputs into scout-style narratives.

**Hard rule from the proposal: the LLM never predicts — it only explains model outputs.**

- [x] Pipeline: model outputs (value/potential/position/club-fit/similarity + SHAP drivers) → structured prompt → Claude API → narrative (`app/llm/`)
- [x] Prompt templates per question type: report (development), club fit, comparison (`app/llm/prompts.py`)
- [x] Responses cached in Redis keyed by (player, model versions) — regenerate only when a model version or the LLM model changes (`service._version_tag`)
- [x] Guardrail: every claim comes from a model output/DB fact (echoed in `grounding`); temperature 0.2; system prompt forbids predicting/inventing

**DONE** (@ ca28ef7). Endpoints: `/players/{id}/explain`, `.../explain/club-fit/{club_id}`, `.../explain/comparison/{other_id}`. Pluggable provider: real Anthropic (`claude-sonnet-5`) when `ANTHROPIC_API_KEY` is set, deterministic **stub** otherwise so the pipeline works keyless. Live path covered by a mocked-client test.

---

## Phase 7 — React Frontend (1.5–2 weeks)

**Deliverable:** Full UI wired to the API.

| Page | Key components |
|---|---|
| Home | Search bar, trending players, featured analysis |
| Player Profile | Info card, **radar chart**, heatmap, strengths/weaknesses, market-value history chart |
| Similar Players | Cards: similarity %, playing style, market value |
| Club Finder | Club selector → tactical/financial fit + recommendation |
| Squad Analyzer | Squad upload → weak positions, imbalance, transfer recs |
| Career Simulator | "What if X joined Y?" → projected goals/assists/value/chemistry |

- [x] React Query for data fetching/caching; Recharts for radar/line charts
- [x] Debounced search-as-you-type against `/players/search`
- [x] Loading/error/empty states on every page
- [x] Auth flow (login/register) wired to backend JWT

**DONE** (@ 1236d00). All six pages built (Player Profile uses nested tabs: Overview / Similar / Club Fit / Career). Verified: `npm run build` (tsc + vite) clean, backend + built frontend boot together, CORS OK.
Scope notes: **heatmap deferred** (no event-level data — dropped in Phase 1 data acquisition); **Career Simulator** ships as the value-trajectory projection (the "what if X joined Y" chemistry angle is covered by the Club Fit page); AI report uses the Phase 6 **stub** until an `ANTHROPIC_API_KEY` is set (UI labels it). Support endpoints added: `/players/{id}/radar`, `/players/{id}/market-values`, `/clubs?q=`.

---

## Phase 8 — Deployment & Automation (3–5 days)

**Deliverable:** Live product with weekly self-updating data.

**Pipeline:** GitHub → GitHub Actions → Docker → Render → Cloudflare

- [ ] Dockerfiles: backend (multi-stage), frontend (static build → CDN)
- [ ] GitHub Actions: lint + test + build on PR; deploy to Render on merge to `main`
- [ ] Managed Postgres + Redis on Render; secrets via Render env vars
- [ ] Cloudflare in front (DNS, caching, TLS)
- [ ] **Weekly ETL cron** (GitHub Actions scheduled workflow): download latest data → update Postgres → optional model retrain → redeploy
- [ ] Alerting on ETL failure (Action failure notification)

---

## Phase 9 — Hardening & Polish (ongoing)

- [ ] Live-data endpoints (fixtures, injuries) from external API — the *only* live external calls, per proposal
- [ ] Model monitoring: track prediction drift between retrains
- [ ] E2E smoke test (Playwright) run in CI against staging
- [ ] README with architecture diagram, setup guide, screenshots

---

## Build Order & Dependencies

```
Phase 0 → 1 → 2 → 3 → 4 → 5 → 6 → 8
                         ↘ 7 ↗
```
- Frontend (7) can start against mocked API responses as soon as Phase 5 schemas are defined.
- The five models in Phase 4 are independent — build Similarity + Market Value first (they power the most pages), then Position, Potential, Club Fit.

## Suggested MVP cut (if you want something demoable fast)
Phases 0–3 + Market Value & Similarity models + `/search`, `/player/{id}`, `/similar`, `/predict/value` + Home & Player Profile pages. Everything else layers on top.

**Total estimate: ~8–10 weeks solo at steady pace; MVP in ~3–4 weeks.**
