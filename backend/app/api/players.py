"""Player search and profile endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.ml.features import latest_feature_row
from app.schemas import (
    MarketValuePoint,
    PlayerHit,
    PlayerProfile,
    RadarMetric,
    RadarResponse,
    SeasonStat,
)

router = APIRouter(prefix="/players", tags=["players"])

# Position-specific radar axes — measuring a striker and a keeper on the same
# metrics is meaningless. Each set is (per-90 feature, display label). Percentiles
# are already computed per position group, so axes read "vs peers in this role".
RADAR_SETS = {
    "FWD": ("Attacking", [
        ("goals_p90", "Goals"), ("np_xg_p90", "Non-pen xG"), ("shots_p90", "Shots"),
        ("sca_p90", "Shot creation"), ("take_ons_succ_p90", "Dribbles"),
        ("xag_p90", "xA"), ("key_passes_p90", "Key passes"), ("aerials_won_p90", "Aerials won"),
    ]),
    "MID": ("Two-way", [
        ("pass_prog_p90", "Prog. passes"), ("key_passes_p90", "Key passes"),
        ("xag_p90", "xA"), ("sca_p90", "Shot creation"),
        ("carries_prog_p90", "Prog. carries"), ("tackles_p90", "Tackles"),
        ("interceptions_p90", "Interceptions"), ("touches_p90", "Touches"),
    ]),
    "DEF": ("Defensive", [
        ("tackles_p90", "Tackles"), ("interceptions_p90", "Interceptions"),
        ("clearances_p90", "Clearances"), ("blocks_p90", "Blocks"),
        ("aerials_won_p90", "Aerials won"), ("recoveries_p90", "Recoveries"),
        ("tkl_plus_int_p90", "Tkl+Int"), ("pass_prog_p90", "Prog. passes"),
    ]),
    "GK": ("Distribution & sweeping", [
        ("pass_cmp_p90", "Passes done"), ("pass_att_p90", "Passes tried"),
        ("pass_prog_p90", "Prog. passes"), ("prog_pass_dist_p90", "Pass distance"),
        ("pass_final_third_p90", "Final-3rd passes"), ("touches_p90", "Touches"),
        ("recoveries_p90", "Recoveries"), ("clearances_p90", "Clearances"),
    ]),
}
GK_NOTE = ("Shot-stopping data (saves, PSxG, clean sheets) isn't in our dataset — "
           "this profiles distribution and sweeping only.")

_SEARCH_SQL = text(
    "select p.id, p.full_name, p.primary_position, p.nationality, p.birth_year, p.foot, "
    "(select mv.value_eur from market_values mv where mv.player_id = p.id "
    " order by mv.as_of desc limit 1) as market_value_eur "
    "from players p "
    "where p.full_name ilike :like or p.normalized_name ilike :like "
    "order by (p.normalized_name ilike :prefix) desc, length(p.full_name) asc "
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


@router.get("/{player_id}/market-values", response_model=list[MarketValuePoint])
def player_market_values(
    player_id: int, db: Session = Depends(get_session)
) -> list[MarketValuePoint]:
    """Chronological market-value history (for the profile value chart)."""
    rows = db.execute(text(
        "select as_of, value_eur from market_values "
        "where player_id = :pid and value_eur is not null order by as_of"),
        {"pid": player_id}).mappings().all()
    return [MarketValuePoint(as_of=str(r["as_of"]), value_eur=float(r["value_eur"])) for r in rows]


@router.get("/{player_id}/radar", response_model=RadarResponse)
def player_radar(player_id: int) -> RadarResponse:
    """Position-appropriate percentile profile (radar axes) + strengths/weaknesses.

    Axes differ by role (attacking for forwards, defensive for defenders, a
    two-way mix for midfielders, distribution for keepers). Percentiles are vs
    same-position peers and map straight onto a fixed 0-100 radar scale.
    """
    row = latest_feature_row(player_id)
    if row is None:
        raise HTTPException(status_code=404, detail="no feature data for this player")

    pos = row.get("position_group") or "MID"
    focus, axes = RADAR_SETS.get(pos, RADAR_SETS["MID"])
    metrics: list[RadarMetric] = []
    for feat, label in axes:
        pct = row.get(f"{feat}_pct_pos")
        if pct is None:
            continue
        per90 = row.get(feat)
        metrics.append(RadarMetric(
            metric=feat, label=label, percentile=round(float(pct), 3),
            per90=None if per90 is None else round(float(per90), 2),
        ))
    ranked = sorted(metrics, key=lambda m: m.percentile, reverse=True)
    return RadarResponse(
        player_id=player_id, season=row["season"], position_group=pos, focus=focus,
        metrics=metrics,
        strengths=[m.label for m in ranked[:3] if m.percentile >= 0.6],
        weaknesses=[m.label for m in ranked[-3:] if m.percentile <= 0.4][::-1],
        note=GK_NOTE if pos == "GK" else None,
    )


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
