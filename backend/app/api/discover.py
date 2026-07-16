"""Discovery endpoints: similar players and club fit (Club Finder)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query

from app.ml.registry import club_fit_engine
from app.schemas import (
    ClubFit,
    ClubFitResponse,
    SimilarPlayer,
    SimilarResponse,
)

router = APIRouter(prefix="/players/{player_id}", tags=["discovery"])


@router.get("/similar", response_model=SimilarResponse)
def similar_players(
    player_id: int = Path(..., ge=1),
    k: int = Query(10, ge=1, le=50),
    mode: str = Query("current", pattern="^(current|career)$"),
    same_position: bool = Query(False),
    explain: bool = Query(True, description="Attach shared style traits per neighbour"),
) -> SimilarResponse:
    from ml.models.similarity import find_similar

    hits = find_similar(player_id, k=k, mode=mode, same_position=same_position)
    if not hits:
        raise HTTPException(status_code=404, detail="player not in similarity index")

    traits_by_pid: dict[int, list] = {}
    if explain:
        from ml.models.explain import _shared_traits, _style_vectors

        names, vecs = _style_vectors("v1")
        q = vecs.get(player_id)
        if q is not None:
            for h in hits:
                other = vecs.get(h["player_id"])
                if other is not None:
                    traits_by_pid[h["player_id"]] = _shared_traits(q, other, names)

    results = [
        SimilarPlayer(
            player_id=h["player_id"], player=h["player"],
            position_group=h.get("position_group"), similarity=h["similarity"],
            season=h.get("season"), shared_traits=traits_by_pid.get(h["player_id"]),
        )
        for h in hits
    ]
    return SimilarResponse(player_id=player_id, mode=mode, results=results)


@router.get("/club-fit", response_model=ClubFitResponse)
def club_fit(
    player_id: int = Path(..., ge=1),
    top: int = Query(10, ge=1, le=50),
) -> ClubFitResponse:
    engine = club_fit_engine()
    if player_id not in engine.players.index:
        raise HTTPException(status_code=404, detail="player has no current-season profile")
    df = engine.rank_clubs(player_id, top=top)
    if df.empty:
        raise HTTPException(status_code=404, detail="no club fits available")
    name_to_id = {v: k for k, v in engine.club_name.items()}
    results = [
        ClubFit(
            club=r["club"], club_id=name_to_id.get(r["club"]),
            tactical_fit=r["tactical_fit"], squad_fit=r["squad_fit"],
            financial_fit=r["financial_fit"], age_fit=r["age_fit"],
            overall_fit=r["overall_fit"],
        )
        for _, r in df.iterrows()
    ]
    return ClubFitResponse(player_id=player_id, player=df.iloc[0]["player"], results=results)


@router.get("/club-fit/{club_id}", response_model=ClubFit)
def club_fit_single(
    player_id: int = Path(..., ge=1),
    club_id: int = Path(..., ge=1),
) -> ClubFit:
    engine = club_fit_engine()
    res = engine.score(player_id, club_id)
    if res is None:
        raise HTTPException(status_code=404, detail="player or club has no current-season profile")
    return ClubFit(
        club=res["club"], club_id=club_id, tactical_fit=res["tactical_fit"],
        squad_fit=res["squad_fit"], financial_fit=res["financial_fit"],
        age_fit=res["age_fit"], overall_fit=res["overall_fit"],
    )
