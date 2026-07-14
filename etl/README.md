# Scout OS — ETL Pipeline

## Phase 1 — Data Acquisition (implemented)

Idempotent, resumable, rate-limited downloaders. Each writes raw artifacts to
`data/raw/<source>/` (gitignored — contains PII) and records them in
`data/raw/manifest.json`. Re-running skips artifacts already in the manifest;
use `--force` to refresh.

### Setup

```bash
cd etl
pip install ".[dev]"          # or: pip install soccerdata statsbombpy pandas pyarrow tqdm
```

### Run

```bash
# From the repo root (so `etl` is importable as a package):
python -m etl.ingest --source statsbomb                 # free GitHub JSON, most reliable
python -m etl.ingest --source understat                 # xG stats, Big-5 domestic
python -m etl.ingest --source understat --seasons 2223 2324 2425
python -m etl.ingest --source fbref                     # needs Chrome; slow (Cloudflare)
python -m etl.ingest --source transfermarkt             # needs Kaggle credentials
python -m etl.ingest --source all

python -m etl.validate                                  # spot-check row counts
```

### Sources & scope

| Source | Via | Coverage | Notes |
|---|---|---|---|
| FBref | `soccerdata` | Big-5 domestic, 5 seasons | Headless browser + rate-limited; run as a long job |
| Understat | `soccerdata` | Big-5 domestic | xG/xA; lightest scrape, most reliable |
| StatsBomb | `statsbombpy` | Curated open-data comps | Event-level; `--with-events` for full events (large) |
| Transfermarkt | Kaggle dump `davidcariboo/player-scores` | Market values + transfers | Needs `KAGGLE_USERNAME`/`KAGGLE_KEY` or `~/.kaggle/kaggle.json` |

### Known limitations (follow-ups)

- **UCL / Europa League** are not in soccerdata's default league dict. To add
  them, define a custom `league_dict.json` (see soccerdata docs) and append the
  IDs to `BIG5_LEAGUES` in `config.py`.
- **FBref** requires Chrome/Chromium for scraping. Not run in CI; execute the
  full multi-season pull locally or on a worker with a browser installed.
- **StatsBomb open data** covers only selected competitions/seasons — it is the
  event-level supplement, not the primary season-stats source.

## Layout

```
etl/
├── config.py            # leagues, seasons, paths, per-source settings
├── ingest/
│   ├── base.py          # Manifest, atomic parquet save, paths
│   ├── fbref.py
│   ├── understat.py
│   ├── statsbomb.py
│   ├── transfermarkt.py
│   └── __main__.py      # CLI
└── validate.py          # spot-check: row counts, missing/empty artifacts
```

## Next (Phase 2)

Transform these raw artifacts into the normalized PostgreSQL schema
(`transform/`, `load/`, Alembic migrations). See `PLAN.md`.
