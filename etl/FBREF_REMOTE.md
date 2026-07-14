# Running the FBref pull on another machine

FBref is behind Cloudflare and gets IP-blocked on some networks. If the primary
machine is blocked, run the FBref download on a different network (e.g. home
wifi) and copy the results back. FBref data is identical regardless of where
it's fetched.

## On the OTHER machine

Requirements: **Python 3.11+** and **Google Chrome** installed (soccerdata
drives a headless browser).

```bash
git clone https://github.com/VaibhaVSharmaVvs/ScoutOS.git
cd ScoutOS

# Install ETL dependencies (from the etl/ project):
pip install ./etl                      # installs soccerdata, pandas, pyarrow, tqdm...

# Run the FBref pull from the REPO ROOT (Big-5, 5 seasons — this is slow,
# rate-limited; expect 30-90+ min):
python -m etl.ingest --source fbref

# Sanity check:
python -m etl.validate
```

This writes:
- `data/raw/fbref/` — parsed parquet (player_season, team_season, schedule) plus
  soccerdata's raw HTML cache under `data/raw/fbref/_cache/`
- `data/raw/manifest.json` — with `fbref:*` entries

## Bring the data back

Zip and transfer these two paths to the primary machine:
1. `data/raw/fbref/`  (the whole folder)
2. `data/raw/manifest.json`  (rename it, e.g. `fbref_manifest.json`, so it does
   not overwrite the primary machine's manifest)

## On the PRIMARY machine

```bash
# 1. Drop the fbref folder in:
#    copy the transferred data/raw/fbref/  ->  ScoutOS/data/raw/fbref/

# 2. Merge the manifest entries (union; does not touch understat/statsbomb/
#    transfermarkt entries already present):
python -m etl.merge_manifest path/to/fbref_manifest.json

# 3. Confirm everything is present:
python -m etl.validate
```

Then we're clear to start Phase 2 (ETL -> PostgreSQL).

## Alternative: skip the copy-back dance

If the other machine can reach GitHub but you'd rather not move files manually,
you can't push `data/raw/` (it's gitignored by design — PII + large). The
folder copy above is the intended path.
