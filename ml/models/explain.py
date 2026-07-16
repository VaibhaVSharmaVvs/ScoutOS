"""Driving factors for each model — structured, LLM-ready explanations.

The LLM layer (Phase 6) explains predictions; it must never compute them. This
module returns WHY each model predicted what it did, in a consistent shape:
  {"prediction": ..., "drivers": [{"feature","label","value","effect","weight"}]}

Coverage:
  - value / potential : per-prediction SHAP contributions (signed: pushes value
                        up/down), top-N.
  - similarity        : the style traits two players most share (embedding-space).
  - position          : class probabilities already ARE the drivers (see
                        position.predict_positions -> primary/secondary/playable).
  - club_fit          : the tactical/squad/financial/age sub-scores already ARE
                        the decomposition (see ClubFitEngine.score).
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd

# human-readable labels for feature names (fallback: prettified name)
LABELS = {
    "club_elo": "club strength", "age": "age", "minutes": "minutes played",
    "goals_p90": "goals/90", "assists_p90": "assists/90", "xg_p90": "xG/90",
    "xa_p90": "xA/90", "xg_chain_p90": "xG chain/90", "sca_p90": "shot-creating actions/90",
    "gca_p90": "goal-creating actions/90", "pass_prog_p90": "progressive passes/90",
    "carries_prog_p90": "progressive carries/90", "tackles_p90": "tackles/90",
    "interceptions_p90": "interceptions/90", "key_passes_p90": "key passes/90",
    "pass_cmp_pct": "pass completion %", "shots_p90": "shots/90",
    "take_ons_att_p90": "take-ons/90", "clearances_p90": "clearances/90",
    "league_strength": "league strength", "cur_value_log": "current value",
}


def _label(feat: str) -> str:
    return LABELS.get(feat, feat.replace("_p90", "/90").replace("_", " "))


def _tree_drivers(booster_path, meta_path, feature_row: dict, top_n=6):
    """Prediction + top signed SHAP contributions for a LightGBM booster."""
    import lightgbm as lgb
    import shap

    booster = lgb.Booster(model_file=str(booster_path))
    meta = joblib.load(meta_path)
    cols = meta["feature_cols"]
    cats = meta.get("categoricals", [])
    X = pd.DataFrame([feature_row]).reindex(columns=cols)
    for c in cols:
        X[c] = X[c].astype("category") if c in cats else pd.to_numeric(X[c], errors="coerce")
    pred_log = float(booster.predict(X)[0])
    contrib = shap.TreeExplainer(booster).shap_values(X)[0]  # log-space contributions
    order = np.argsort(np.abs(contrib))[::-1][:top_n]
    drivers = [{"feature": cols[i], "label": _label(cols[i]), "value": feature_row.get(cols[i]),
                "effect": "increases" if contrib[i] >= 0 else "decreases",
                "weight": round(float(abs(contrib[i])), 3)} for i in order]
    return pred_log, drivers


def explain_value(feature_row: dict, top_n=6) -> dict:
    from ml.models.value import OUT
    pred_log, drivers = _tree_drivers(OUT / "model.txt", OUT / "meta.joblib", feature_row, top_n)
    return {"predicted_value_eur": round(max(float(np.expm1(pred_log)), 0)), "drivers": drivers}


def explain_potential(feature_row: dict, horizon=3, top_n=6) -> dict:
    from ml.models.potential import OUT
    pred_log, drivers = _tree_drivers(OUT / f"model_h{horizon}.txt", OUT / "meta.joblib",
                                      feature_row, top_n)
    return {"horizon_years": horizon,
            "predicted_value_eur": round(max(float(np.expm1(pred_log)), 0)), "drivers": drivers}


def explain_similarity(player_id: int, other_id: int, top_n=5) -> dict:
    """Style traits two players most share. Embedding dims aren't human-readable,
    so we report the standout STYLE features (z-scored per-90/rates) where BOTH
    players sit well above average — the traits that make them alike."""
    from app.db.session import get_engine
    from ml.features.scaler import load as load_scaler, transform

    _, names, _ = load_scaler("v1")
    feats = pd.read_sql(
        "select player_id, features from player_features where feature_set_version='v1'",
        get_engine())

    def _vec(pid):
        sub = feats[feats["player_id"] == pid]
        return None if sub.empty else transform(list(sub["features"]), "v1").mean(0)

    a, b = _vec(player_id), _vec(other_id)
    if a is None or b is None:
        return {"shared_traits": []}
    # dims where BOTH are clearly above average (z>0.4) -> shared strengths
    shared = sorted(((names[i], min(a[i], b[i])) for i in range(len(names))
                     if a[i] > 0.4 and b[i] > 0.4), key=lambda kv: kv[1], reverse=True)
    return {"shared_traits": [{"feature": f, "label": _label(f)} for f, _ in shared[:top_n]]}
