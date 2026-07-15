"""Entity resolution: build canonical players + cross-source xref (conservative).

Pool = FBref players (the stat backbone: all 5 leagues x 5 seasons), keyed by
(normalized_name, birth_year). Each is matched to:
  - Transfermarkt (the bio/value spine): EXACT normalized_name + birth_year.
      1 candidate  -> confident link (bio taken from TM: DOB, nationality, ...)
      0 candidates -> FBref-only canonical (stats but no market value)
      >1 candidates-> AMBIGUOUS -> flagged, no link
  - Understat: EXACT normalized_name against the canonical pool (Understat has
      no birth year, so a name hitting >1 canonical is AMBIGUOUS -> flagged).

Conservative = exact keys only, no fuzzy. Ambiguous/unmatched are reported (and
written to data/processed/entity_resolution_report.csv) rather than guessed.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.db.models import EntityXref, Player
from etl.load.db import SessionLocal, log
from etl.load.normalize import normalize_name

FBREF_STD = "data/raw/fbref/player_season/standard.parquet"
UNDERSTAT = "data/raw/understat/player_season.parquet"
TM_PLAYERS = "data/raw/transfermarkt/players.csv"
REPORT = Path("data/processed/entity_resolution_report.csv")


def _fbref_players() -> pd.DataFrame:
    df = pd.read_parquet(FBREF_STD, columns=["player", "nation", "pos", "born"])
    df = df.dropna(subset=["player", "born"])
    df["norm"] = df["player"].map(normalize_name)
    df["birth_year"] = df["born"].astype(int)
    agg = (
        df.groupby(["norm", "birth_year"])
        .agg(full_name=("player", "first"),
             nationality=("nation", lambda s: s.dropna().iloc[0] if s.notna().any() else None),
             position=("pos", lambda s: s.dropna().iloc[0] if s.notna().any() else None))
        .reset_index()
    )
    return agg


def _tm_index() -> dict[str, list[dict]]:
    tm = pd.read_csv(TM_PLAYERS)
    tm = tm.dropna(subset=["name", "date_of_birth"])
    tm["norm"] = tm["name"].map(normalize_name)
    tm["birth_year"] = pd.to_datetime(tm["date_of_birth"], errors="coerce").dt.year
    tm = tm.dropna(subset=["birth_year"])
    idx: dict[str, list[dict]] = {}
    for r in tm.itertuples(index=False):
        idx.setdefault(r.norm, []).append({
            "player_id": int(r.player_id), "birth_year": int(r.birth_year),
            "dob": r.date_of_birth, "nationality": getattr(r, "country_of_citizenship", None),
            "position": getattr(r, "sub_position", None), "foot": getattr(r, "foot", None),
            "height": getattr(r, "height_in_cm", None),
        })
    return idx


def _understat_players() -> pd.DataFrame:
    us = pd.read_parquet(UNDERSTAT, columns=["player", "player_id", "position"])
    us = us.dropna(subset=["player", "player_id"])
    us["norm"] = us["player"].map(normalize_name)
    return (us.groupby("player_id")
              .agg(norm=("norm", "first"), full_name=("player", "first"),
                   position=("position", "first"))
              .reset_index())


def run() -> None:
    fb = _fbref_players()
    tm_idx = _tm_index()
    us = _understat_players()
    log.info("pool: fbref=%d players, tm names=%d, understat=%d players",
             len(fb), len(tm_idx), len(us))

    session = SessionLocal()
    flags: list[dict] = []
    name_to_players: dict[str, list[Player]] = {}
    stats = {"tm_linked": 0, "tm_none": 0, "tm_ambiguous": 0}
    try:
        # --- 1. FBref pool -> canonical players + TM link ---
        for row in fb.itertuples(index=False):
            cands = [c for c in tm_idx.get(row.norm, []) if c["birth_year"] == row.birth_year]
            dob = nat = pos = foot = height = None
            if len(cands) == 1:
                c = cands[0]
                dob = pd.to_datetime(c["dob"]).date() if c["dob"] else None
                nat, pos, foot = c["nationality"], c["position"], c["foot"]
                height = int(c["height"]) if pd.notna(c["height"]) else None
                stats["tm_linked"] += 1
            elif len(cands) == 0:
                stats["tm_none"] += 1
                nat, pos = row.nationality, row.position
            else:
                stats["tm_ambiguous"] += 1
                nat, pos = row.nationality, row.position
                flags.append({"type": "tm_ambiguous", "name": row.full_name,
                              "birth_year": row.birth_year,
                              "detail": f"{len(cands)} TM ids: {[c['player_id'] for c in cands]}"})

            player = Player(
                full_name=row.full_name, normalized_name=row.norm,
                date_of_birth=dob, birth_year=int(row.birth_year),
                nationality=nat, primary_position=pos, foot=foot, height_cm=height,
            )
            session.add(player)
            session.flush()  # get player.id
            session.add(EntityXref(player_id=player.id, source="fbref",
                                   source_key=f"{row.norm}|{row.birth_year}",
                                   match_method="pool", confidence=1.0))
            if len(cands) == 1:
                session.add(EntityXref(player_id=player.id, source="transfermarkt",
                                       source_id=str(cands[0]["player_id"]),
                                       match_method="exact", confidence=1.0))
            name_to_players.setdefault(row.norm, []).append(player)

        # --- 2. Understat -> link to canonical by exact name ---
        us_stats = {"linked": 0, "ambiguous": 0, "none": 0}
        for row in us.itertuples(index=False):
            matches = name_to_players.get(row.norm, [])
            if len(matches) == 1:
                session.add(EntityXref(player_id=matches[0].id, source="understat",
                                       source_id=str(int(row.player_id)),
                                       match_method="exact_name", confidence=0.9))
                us_stats["linked"] += 1
            elif len(matches) > 1:
                us_stats["ambiguous"] += 1
                flags.append({"type": "understat_ambiguous", "name": row.full_name,
                              "birth_year": "", "detail": f"{len(matches)} canonical same name"})
            else:
                us_stats["none"] += 1
                flags.append({"type": "understat_no_match", "name": row.full_name,
                              "birth_year": "", "detail": f"understat_id={int(row.player_id)}"})

        session.commit()
    finally:
        session.close()

    # --- report ---
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(flags).to_csv(REPORT, index=False)
    total = len(fb)
    log.info("=== ENTITY RESOLUTION (conservative) ===")
    log.info("canonical players (from FBref): %d", total)
    log.info("  TM linked (name+birthyear, 1:1): %d (%.1f%%)",
             stats["tm_linked"], 100 * stats["tm_linked"] / total)
    log.info("  TM no candidate (FBref-only, no value): %d (%.1f%%)",
             stats["tm_none"], 100 * stats["tm_none"] / total)
    log.info("  TM AMBIGUOUS (flagged): %d", stats["tm_ambiguous"])
    log.info("understat: linked=%d, AMBIGUOUS=%d, no_match=%d",
             us_stats["linked"], us_stats["ambiguous"], us_stats["none"])
    log.info("flags written: %d -> %s", len(flags), REPORT)
