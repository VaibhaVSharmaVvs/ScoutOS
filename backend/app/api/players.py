"""Player search and profile endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas import PlayerHit, PlayerProfile, SeasonStat

router = APIRouter(prefix="/players", tags=["players"])

_SEARCH_SQL = text(
    "select id, full_name, primary_position, nationality, birth_year, foot "
    "from players "
    "where full_name ilike :like or normalized_name ilike :like "
    "order by (normalized_name ilike :prefix) desc, length(full_name) asc "
    "limit :limit"
)

_BIO_SQL = text(
    "select id, full_name, primary_position, nationality, date_of_birth, foot, "
    "height_cm, highest_market_value_eur, contract_expiration, international_caps "
    "from players where id = :pid"
)

_CURRENT_VALUE_SQL = text(
    "select value_eur from market_values where player_id = :pid "
    "order by as_of desc limit 1"
)

# one row per season = the source with the most minutes that season
_SEASONS_SQL = text(
    "select distinct on (s.start_year) s.label as season, c.name as club, "
    "l.name as league, pss.minutes, pss.matches, pss.goals, pss.assists, "
    "pss.xg, pss.xa "
    "from player_season_stats pss join seasons s on s.id = pss.season_id "
    "left join clubs c on c.id = pss.club_id "
    "left join leagues l on l.id = pss.league_id "
    "where pss.player_id = :pid "
    "order by s.start_year desc, pss.minutes desc nulls last"
)


@router.get("/search", response_model=list[PlayerHit])
def search_players(
    q: str = Query(..., min_length=2, description="Name fragment"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
) -> list[PlayerHit]:
    rows = db.execute(
        _SEARCH_SQL, {"like": f"%{q}%", "prefix": f"{q}%", "limit": limit}
    ).mappings().all()
    return [PlayerHit(**r) for r in rows]


@router.get("/{player_id}", response_model=PlayerProfile)
def player_profile(player_id: int, db: Session = Depends(get_session)) -> PlayerProfile:
    bio = db.execute(_BIO_SQL, {"pid": player_id}).mappings().first()
    if bio is None:
        raise HTTPException(status_code=404, detail="player not found")
    cur = db.execute(_CURRENT_VALUE_SQL, {"pid": player_id}).scalar()
    seasons = db.execute(_SEASONS_SQL, {"pid": player_id}).mappings().all()

    return PlayerProfile(
        id=bio["id"],
        full_name=bio["full_name"],
        primary_position=bio["primary_position"],
        nationality=bio["nationality"],
        date_of_birth=str(bio["date_of_birth"]) if bio["date_of_birth"] else None,
        foot=bio["foot"],
        height_cm=bio["height_cm"],
        market_value_eur=float(cur) if cur is not None else None,
        highest_market_value_eur=(
            float(bio["highest_market_value_eur"])
            if bio["highest_market_value_eur"] is not None else None
        ),
        contract_expiration=(
            str(bio["contract_expiration"]) if bio["contract_expiration"] else None
        ),
        international_caps=bio["international_caps"],
        seasons=[SeasonStat(**s) for s in seasons],
    )
