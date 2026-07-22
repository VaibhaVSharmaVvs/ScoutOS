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

from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

# Human scout-facing labels for every feature (no raw "np xg/90"). Used by the
# driver lists AND the similar-player trait chips.
LABELS = {
    # context
    "club_elo": "club pedigree", "age": "age", "minutes": "minutes played",
    "league_strength": "league strength", "cur_value_log": "current value",
    # attacking
    "goals_p90": "goals", "assists_p90": "assists", "shots_p90": "shots",
    "sot_p90": "shots on target", "xg_p90": "expected goals",
    "np_xg_p90": "non-penalty xG", "npxg_p90": "non-penalty xG",
    "xa_p90": "expected assists", "xag_p90": "expected assists",
    "np_g_per_shot": "finishing (goals/shot)", "shot_accuracy": "shot accuracy",
    # creation
    "sca_p90": "shot-creating actions", "gca_p90": "goal-creating actions",
    "key_passes_p90": "key passes", "ppa_p90": "passes into the box",
    "xg_chain_p90": "attacking involvement", "xg_buildup_p90": "buildup involvement",
    # passing
    "pass_cmp_p90": "passes completed", "pass_att_p90": "passes attempted",
    "pass_cmp_pct": "pass completion %", "pass_prog_p90": "progressive passes",
    "prog_pass_dist_p90": "passing distance", "pass_final_third_p90": "final-third passes",
    "prog_rec_p90": "progressive passes received",
    # carrying / dribbling
    "carries_p90": "carries", "carries_prog_p90": "progressive carries",
    "carries_prog_dist_p90": "carry distance", "touches_p90": "touches",
    "take_ons_att_p90": "take-ons attempted", "take_ons_succ_p90": "successful take-ons",
    "take_on_pct": "take-on success %",
    # defending
    "tackles_p90": "tackles", "tackles_won_p90": "tackles won",
    "interceptions_p90": "interceptions", "tkl_plus_int_p90": "tackles + interceptions",
    "clearances_p90": "clearances", "blocks_p90": "blocks",
    "recoveries_p90": "ball recoveries", "dribblers_challenged_p90": "dribblers challenged",
    # aerial / discipline
    "aerials_won_p90": "aerial duels won", "aerials_lost_p90": "aerial duels lost",
    "aerial_win_pct": "aerial win %", "fouls_p90": "fouls committed",
    "fouled_p90": "fouls won",
}


def _label(feat: str) -> str:
    return LABELS.get(feat, feat.replace("_p90", "").replace("_", " "))


@lru_cache(maxsize=8)
def _booster_and_explainer(booster_path: str):
    """Load a LightGBM booster + its SHAP explainer once (cached).

    Loading the booster from disk and constructing the TreeExplainer on every
    request cost ~seconds each; caching makes repeat predictions instant (fixes
    the cold value/potential latency)."""
    import lightgbm as lgb
    import shap

    booster = lgb.Booster(model_file=booster_path)
    return booster, shap.TreeExplainer(booster)


def _tree_drivers(booster_path, meta_path, feature_row: dict, top_n=6):
    """Prediction + top signed SHAP contributions for a LightGBM booster."""
    booster, explainer = _booster_and_explainer(str(booster_path))
    meta = joblib.load(meta_path)
    cols = meta["feature_cols"]
    cats = meta.get("categoricals", [])
    X = pd.DataFrame([feature_row]).reindex(columns=cols)
    for c in cols:
        X[c] = X[c].astype("category") if c in cats else pd.to_numeric(X[c], errors="coerce")
    pred_log = float(booster.predict(X)[0])
    contrib = explainer.shap_values(X)[0]  # log-space contributions
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


@lru_cache(maxsize=1)
def _style_vectors(version: str = "v1"):
    """Per-player z-scored style vector (mean across their seasons), cached.

    Returns (feature_names, {player_id: np.ndarray}). One scaler.transform over
    all rows, then averaged per player — cheap to reuse across many explanations.
    """
    from app.db.session import get_engine
    from ml.features.scaler import load as load_scaler, transform

    _, names, _ = load_scaler(version)
    feats = pd.read_sql(
        f"select player_id, features from player_features where feature_set_version='{version}'",
        get_engine()).reset_index(drop=True)
    mat = transform(list(feats["features"]), version)
    vecs = {int(pid): mat[list(idx)].mean(0)
            for pid, idx in feats.groupby("player_id").groups.items()}
    return names, vecs


def _shared_traits(a, b, names, top_n=5) -> list[dict]:
    """Style dims where BOTH players sit clearly above average (z>0.4).

    Deduped by human label — near-duplicate features (np_xg / npxg both read
    "non-penalty xG") shouldn't show twice."""
    shared = sorted(((names[i], min(a[i], b[i])) for i in range(len(names))
                     if a[i] > 0.4 and b[i] > 0.4), key=lambda kv: kv[1], reverse=True)
    out, seen = [], set()
    for f, _ in shared:
        label = _label(f)
        if label in seen:
            continue
        seen.add(label)
        out.append({"feature": f, "label": label})
        if len(out) >= top_n:
            break
    return out


def explain_similarity(player_id: int, other_id: int, top_n=5) -> dict:
    """Style traits two players most share. Embedding dims aren't human-readable,
    so we report the standout STYLE features (z-scored per-90/rates) where BOTH
    players sit well above average — the traits that make them alike."""
    names, vecs = _style_vectors("v1")
    a, b = vecs.get(player_id), vecs.get(other_id)
    if a is None or b is None:
        return {"shared_traits": []}
    return {"shared_traits": _shared_traits(a, b, names, top_n)}
