"""Analytics endpoints: squad analysis (club) and career simulation (player)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.ml.features import latest_feature_row
from app.schemas import (
    CareerPoint,
    CareerSimulation,
    ClubHit,
    PositionDepth,
    SquadAnalysis,
)

router = APIRouter(tags=["analytics"])

CURRENT_SEASON = "2024-25"
REGULAR_MINUTES = 900
CAREER_HORIZONS = (1, 3)  # +5yr not trained (too few valuation pairs)
POSITION_GROUPS = ("GK", "DEF", "MID", "FWD")

_SQUAD_SQL = text(
    "select pf.position_group, pf.age, pf.minutes, "
    "nullif(pf.market_value_eur,'NaN')::numeric as value "
    "from player_features pf join seasons s on s.id = pf.season_id "
    "where pf.feature_set_version='v1' and s.label=:season and pf.club_id=:cid"
)


@router.get("/clubs", response_model=list[ClubHit], tags=["clubs"])
def search_clubs(
    q: str = Query(..., min_length=2, description="Club name fragment"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
) -> list[ClubHit]:
    """Clubs that have a current-season squad profile (usable by squad-analysis)."""
    rows = db.execute(text(
        "select distinct c.id, c.name, c.country from clubs c "
        "join player_features pf on pf.club_id = c.id "
        "join seasons s on s.id = pf.season_id "
        "where s.label = :season and c.name ilike :like "
        "order by c.name limit :limit"),
        {"season": CURRENT_SEASON, "like": f"%{q}%", "limit": limit}).mappings().all()
    return [ClubHit(**r) for r in rows]


@router.get("/clubs/{club_id}/squad-analysis", response_model=SquadAnalysis)
def squad_analysis(
    club_id: int = Path(..., ge=1),
    db: Session = Depends(get_session),
) -> SquadAnalysis:
    club = db.execute(text("select name from clubs where id=:cid"), {"cid": club_id}).scalar()
    if club is None:
        raise HTTPException(status_code=404, detail="club not found")
    rows = db.execute(_SQUAD_SQL, {"season": CURRENT_SEASON, "cid": club_id}).mappings().all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"no {CURRENT_SEASON} squad data for this club")

    depth: list[PositionDepth] = []
    gaps: list[str] = []
    tot_val = 0.0
    for pg in POSITION_GROUPS:
        grp = [r for r in rows if r["position_group"] == pg]
        if not grp:
            gaps.append(pg)
            depth.append(PositionDepth(position_group=pg, squad_size=0, regulars=0))
            continue
        regulars = [r for r in grp if (r["minutes"] or 0) >= REGULAR_MINUTES]
        vals = [float(r["value"]) for r in grp if r["value"] is not None]
        mins = sum((r["minutes"] or 0) for r in grp) or 1
        avg_age = sum((r["age"] or 0) * (r["minutes"] or 0) for r in grp) / mins
        depth.append(PositionDepth(
            position_group=pg, squad_size=len(grp), regulars=len(regulars),
            avg_age=round(avg_age, 1) if avg_age else None,
            total_value_eur=sum(vals) if vals else None,
        ))
        tot_val += sum(vals)
        # a group with fewer than 2 regulars is thin depth
        if len(regulars) < 2:
            gaps.append(pg)

    all_mins = sum((r["minutes"] or 0) for r in rows) or 1
    squad_avg_age = sum((r["age"] or 0) * (r["minutes"] or 0) for r in rows) / all_mins
    return SquadAnalysis(
        club_id=club_id, club=club, season=CURRENT_SEASON, squad_size=len(rows),
        avg_age=round(squad_avg_age, 1) if squad_avg_age else None,
        total_value_eur=tot_val or None, depth=depth, gaps=gaps,
    )


@router.get("/players/{player_id}/career-simulation", response_model=CareerSimulation)
def career_simulation(
    player_id: int = Path(..., ge=1),
    db: Session = Depends(get_session),
) -> CareerSimulation:
    """Market-value trajectory projected by the Potential model (now, +1, +3yr).

    This is a value projection, not a guarantee — it extrapolates from the
    player's current stats/age/context, and the drivers explain each point.
    """
    from ml.models.explain import explain_potential

    row = latest_feature_row(player_id)
    if row is None:
        raise HTTPException(status_code=404, detail="no feature data for this player")
    name = db.execute(
        text("select full_name from players where id=:pid"), {"pid": player_id}
    ).scalar() or "Unknown"
    if row.get("cur_value_log") is None:
        raise HTTPException(status_code=422, detail="no current market value — cannot simulate")

    age = row.get("age")
    traj = [CareerPoint(label="current", horizon_years=0, age=age,
                        value_eur=row.get("market_value_eur"))]
    for h in CAREER_HORIZONS:
        res = explain_potential(row, horizon=h)
        traj.append(CareerPoint(
            label=f"+{h}yr", horizon_years=h,
            age=round(age + h, 1) if age is not None else None,
            value_eur=res["predicted_value_eur"], drivers=res["drivers"][:4],
        ))
    return CareerSimulation(
        player_id=player_id, player=name, season=row["season"], trajectory=traj,
        note="Value trajectory from the Potential model (+1/+3yr); +5yr omitted "
             "(insufficient training data). Projection, not a forecast guarantee.",
    )
