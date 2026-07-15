"""FBref detailed season stats from Kaggle (workaround for hollow soccerdata pull).

soccerdata's headless fetch returns stripped FBref pages here, so the detailed
categories (passing/defense/possession/gca) have no values. Community Kaggle
datasets carry the full, populated detailed stats. This ingester downloads them
and normalizes each publisher's schema to ONE canonical column set, saved as
`data/raw/fbref_kaggle/player_season_<code>.parquet`.

Covered seasons (all have Born -> clean resolution to canonical players):
  2021, 2122, 2223, 2324 -> akshankrithick (one cleaned CSV per season, uniform
                            schema, counting stats as totals, SCA/GCA per-90)
  2425                   -> hubertsidorowicz (wide, _stats_<cat> suffixes, totals)
Two sources cover all five Big-5 seasons; no worldfootballR/scraping needed.
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
AKSHAN_MAP = {
    "player": "player", "squad": "squad", "comp": "comp", "born": "born",
    "nation": "nation", "pos": "pos", "age": "age", "Matches Played": "mp",
    "Avg Mins per Match": "minutes",  # actually total minutes in this dataset
    "Goals": "goals", "Assists": "assists", "Expected Goals": "xg", "Exp NPG": "npxg",
    "Total Shots": "shots", "Passes Completed": "pass_cmp",
    "Passes Attempted": "pass_att", "Pass completion %": "pass_cmp_pct",
    "Progressive Passes": "pass_prog", "1/3": "pass_final_third",
    "Key passes": "key_passes", "Passes into penalty area": "ppa",
    "Progressive passes distance": "prog_pass_dist",
    "Progressive Carries": "carries_prog", "Take ons attempted": "take_ons_att",
    "Tackles attempted": "tackles", "Tackles Won": "tackles_won",
    "Interceptions": "interceptions", "Clearances": "clearances",
    "Shot creating actions p 90": "sca", "Goal creating actions p 90": "gca",
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

# season code -> (kaggle ref, filename (relative), read kwargs, mapping, per90_cols)
# per90_cols: canonical cols the source stores as per-90 -> multiplied by 90s to
# season TOTALS (so all sources/seasons are consistent totals).
DATASETS = {
    "2021": ("akshankrithick/fbref-2017-2024-for-europes-top-5-leagues",
             "cleaned_2020-21.csv", {}, AKSHAN_MAP, {"sca", "gca"}),
    "2122": ("akshankrithick/fbref-2017-2024-for-europes-top-5-leagues",
             "cleaned_2021-22.csv", {}, AKSHAN_MAP, {"sca", "gca"}),
    "2223": ("akshankrithick/fbref-2017-2024-for-europes-top-5-leagues",
             "cleaned_2022-23.csv", {}, AKSHAN_MAP, {"sca", "gca"}),
    "2324": ("akshankrithick/fbref-2017-2024-for-europes-top-5-leagues",
             "cleaned_2023-24.csv", {}, AKSHAN_MAP, {"sca", "gca"}),
    "2425": ("hubertsidorowicz/football-players-stats-2024-2025",
             "players_data-2024_2025.csv", {}, HUBERT_MAP, set()),
}


def _normalize(df: pd.DataFrame, mapping: dict, season: str, per90_cols: set) -> pd.DataFrame:
    present = {src: dst for src, dst in mapping.items() if src in df.columns}
    out = df[list(present)].rename(columns=present).copy()
    out["season"] = season
    for col in CANON:
        if col not in out.columns:
            out[col] = pd.NA
    out = out[CANON]
    # derive 90s from minutes when the source has no explicit 90s column
    nineties = pd.to_numeric(out["nineties"], errors="coerce")
    if nineties.isna().all():
        nineties = pd.to_numeric(out["minutes"], errors="coerce") / 90
        out["nineties"] = nineties.round(1)
    for c in per90_cols:
        out[c] = (pd.to_numeric(out[c], errors="coerce") * nineties).round()
    return out


def run(force: bool = False) -> None:
    import glob

    import kagglehub

    manifest = Manifest()
    for season, (ref, pattern, kw, mapping, per90_cols) in DATASETS.items():
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
        norm = _normalize(df, mapping, season, per90_cols)
        out_path = SOURCE_DIRS[SOURCE] / f"player_season_{season}.parquet"
        rows = save_parquet(norm, out_path)
        mapped = sum(1 for c in CANON if norm[c].notna().any())
        manifest.add(Artifact(SOURCE, "player_season", season, rel(out_path), rows, utcnow_iso()))
        log.info("saved %s: %d players, %d/%d canonical cols populated (from %s)",
                 season, rows, mapped, len(CANON), ref.split("/")[0])

    log.info("fbref_kaggle done. Manifest counts: %s", manifest.summary())
