"""Enrich canonical players with Transfermarkt youth-value signals.

Non-destructive UPDATE (no re-resolution): joins the TM entity_xref to the raw
players.csv and sets international caps/goals, contract expiration, and
highest-ever market value — the "potential premium" signals that current stats
miss for young players (Phase 4 value_v2). Run:  python -m etl.load --step enrich
"""

from __future__ import annotations

import pandas as pd

from app.db.models import EntityXref, Player
from etl.load.db import SessionLocal, log

TM_PLAYERS = "data/raw/transfermarkt/players.csv"


def run() -> None:
    tm = pd.read_csv(TM_PLAYERS)
    tm["contract"] = pd.to_datetime(tm["contract_expiration_date"], errors="coerce").dt.date
    tm = tm.set_index("player_id")

    session = SessionLocal()
    try:
        xrefs = session.query(EntityXref.player_id, EntityXref.source_id).filter(
            EntityXref.source == "transfermarkt").all()
        updates, n = [], 0
        for player_id, source_id in xrefs:
            try:
                r = tm.loc[int(source_id)]
            except (KeyError, ValueError):
                continue
            updates.append({
                "id": player_id,
                "international_caps": int(r["international_caps"]) if pd.notna(r["international_caps"]) else None,
                "international_goals": int(r["international_goals"]) if pd.notna(r["international_goals"]) else None,
                "contract_expiration": r["contract"] if pd.notna(r["contract"]) else None,
                "highest_market_value_eur": int(r["highest_market_value_in_eur"]) if pd.notna(r["highest_market_value_in_eur"]) else None,
            })
            n += 1
        session.bulk_update_mappings(Player, updates)
        session.commit()
        capped = sum(1 for u in updates if u["international_caps"] is not None)
        contracts = sum(1 for u in updates if u["contract_expiration"] is not None)
        hmv = sum(1 for u in updates if u["highest_market_value_eur"] is not None)
        log.info("enriched %d players | intl_caps=%d, contract=%d, highest_mv=%d", n, capped, contracts, hmv)
    finally:
        session.close()
