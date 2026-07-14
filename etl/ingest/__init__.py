"""Raw data ingestion for Scout OS.

Each source module exposes a `run(...)` function that downloads raw data into
`data/raw/<source>/` and records what it fetched in the manifest. All
downloaders are idempotent (skip already-fetched artifacts unless forced) and
resumable (each league/season/dataset is a separate artifact).
"""
