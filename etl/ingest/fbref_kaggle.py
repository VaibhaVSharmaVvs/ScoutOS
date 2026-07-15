"""FBref detailed season stats from Kaggle (workaround for hollow soccerdata pull).

soccerdata's headless fetch returns stripped FBref pages here, so the detailed
categories (passing/defense/possession/gca) have no values. Community Kaggle
datasets carry the full, populated detailed stats. This ingester downloads them
and normalizes each publisher's schema to ONE canonical column set, saved as
`data/raw/fbref_kaggle/player_season_<code>.parquet`.

Covered seasons (all have Born -> clean resolution to canonical players):
  2122, 2223  -> vivovinco (semicolon/latin-1, one wide file)
  2425        -> hubertsidorowicz (comma, wide, _stats_<cat> suffixes)
Not here: 2324 (anisguechtouli exists but lacks Born) and 2021 (absent) — those
are the worldfootballR evaluation targets.
"""

from __future__ import annotations

import os

import pandas as pd

from etl.config import SOURCE_DIRS
from etl.ingest.base import Artifact, Manifest, log, rel, save_parquet, utcnow_iso

SOURCE = "fbref_kaggle"

# Canonical detailed metrics (target column names).
CANON = [
    "player", "squad", "comp", "season", "born", "nation", "pos", "age", "mp",
    "minutes", "nineties", "goals", "assists", "shots", "sot", "xg", "npxg", "xag",
    "pass_cmp", "pass_att", "pass_cmp_pct", "pass_prog", "pass_final_third",
    "key_passes", "ppa", "prog_pass_dist", "touches", "carries", "carries_prog",
    "carries_prog_dist", "take_ons_att", "take_ons_succ", "prog_rec", "tackles",
    "tackles_won", "tackles_def3rd", "interceptions", "blocks", "tkl_plus_int",
    "clearances", "dribblers_challenged", "sca", "gca", "recoveries",
    "aerials_won", "aerials_lost", "fouls", "fouled",
]

# source column -> canonical
VIVO_MAP = {
    "Player": "player", "Squad": "squad", "Comp": "comp", "Born": "born",
    "Nation": "nation", "Pos": "pos", "Age": "age", "MP": "mp", "Min": "minutes",
    "90s": "nineties", "Goals": "goals", "Assists": "assists", "Shots": "shots",
    "SoT": "sot", "PasTotCmp": "pass_cmp", "PasTotAtt": "pass_att",
    "PasTotCmp%": "pass_cmp_pct", "PasProg": "pass_prog", "Pas3rd": "pass_final_third",
    "PPA": "ppa", "PasTotPrgDist": "prog_pass_dist", "Touches": "touches",
    "Carries": "carries", "CarProg": "carries_prog", "CarPrgDist": "carries_prog_dist",
    "ToAtt": "take_ons_att", "ToSuc": "take_ons_succ", "RecProg": "prog_rec",
    "Tkl": "tackles", "TklWon": "tackles_won", "TklDef3rd": "tackles_def3rd",
    "Int": "interceptions", "Blocks": "blocks", "Tkl+Int": "tkl_plus_int",
    "Clr": "clearances", "TklDri": "dribblers_challenged", "SCA": "sca", "GCA": "gca",
    "Recov": "recoveries", "AerWon": "aerials_won", "AerLost": "aerials_lost",
    "Fls": "fouls", "Fld": "fouled",
}

HUBERT_MAP = {
    "Player": "player", "Squad": "squad", "Comp": "comp", "Born": "born",
    "Nation": "nation", "Pos": "pos", "Age": "age", "MP": "mp", "Min": "minutes",
    "90s": "nineties", "Gls": "goals", "Ast": "assists", "Sh": "shots", "SoT": "sot",
    "xG": "xg", "npxG": "npxg", "xAG": "xag", "Cmp": "pass_cmp", "Att": "pass_att",
    "Cmp%": "pass_cmp_pct", "PrgP": "pass_prog", "1/3": "pass_final_third",
    "KP": "key_passes", "PPA": "ppa", "PrgDist": "prog_pass_dist", "Touches": "touches",
    "Carries": "carries", "PrgC": "carries_prog", "Succ": "take_ons_succ",
    "Tkl": "tackles", "TklW": "tackles_won", "Def 3rd": "tackles_def3rd",
    "Int": "interceptions", "Blocks_stats_defense": "blocks", "Tkl+Int": "tkl_plus_int",
    "Clr": "clearances", "SCA": "sca", "GCA": "gca", "Recov": "recoveries",
    "Won": "aerials_won", "Lost_stats_misc": "aerials_lost", "Fls": "fouls",
    "Fld_stats_misc": "fouled",
}

# season code -> (kaggle ref, filename glob, read kwargs, mapping, per90)
# per90=True means the source stores per-90 rates; we multiply counting metrics
# by 90s to get season TOTALS (consistent with hubertsidorowicz and our other
# sources, which store totals).
DATASETS = {
    "2122": ("vivovinco/20212022-football-player-stats", "*.csv",
             {"sep": ";", "encoding": "latin-1"}, VIVO_MAP, True),
    "2223": ("vivovinco/20222023-football-player-stats", "*.csv",
             {"sep": ";", "encoding": "latin-1"}, VIVO_MAP, True),
    "2425": ("hubertsidorowicz/football-players-stats-2024-2025", "players_data-2024_2025.csv",
             {}, HUBERT_MAP, False),
}

# identity + rate columns are NOT scaled by 90s; everything else is a count.
_NON_COUNTING = {
    "player", "squad", "comp", "season", "born", "nation", "pos", "age", "mp",
    "minutes", "nineties", "pass_cmp_pct",
}
COUNTING_COLS = [c for c in CANON if c not in _NON_COUNTING]


def _normalize(df: pd.DataFrame, mapping: dict, season: str, per90: bool) -> pd.DataFrame:
    present = {src: dst for src, dst in mapping.items() if src in df.columns}
    out = df[list(present)].rename(columns=present).copy()
    out["season"] = season
    for col in CANON:
        if col not in out.columns:
            out[col] = pd.NA
    out = out[CANON]
    if per90:
        nineties = pd.to_numeric(out["nineties"], errors="coerce")
        for c in COUNTING_COLS:
            vals = pd.to_numeric(out[c], errors="coerce")
            out[c] = (vals * nineties).round()
    return out


def run(force: bool = False) -> None:
    import glob

    import kagglehub

    manifest = Manifest()
    for season, (ref, pattern, kw, mapping, per90) in DATASETS.items():
        if manifest.has(SOURCE, "player_season", season) and not force:
            log.info("skip %s (in manifest)", season)
            continue
        try:
            path = kagglehub.dataset_download(ref)
        except Exception as exc:  # noqa: BLE001
            log.error("FAILED download %s: %s", ref, exc)
            continue
        files = glob.glob(os.path.join(path, "**", pattern), recursive=True)
        if not files:
            log.error("no file matching %s in %s", pattern, ref)
            continue
        df = pd.read_csv(files[0], **kw)
        norm = _normalize(df, mapping, season, per90)
        out_path = SOURCE_DIRS[SOURCE] / f"player_season_{season}.parquet"
        rows = save_parquet(norm, out_path)
        mapped = sum(1 for c in CANON if norm[c].notna().any())
        manifest.add(Artifact(SOURCE, "player_season", season, rel(out_path), rows, utcnow_iso()))
        log.info("saved %s: %d players, %d/%d canonical cols populated (from %s)",
                 season, rows, mapped, len(CANON), ref.split("/")[0])

    log.info("fbref_kaggle done. Manifest counts: %s", manifest.summary())
