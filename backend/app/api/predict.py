"""Prediction endpoints: market value, potential, position.

Every prediction returns the driving factors from ml.models.explain so the
Phase 6 LLM layer can narrate the "why" without recomputing anything.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query

from app.ml.features import latest_feature_row, position_frame
from app.ml.registry import position_models
from app.schemas import PositionPrediction, PotentialPrediction, ValuePrediction

router = APIRouter(prefix="/players/{player_id}", tags=["predictions"])

POTENTIAL_HORIZONS = (1, 3, 5)


def _require_features(player_id: int) -> dict:
    row = latest_feature_row(player_id)
    if row is None:
        raise HTTPException(status_code=404, detail="no feature data for this player")
    return row


@router.get("/predict/value", response_model=ValuePrediction)
def predict_value(player_id: int = Path(..., ge=1)) -> ValuePrediction:
    from ml.models.explain import explain_value

    row = _require_features(player_id)
    res = explain_value(row)
    return ValuePrediction(
        player_id=player_id, season=row["season"],
        predicted_value_eur=res["predicted_value_eur"],
        actual_value_eur=row.get("market_value_eur"),
        drivers=res["drivers"],
    )


@router.get("/predict/potential", response_model=PotentialPrediction)
def predict_potential(
    player_id: int = Path(..., ge=1),
    horizon: int = Query(3, description="Years ahead (1, 3, or 5)"),
) -> PotentialPrediction:
    from ml.models.explain import explain_potential

    if horizon not in POTENTIAL_HORIZONS:
        raise HTTPException(status_code=400, detail=f"horizon must be one of {POTENTIAL_HORIZONS}")
    row = _require_features(player_id)
    if row.get("cur_value_log") is None:
        raise HTTPException(status_code=422,
                            detail="no current market value — cannot project growth")
    res = explain_potential(row, horizon=horizon)
    return PotentialPrediction(
        player_id=player_id, season=row["season"], horizon_years=horizon,
        current_value_eur=row.get("market_value_eur"),
        predicted_value_eur=res["predicted_value_eur"], drivers=res["drivers"],
    )


@router.get("/predict/position", response_model=PositionPrediction)
def predict_position(player_id: int = Path(..., ge=1)) -> PositionPrediction:
    from ml.models.position import predict_positions

    row = _require_features(player_id)
    models = position_models()
    role_model, role_meta = models["role"]
    role = predict_positions(role_model, role_meta, position_frame(row, role_meta))[0]

    side_aware = None
    if row.get("foot"):  # foot known -> refine Left/Right
        side_model, side_meta = models["side"]
        side = predict_positions(side_model, side_meta, position_frame(row, side_meta))[0]
        side_aware = {"primary": side["primary"], "secondary": side["secondary"],
                      "foot": row["foot"], "probs": side["probs"]}

    return PositionPrediction(
        player_id=player_id, season=row["season"], primary=role["primary"],
        secondary=role["secondary"], playable=role["playable"], probs=role["probs"],
        side_aware=side_aware,
    )
