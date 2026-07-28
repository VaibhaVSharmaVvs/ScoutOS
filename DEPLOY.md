# Deployment & Automation (Phase 8)

What's in the repo vs. what needs your accounts. Everything here is a
**recommendation/template** — applying it (and the cost that implies) is your call.

## In the repo (code, reviewable)
- **CI** — `.github/workflows/ci.yml`: lint (maintained code), tests, frontend build on every push/PR.
- **Backend image** — `deploy/Dockerfile.backend` (root context, includes `ml`/`etl` + model deps). `.dockerignore` keeps `data/raw` and `ml/artifacts` out of the build.
- **Frontend image** — `frontend/Dockerfile` (nginx static) — unchanged, already works.
- **Compose** — `docker-compose.yml` backend now builds from the root image and mounts `ml`/`etl`/`config` + local artifacts, so the full stack (incl. model serving) runs locally.
- **Render blueprint** — `render.yaml` (backend web + static frontend + Postgres + Redis + artifacts disk).
- **Weekly refresh** — `.github/workflows/etl-refresh.yml` (ingest → load → features → retrain → checks). Also the acceptance test for the 2025-26 roll-forward.

## Your steps (accounts / secrets)
1. **Render:** New → Blueprint → this repo → apply `render.yaml`. Adjust plans/region.
2. **Backend env vars** (Render dashboard): `ANTHROPIC_API_KEY` (real LLM narratives), `WEBAUTHN_RP_ID`, `WEBAUTHN_ORIGIN` (your domain, HTTPS). `DATABASE_URL`/`REDIS_URL`/`JWT_SECRET` come from the blueprint.
3. **Frontend env:** `VITE_API_BASE_URL` = backend public URL.
4. **GitHub Actions secrets** (for the weekly refresh): `DATABASE_URL` (managed Postgres), `KAGGLE_USERNAME`, `KAGGLE_KEY`. Rotate the Kaggle key that was pasted in chat earlier.
5. **First data load:** run the `etl-refresh` workflow once manually (Actions → Run workflow) to populate the managed DB and produce artifacts.
6. **Cloudflare:** point DNS at the Render URLs; enable TLS + caching for the static frontend. Tighten backend CORS from `*` to the frontend origin (in `app/main.py`).

## Model artifacts in production
The image does **not** bake in `ml/artifacts` (gitignored, and they change on retrain). Pick one delivery path:
- **(a) Render persistent disk** (blueprint mounts one at `/app/ml/artifacts`): the refresh job writes artifacts there, backend reads on `warmup()`. Simplest.
- **(b) Object storage** (S3/R2): refresh uploads, backend downloads on start.
- **(c) Bake into the image**: refresh trains, then build/push a new image with artifacts + redeploy.

The `etl-refresh.yml` has a `TODO(deploy)` where this hook goes.

## Prod hardening carried here (Phase 8/9)
- Tighten CORS/auth (currently open for dev).
- Redis-backed rate limiting (in-memory now → per-worker only).
- Self-host the Geist font (currently Google Fonts) for offline/CSP.
- Failure alerting on the refresh workflow (stub job present → wire to Slack/email).

## Verification status
- ✅ CI commands verified locally (scoped lint clean, tests pass/skip, `npm run build` clean).
- ⏳ **Docker images not built here** (Docker Desktop was down) — `docker build` + a compose smoke test are pending on a machine with Docker running.
- ⏳ Render/Cloudflare provisioning is account-dependent (your action).
