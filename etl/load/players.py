"""Entity resolution: canonical players + cross-source xref.

Staged, conservative-to-recovering:
  1. EXACT   normalized_name (+birth_year for TM)
  2. FUZZY   TM: same birth_year + fuzzy name, unique candidate >= threshold
             US: fuzzy name + CLUB OVERLAP (Understat has no DOB), unique
  3. OVERRIDE etl/load/overrides.csv pins hard/ambiguous cases (committed)

Pool = FBref players (stat backbone), keyed by (normalized_name, birth_year).
Anything still ambiguous after all stages is flagged to
data/processed/entity_resolution_report.csv, never guessed.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process
from sqlalchemy import delete

from app.db.models import EntityXref, Player
from etl.load.db import SessionLocal, log
from etl.load.normalize import normalize_name

FBREF_STD = "data/raw/fbref/player_season/standard.parquet"
UNDERSTAT = "data/raw/understat/player_season.parquet"
TM_PLAYERS = "data/raw/transfermarkt/players.csv"
REPORT = Path("data/processed/entity_resolution_report.csv")
OVERRIDES = Path("etl/load/overrides.csv")

TM_NAME_THRESHOLD = 90  # birth_year already constrains
US_NAME_THRESHOLD = 87
TEAM_THRESHOLD = 85


# --- source readers -----------------------------------------------------------
def _fbref_players() -> pd.DataFrame:
    df = pd.read_parquet(FBREF_STD, columns=["player", "nation", "pos", "born", "team"])
    df = df.dropna(subset=["player", "born"])
    df["norm"] = df["player"].map(normalize_name)
    df["birth_year"] = df["born"].astype(int)
    df["team_norm"] = df["team"].map(normalize_name)
    return (
        df.groupby(["norm", "birth_year"])
        .agg(full_name=("player", "first"),
             nationality=("nation", lambda s: s.dropna().iloc[0] if s.notna().any() else None),
             position=("pos", lambda s: s.dropna().iloc[0] if s.notna().any() else None),
             teams=("team_norm", lambda s: set(s.dropna())))
        .reset_index()
    )


def _tm_records() -> list[dict]:
    tm = pd.read_csv(TM_PLAYERS).dropna(subset=["name", "date_of_birth"])
    tm["norm"] = tm["name"].map(normalize_name)
    tm["birth_year"] = pd.to_datetime(tm["date_of_birth"], errors="coerce").dt.year
    tm = tm.dropna(subset=["birth_year"])
    recs = []
    for r in tm.itertuples(index=False):
        recs.append({
            "player_id": int(r.player_id), "norm": r.norm, "birth_year": int(r.birth_year),
            "dob": r.date_of_birth, "nationality": getattr(r, "country_of_citizenship", None),
            "position": getattr(r, "sub_position", None), "foot": getattr(r, "foot", None),
            "height": getattr(r, "height_in_cm", None),
        })
    return recs


def _understat_players() -> pd.DataFrame:
    us = pd.read_parquet(UNDERSTAT, columns=["player", "player_id", "position", "team"])
    us = us.dropna(subset=["player", "player_id"])
    us["norm"] = us["player"].map(normalize_name)
    us["team_norm"] = us["team"].map(normalize_name)
    return (us.groupby("player_id")
              .agg(norm=("norm", "first"), full_name=("player", "first"),
                   position=("position", "first"), teams=("team_norm", lambda s: set(s.dropna())))
              .reset_index())


def _load_overrides() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"tm": [], "understat": []}
    if OVERRIDES.exists():
        with OVERRIDES.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("kind") in out:
                    out[row["kind"]].append(row)
    return out


def _teams_overlap(a: set[str], b: set[str]) -> bool:
    return any(fuzz.token_set_ratio(x, y) >= TEAM_THRESHOLD for x in a for y in b if x and y)


# --- resolution ---------------------------------------------------------------
def run() -> None:
    fb = _fbref_players()
    tm_recs = _tm_records()
    us = _understat_players()
    overrides = _load_overrides()

    # TM lookups
    tm_by_year: dict[int, list[dict]] = {}
    tm_exact: dict[tuple[str, int], list[dict]] = {}
    for r in tm_recs:
        tm_by_year.setdefault(r["birth_year"], []).append(r)
        tm_exact.setdefault((r["norm"], r["birth_year"]), []).append(r)
    tm_by_id = {r["player_id"]: r for r in tm_recs}
    tm_override = {o["key"]: int(o["target"]) for o in overrides["tm"]}

    log.info("pool: fbref=%d, tm=%d, understat=%d | overrides tm=%d us=%d",
             len(fb), len(tm_recs), len(us), len(overrides["tm"]), len(overrides["understat"]))

    session = SessionLocal()
    flags: list[dict] = []
    canon: list[dict] = []  # {norm, birth_year, teams, player}
    s = {"tm_exact": 0, "tm_fuzzy": 0, "tm_override": 0, "tm_none": 0, "tm_ambiguous": 0}
    try:
        # Idempotent full rebuild of the canonical layer (players -> xref cascade).
        session.execute(delete(EntityXref))
        session.execute(delete(Player))
        session.commit()
        for row in fb.itertuples(index=False):
            key = f"{row.norm}|{row.birth_year}"
            tm_rec = None
            method = None
            # 1. override
            if key in tm_override:
                tm_rec = tm_by_id.get(tm_override[key]); method = "override"; s["tm_override"] += 1
            # 2. exact
            if tm_rec is None:
                exact = tm_exact.get((row.norm, row.birth_year), [])
                ids = {r["player_id"] for r in exact}
                if len(ids) == 1:
                    tm_rec = exact[0]; method = "exact"; s["tm_exact"] += 1
                elif len(ids) > 1:
                    s["tm_ambiguous"] += 1
                    flags.append({"type": "tm_ambiguous", "key": key, "name": row.full_name,
                                  "detail": f"exact ids {sorted(ids)}"})
            # 3. fuzzy within same birth_year
            if tm_rec is None and method is None:
                pool = tm_by_year.get(row.birth_year, [])
                if pool:
                    names = [r["norm"] for r in pool]
                    hits = process.extract(row.norm, names, scorer=fuzz.token_set_ratio,
                                            limit=3, score_cutoff=TM_NAME_THRESHOLD)
                    good_ids = {pool[i]["player_id"] for _, sc, i in hits}
                    if len(good_ids) == 1:
                        tm_rec = pool[hits[0][2]]; method = "fuzzy"; s["tm_fuzzy"] += 1
                    elif len(good_ids) > 1:
                        s["tm_ambiguous"] += 1
                        flags.append({"type": "tm_fuzzy_ambiguous", "key": key,
                                      "name": row.full_name, "detail": f"ids {sorted(good_ids)}"})
                    else:
                        s["tm_none"] += 1
                else:
                    s["tm_none"] += 1

            dob = pd.to_datetime(tm_rec["dob"]).date() if tm_rec and tm_rec["dob"] else None
            player = Player(
                full_name=row.full_name, normalized_name=row.norm,
                date_of_birth=dob, birth_year=int(row.birth_year),
                nationality=(tm_rec["nationality"] if tm_rec else row.nationality),
                primary_position=(tm_rec["position"] if tm_rec else row.position),
                foot=(tm_rec["foot"] if tm_rec else None),
                height_cm=(int(tm_rec["height"]) if tm_rec and pd.notna(tm_rec["height"]) else None),
            )
            session.add(player)
            session.flush()
            session.add(EntityXref(player_id=player.id, source="fbref", source_key=key,
                                   match_method="pool", confidence=1.0))
            if tm_rec:
                session.add(EntityXref(player_id=player.id, source="transfermarkt",
                                       source_id=str(tm_rec["player_id"]), match_method=method,
                                       confidence=1.0 if method in ("exact", "override") else 0.9))
            canon.append({"norm": row.norm, "teams": row.teams, "player": player})

        # --- Understat ---
        canon_norms = [c["norm"] for c in canon]
        by_norm: dict[str, list[int]] = {}
        for i, c in enumerate(canon):
            by_norm.setdefault(c["norm"], []).append(i)
        us_override = {o["key"]: o["target"] for o in overrides["understat"]}  # us_id -> "name|by"
        canon_by_key = {f"{c['norm']}|{c['player'].birth_year}": c for c in canon}
        us_s = {"exact": 0, "fuzzy": 0, "override": 0, "ambiguous": 0, "none": 0}

        for row in us.itertuples(index=False):
            uid = str(int(row.player_id))
            target = None
            # override
            if uid in us_override and us_override[uid] in canon_by_key:
                target = canon_by_key[us_override[uid]]; us_s["override"] += 1
            # exact name (disambiguate same-name namesakes by club overlap)
            if target is None:
                idxs = by_norm.get(row.norm, [])
                if len(idxs) == 1:
                    target = canon[idxs[0]]; us_s["exact"] += 1
                elif len(idxs) > 1:
                    overlap = [canon[i] for i in idxs if _teams_overlap(row.teams, canon[i]["teams"])]
                    if len(overlap) == 1:
                        target = overlap[0]; us_s["fuzzy"] += 1
                    else:
                        us_s["ambiguous"] += 1
                        flags.append({"type": "us_exact_ambiguous", "key": uid,
                                      "name": row.full_name,
                                      "detail": f"{len(idxs)} same-name, {len(overlap)} club-overlap"})
            # fuzzy name + club overlap (no exact name hit)
            if target is None and row.norm not in by_norm:
                hits = process.extract(row.norm, canon_norms, scorer=fuzz.token_set_ratio,
                                       limit=6, score_cutoff=US_NAME_THRESHOLD)
                cand = [canon[i] for _, _, i in hits if _teams_overlap(row.teams, canon[i]["teams"])]
                uniq = {id(c["player"]): c for c in cand}
                if len(uniq) == 1:
                    target = next(iter(uniq.values())); us_s["fuzzy"] += 1
                elif len(uniq) > 1:
                    us_s["ambiguous"] += 1
                    flags.append({"type": "us_fuzzy_ambiguous", "key": uid,
                                  "name": row.full_name, "detail": f"{len(uniq)} club-overlap canon"})
                else:
                    us_s["none"] += 1
                    flags.append({"type": "us_no_match", "key": uid, "name": row.full_name,
                                  "detail": ""})
            if target is not None:
                session.add(EntityXref(player_id=target["player"].id, source="understat",
                                       source_id=uid, match_method="resolved", confidence=0.9))

        session.commit()
    finally:
        session.close()

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(flags).to_csv(REPORT, index=False)
    n = len(fb)
    tm_linked = s["tm_exact"] + s["tm_fuzzy"] + s["tm_override"]
    log.info("=== ENTITY RESOLUTION ===")
    log.info("canonical players: %d", n)
    log.info("TM linked: %d (%.1f%%) [exact=%d fuzzy=%d override=%d] | none=%d | AMBIGUOUS=%d",
             tm_linked, 100 * tm_linked / n, s["tm_exact"], s["tm_fuzzy"], s["tm_override"],
             s["tm_none"], s["tm_ambiguous"])
    us_linked = us_s["exact"] + us_s["fuzzy"] + us_s["override"]
    log.info("US linked: %d (%.1f%%) [exact=%d fuzzy=%d override=%d] | none=%d | AMBIGUOUS=%d",
             us_linked, 100 * us_linked / len(us), us_s["exact"], us_s["fuzzy"], us_s["override"],
             us_s["none"], us_s["ambiguous"])
    log.info("flags: %d -> %s", len(flags), REPORT)
