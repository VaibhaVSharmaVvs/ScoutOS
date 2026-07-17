"""Potential Growth model (Phase 4.4): LightGBM value trajectories.

For each player-season we predict the player's market value +1 / +3 / +5 years
out, using current stats + age + current value. "Potential" = predicting CHANGE,
so every horizon is scored against a naive FLAT baseline (assume value is
unchanged) and on growth-direction accuracy. Targets come from the long
Transfermarkt valuation history (merge_asof to the valuation nearest the future
date). Time-based split (test = latest feature-season with that horizon's target)
avoids leakage.

    python -m ml.models.potential        # train all horizons, evaluate, persist
"""

from __future__ import annotations

import json

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score

from app.db.session import get_engine
from etl.load.db import log
from ml._paths import MODELS_DIR
from ml.models.dataset import feature_columns, load_features

MODEL_VERSION = "potential_v1"
FEATURE_SET_VERSION = "v1"
MIN_MINUTES = 450
HORIZONS = [1, 3, 5]
TOLERANCE_DAYS = 300
CATEGORICALS = ["position_group", "league_id"]
CONTEXT = ["age", "minutes", "club_elo", "league_strength", "cur_value_log"]
OUT = MODELS_DIR / MODEL_VERSION


def _prep():
    df = load_features(FEATURE_SET_VERSION)
    df = df[df["market_value_eur"].notna() & (df["minutes"] >= MIN_MINUTES)].copy()
    df["cur_value"] = df["market_value_eur"].astype(float)
    df["cur_value_log"] = np.log1p(df["cur_value"])
    df["ref_date"] = pd.to_datetime(df["start_year"].astype(int).add(1).astype(str) + "-06-01")

    mv = pd.read_sql("select player_id, as_of, value_eur from market_values", get_engine())
    mv["as_of"] = pd.to_datetime(mv["as_of"])
    mv["value_eur"] = pd.to_numeric(mv["value_eur"], errors="coerce")
    mv = mv.dropna(subset=["as_of", "value_eur"]).sort_values("as_of")

    for h in HORIZONS:
        tgt = df[["player_id", "ref_date"]].copy()
        tgt["target_date"] = tgt["ref_date"] + pd.DateOffset(years=h)
        tgt = tgt.sort_values("target_date")
        merged = pd.merge_asof(
            tgt, mv, left_on="target_date", right_on="as_of", by="player_id",
            direction="nearest", tolerance=pd.Timedelta(f"{TOLERANCE_DAYS}D"),
        )
        df[f"future_{h}"] = merged.set_index(tgt.index)["value_eur"]

    feat_cols = feature_columns(df) + CONTEXT + CATEGORICALS
    for c in CONTEXT:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in CATEGORICALS:
        df[c] = df[c].astype("category")
    return df, feat_cols


def _train_horizon(df, feat_cols, h) -> dict:
    d = df[df[f"future_{h}"].notna()].copy()
    d["y_log"] = np.log1p(d[f"future_{h}"].astype(float))
    test_year = int(d["start_year"].max())
    train = d[d["start_year"] < test_year]
    test = d[d["start_year"] == test_year]
    if len(train) < 200 or len(test) < 30:
        log.warning("+%dyr: insufficient data (train=%d test=%d) — skipping", h, len(train), len(test))
        return {"horizon": h, "skipped": True, "n_train": len(train), "n_test": len(test)}

    model = lgb.LGBMRegressor(n_estimators=1500, learning_rate=0.02, num_leaves=48,
                              subsample=0.8, colsample_bytree=0.8, min_child_samples=30,
                              random_state=42, n_jobs=-1, verbosity=-1)
    model.fit(train[feat_cols], train["y_log"], categorical_feature=CATEGORICALS)

    pred = np.clip(np.expm1(model.predict(test[feat_cols])), 0, None)
    actual = test[f"future_{h}"].astype(float).to_numpy()
    cur = test["cur_value"].to_numpy()
    flat_mae = mean_absolute_error(actual, cur)  # naive: value unchanged
    dir_ok = np.mean(np.sign(pred - cur) == np.sign(actual - cur))

    OUT.mkdir(parents=True, exist_ok=True)
    model.booster_.save_model(str(OUT / f"model_h{h}.txt"))
    m = {
        "horizon": h, "test_season": test_year, "n_train": len(train), "n_test": len(test),
        "mae_eur": round(float(mean_absolute_error(actual, pred))),
        "flat_baseline_mae_eur": round(float(flat_mae)),
        "r2_eur": round(float(r2_score(actual, pred)), 4),
        "r2_log": round(float(r2_score(test["y_log"], model.predict(test[feat_cols]))), 4),
        "growth_direction_acc": round(float(dir_ok), 4),
        "top_features": list(pd.Series(model.booster_.feature_importance("gain"),
                                       index=feat_cols).sort_values(ascending=False).head(8).index),
    }
    log.info("+%dyr | MAE €%s (flat €%s) | R2 %.3f | dir-acc %.3f | n_test=%d",
             h, f"{m['mae_eur']:,}", f"{m['flat_baseline_mae_eur']:,}",
             m["r2_eur"], m["growth_direction_acc"], len(test))
    return m


def train() -> dict:
    df, feat_cols = _prep()
    log.info("potential model: %d player-seasons, %d features, horizons %s",
             len(df), len(feat_cols), HORIZONS)
    results = {f"h{h}": _train_horizon(df, feat_cols, h) for h in HORIZONS}
    OUT.mkdir(parents=True, exist_ok=True)
    joblib.dump({"feature_cols": feat_cols, "categoricals": CATEGORICALS,
                 "horizons": HORIZONS, "feature_set_version": FEATURE_SET_VERSION,
                 "log_target": True}, OUT / "meta.joblib")
    (OUT / "metrics.json").write_text(json.dumps(results, indent=2))
    log.info("saved -> %s", OUT)
    return results


if __name__ == "__main__":
    train()
