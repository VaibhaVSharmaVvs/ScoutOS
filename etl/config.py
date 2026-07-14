"""Central configuration for the Scout OS data pipeline.

Leagues, seasons, storage paths, and per-source settings live here so ingest,
transform, and load stages share one source of truth.
"""

from __future__ import annotations

import os
from pathlib import Path

# --- Storage layout -----------------------------------------------------------
# Repo root is one level up from etl/.
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("SCOUTOS_DATA_DIR", REPO_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"

# soccerdata keeps its own untouched HTML/JSON cache; we point it inside raw/
# so "raw data remains untouched" while we also save parsed parquet alongside.
SOURCE_DIRS = {
    "fbref": RAW_DIR / "fbref",
    "understat": RAW_DIR / "understat",
    "statsbomb": RAW_DIR / "statsbomb",
    "transfermarkt": RAW_DIR / "transfermarkt",
}

MANIFEST_PATH = RAW_DIR / "manifest.json"

# --- Leagues ------------------------------------------------------------------
# soccerdata league IDs. UCL/UEL are not in soccerdata's default league dict;
# add them via a custom league_dict.json before enabling here.
BIG5_LEAGUES = [
    "ENG-Premier League",
    "ESP-La Liga",
    "ITA-Serie A",
    "GER-Bundesliga",
    "FRA-Ligue 1",
]

# --- Seasons ------------------------------------------------------------------
# soccerdata 4-digit codes: "2425" == 2024-25. Most recent completed seasons.
DEFAULT_SEASONS = ["2021", "2122", "2223", "2324", "2425"]

# --- FBref -------------------------------------------------------------------
# soccerdata 1.9.0 ships a working (Cloudflare-bypassing) parser but restricts
# season stats to {standard, shooting, playing_time, misc, keeper}. Its code
# path is generic (page=stat_type, table id=stats_{stat_type}), so widening the
# gate recovers the detailed categories — see etl/ingest/_fbref_patch.py, which
# is what FBrefExtended uses. Names below are FBref's native page slugs:
#   gca = goal & shot creation. (keeper_adv omitted: needs a different slug.)
# These detailed stats (tackles, interceptions, progressive passes/carries,
# passing accuracy, shot creation) are required for the position & similarity
# models per the proposal's Feature Engineering section.
FBREF_PLAYER_STAT_TYPES = [
    "standard",
    "shooting",
    "passing",
    "passing_types",
    "gca",
    "defense",
    "possession",
    "playing_time",
    "misc",
    "keeper",
]

# Team tactical profile inputs (outfield-relevant categories).
FBREF_TEAM_STAT_TYPES = [
    "standard",
    "shooting",
    "passing",
    "passing_types",
    "gca",
    "defense",
    "possession",
    "misc",
]

# --- Throttling ---------------------------------------------------------------
# soccerdata throttles requests internally; this is an extra courtesy delay
# between our own top-level pulls (seconds).
REQUEST_DELAY_SECONDS = float(os.getenv("SCOUTOS_REQUEST_DELAY", "2"))

# --- Transfermarkt ------------------------------------------------------------
# Kaggle dataset providing player market values & transfer history.
TRANSFERMARKT_KAGGLE_DATASET = "davidcariboo/player-scores"
