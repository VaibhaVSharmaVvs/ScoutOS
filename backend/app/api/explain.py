"""LLM explanation endpoints (Phase 6).

Narratives are grounded strictly in model outputs (the `grounding` field echoes
exactly what the LLM was given). With no ANTHROPIC_API_KEY the layer returns a
deterministic stub so the pipeline and frontend still work.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.llm import service
from app.schemas import ExplanationResponse

router = APIRouter(prefix="/players/{player_id}/explain", tags=["explain"])


@router.get("", response_model=ExplanationResponse)
def explain_player(
    player_id: int = Path(..., ge=1), db: Session = Depends(get_session)
) -> ExplanationResponse:
    """Scouting report: narrates the value/potential/position/similarity outputs."""
    res = service.explain_report(db, player_id)
    if res is None:
        raise HTTPException(status_code=404, detail="no model data for this player")
    return ExplanationResponse(**res)


@router.get("/club-fit/{club_id}", response_model=ExplanationResponse)
def explain_club_fit(
    player_id: int = Path(..., ge=1), club_id: int = Path(..., ge=1)
) -> ExplanationResponse:
    res = service.explain_club_fit(player_id, club_id)
    if res is None:
        raise HTTPException(status_code=404, detail="player or club has no current-season profile")
    return ExplanationResponse(**res)


@router.get("/comparison/{other_id}", response_model=ExplanationResponse)
def explain_comparison(
    player_id: int = Path(..., ge=1),
    other_id: int = Path(..., ge=1),
    db: Session = Depends(get_session),
) -> ExplanationResponse:
    res = service.explain_comparison(db, player_id, other_id)
    if res is None:
        raise HTTPException(status_code=404, detail="one or both players not found")
    return ExplanationResponse(**res)
