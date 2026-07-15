"""Market Value model (Phase 4.2): LightGBM regression on player_features.

Target: market_value_eur (log1p-transformed — values are heavily right-skewed).
Split: TIME-BASED (train on earlier seasons, validate on 2023-24, test on
2024-25) so we measure generalization to a future season, not random leakage.
Metrics: MAE / RMSE / MedAE (EUR) + R2 (log & EUR), vs a median baseline.
Explainability: LightGBM gain importance + SHAP top features.

    python -m ml.models.value            # train, evaluate, persist
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from etl.load.db import log
from ml.models.dataset import feature_columns, load_features, time_split

MODEL_VERSION = "value_v1"
FEATURE_SET_VERSION = "v1"
MIN_MINUTES = 300          # drop tiny samples (noisy per-90) from training
TEST_YEAR, VAL_YEAR = 2024, 2023  # 2024-25 test, 2023-24 val
CATEGORICALS = ["position_group", "league_id"]
CONTEXT = ["age", "minutes", "club_elo", "league_strength"]
OUT = Path("ml/artifacts/models") / MODEL_VERSION


def _prep():
    df = load_features(FEATURE_SET_VERSION)
    df = df[df["market_value_eur"].notna() & (df["minutes"] >= MIN_MINUTES)].copy()
    feat_cols = feature_columns(df) + CONTEXT + CATEGORICALS
    for c in CONTEXT:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in CATEGORICALS:
        df[c] = df[c].astype("category")
    df["y_log"] = np.log1p(df["market_value_eur"].astype(float))
    return df, feat_cols


def train() -> dict:
    df, feat_cols = _prep()
    train_df, val_df, test_df = time_split(df, TEST_YEAR, VAL_YEAR)
    log.info("value model: train=%d val=%d test=%d (features=%d)",
             len(train_df), len(val_df), len(test_df), len(feat_cols))

    Xtr, ytr = train_df[feat_cols], train_df["y_log"]
    Xval, yval = val_df[feat_cols], val_df["y_log"]
    Xte = test_df[feat_cols]
    y_true = test_df["market_value_eur"].astype(float).to_numpy()

    model = lgb.LGBMRegressor(
        n_estimators=2000, learning_rate=0.02, num_leaves=63,
        subsample=0.8, colsample_bytree=0.8, min_child_samples=30,
        random_state=42, n_jobs=-1, verbosity=-1,
    )
    model.fit(Xtr, ytr, eval_set=[(Xval, yval)], eval_metric="l2",
              categorical_feature=CATEGORICALS,
              callbacks=[lgb.early_stopping(100), lgb.log_evaluation(0)])

    y_pred = np.expm1(model.predict(Xte))
    y_pred = np.clip(y_pred, 0, None)

    baseline = np.expm1(ytr.median())  # predict train median value for everyone
    metrics = {
        "mae_eur": round(float(mean_absolute_error(y_true, y_pred))),
        "rmse_eur": round(float(np.sqrt(mean_squared_error(y_true, y_pred)))),
        "medae_eur": round(float(np.median(np.abs(y_true - y_pred)))),
        "r2_eur": round(float(r2_score(y_true, y_pred)), 4),
        "r2_log": round(float(r2_score(test_df["y_log"], model.predict(Xte))), 4),
        "baseline_mae_eur": round(float(mean_absolute_error(y_true, np.full_like(y_true, baseline)))),
        "best_iteration": int(model.best_iteration_ or model.n_estimators),
        "n_train": len(train_df), "n_test": len(test_df),
        "test_season": int(TEST_YEAR),
    }

    # importance
    gain = pd.Series(model.booster_.feature_importance("gain"), index=feat_cols)
    top_gain = gain.sort_values(ascending=False).head(15)
    try:
        import shap
        expl = shap.TreeExplainer(model)
        sample = Xte.sample(min(500, len(Xte)), random_state=0)
        sv = expl.shap_values(sample)
        shap_imp = pd.Series(np.abs(sv).mean(0), index=feat_cols).sort_values(ascending=False)
        top_shap = shap_imp.head(15).round(4).to_dict()
    except Exception as exc:  # noqa: BLE001
        log.warning("SHAP skipped: %s", exc)
        top_shap = {}

    OUT.mkdir(parents=True, exist_ok=True)
    model.booster_.save_model(str(OUT / "model.txt"))
    joblib.dump({"feature_cols": feat_cols, "categoricals": CATEGORICALS,
                 "feature_set_version": FEATURE_SET_VERSION, "log_target": True},
                OUT / "meta.joblib")
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (OUT / "importance.json").write_text(json.dumps(
        {"gain_top": top_gain.round(1).to_dict(), "shap_top": top_shap}, indent=2))

    log.info("=== VALUE MODEL (test %d-%d) ===", TEST_YEAR, TEST_YEAR + 1)
    log.info("MAE  EUR %s (baseline %s)", f"{metrics['mae_eur']:,}", f"{metrics['baseline_mae_eur']:,}")
    log.info("RMSE EUR %s | MedAE EUR %s", f"{metrics['rmse_eur']:,}", f"{metrics['medae_eur']:,}")
    log.info("R2 (EUR) %.3f | R2 (log) %.3f | best_iter %d",
             metrics["r2_eur"], metrics["r2_log"], metrics["best_iteration"])
    log.info("top gain features: %s", list(top_gain.head(8).index))
    log.info("saved -> %s", OUT)
    return metrics


if __name__ == "__main__":
    train()
