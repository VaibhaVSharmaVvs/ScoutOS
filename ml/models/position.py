"""Position model (Phase 4.3): CatBoost multiclass from a player's stat profile.

Two variants:
  - ROLE (side-agnostic): predicts role from per-90/rate style only. A stat
    profile can't tell left from right, so LB/RB->Full-Back, LW/RW->Winger.
  - SIDE (side-aware): adds `foot` (a non-stat attribute) to recover Left/Right
    (a left-footed full-back is likely a left-back). Keeps LB/RB/LW/RW distinct.

Split by PLAYER (position is season-stable) -> no leakage. Metrics: accuracy,
macro-F1, per-class F1, top confusions, vs majority baseline.

    python -m ml.models.position          # train both, evaluate, persist
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit

from app.db.session import get_engine
from etl.load.db import log
from ml.models.dataset import feature_columns, load_features

FEATURE_SET_VERSION = "v1"
MIN_MINUTES = 450
PLAYABLE_THRESHOLD = 0.15
ART_ROOT = Path("ml/artifacts/models")

# side-agnostic ROLE taxonomy
ROLE_MAP = {
    "GK": "Goalkeeper", "Second Striker": "Centre-Forward",
    "Left-Back": "Full-Back", "Right-Back": "Full-Back",
    "Left Winger": "Winger", "Right Winger": "Winger",
    "Left Midfield": "Winger", "Right Midfield": "Winger",
}
ROLE_VALID = {"Goalkeeper", "Centre-Back", "Full-Back", "Defensive Midfield",
              "Central Midfield", "Attacking Midfield", "Winger", "Centre-Forward"}

# side-aware taxonomy (keeps Left/Right; uses foot)
SIDE_MAP = {
    "GK": "Goalkeeper", "Second Striker": "Centre-Forward",
    "Left Midfield": "Left Winger", "Right Midfield": "Right Winger",
}
SIDE_VALID = {"Goalkeeper", "Centre-Back", "Left-Back", "Right-Back",
              "Defensive Midfield", "Central Midfield", "Attacking Midfield",
              "Left Winger", "Right Winger", "Centre-Forward"}

MODES = {
    "role": {"map": ROLE_MAP, "valid": ROLE_VALID, "cats": [], "dir": "position_v1"},
    "side": {"map": SIDE_MAP, "valid": SIDE_VALID, "cats": ["foot"], "dir": "position_side_v1"},
}


def _prep(mode: str):
    cfg = MODES[mode]
    df = load_features(FEATURE_SET_VERSION)
    pos = pd.read_sql("select id as player_id, primary_position from players", get_engine())
    df = df.merge(pos, on="player_id", how="left")
    df = df[df["minutes"] >= MIN_MINUTES].copy()
    df["label"] = df["primary_position"].replace(cfg["map"])
    df = df[df["label"].isin(cfg["valid"])].copy()
    feat_cols = feature_columns(df) + cfg["cats"]
    stat_cols = feature_columns(df)
    df[stat_cols] = df[stat_cols].apply(pd.to_numeric, errors="coerce")
    for c in cfg["cats"]:
        df[c] = df[c].fillna("unknown").astype(str)
    return df, feat_cols, cfg


def train(mode: str = "role") -> dict:
    df, feat_cols, cfg = _prep(mode)
    out = ART_ROOT / cfg["dir"]
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr_idx, te_idx = next(gss.split(df, groups=df["player_id"]))
    train_df, test_df = df.iloc[tr_idx], df.iloc[te_idx]
    g2 = GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=1)
    t2, v2 = next(g2.split(train_df, groups=train_df["player_id"]))
    fit_df, val_df = train_df.iloc[t2], train_df.iloc[v2]
    assert not (set(train_df["player_id"]) & set(test_df["player_id"])), "player leak!"
    log.info("position[%s]: fit=%d val=%d test=%d | %d classes, %d features (cats=%s)",
             mode, len(fit_df), len(val_df), len(test_df), df["label"].nunique(),
             len(feat_cols), cfg["cats"])

    model = CatBoostClassifier(loss_function="MultiClass", iterations=1500,
                               learning_rate=0.05, depth=6, l2_leaf_reg=5,
                               random_seed=42, verbose=0, early_stopping_rounds=80)
    model.fit(Pool(fit_df[feat_cols], fit_df["label"], cat_features=cfg["cats"]),
              eval_set=Pool(val_df[feat_cols], val_df["label"], cat_features=cfg["cats"]))

    y_true = test_df["label"].to_numpy()
    y_pred = model.predict(test_df[feat_cols]).ravel()
    labels = sorted(df["label"].unique())
    rep = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    conf = sorted(((int(cm[i, j]), labels[i], labels[j]) for i in range(len(labels))
                   for j in range(len(labels)) if i != j and cm[i, j] > 0), reverse=True)
    metrics = {
        "mode": mode, "accuracy": round(rep["accuracy"], 4),
        "macro_f1": round(f1_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "baseline_majority_acc": round(float(df["label"].value_counts(normalize=True).iloc[0]), 4),
        "n_test": len(test_df), "n_classes": len(labels),
        "per_class_f1": {k: round(rep[k]["f1-score"], 3) for k in labels},
        "top_confusions": [f"{a} -> {b} ({n})" for n, a, b in conf[:8]],
    }
    out.mkdir(parents=True, exist_ok=True)
    model.save_model(str(out / "model.cbm"))
    joblib.dump({"feature_cols": feat_cols, "labels": labels, "cats": cfg["cats"],
                 "feature_set_version": FEATURE_SET_VERSION}, out / "meta.joblib")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    log.info("position[%s]: accuracy %.3f (baseline %.3f) | macro-F1 %.3f",
             mode, metrics["accuracy"], metrics["baseline_majority_acc"], metrics["macro_f1"])
    log.info("  per-class F1: %s", metrics["per_class_f1"])
    return metrics


def load_model(mode: str = "role"):
    out = ART_ROOT / MODES[mode]["dir"]
    meta = joblib.load(out / "meta.joblib")
    model = CatBoostClassifier()
    model.load_model(str(out / "model.cbm"))
    return model, meta


def predict_positions(model, meta, X: pd.DataFrame,
                      playable_threshold: float = PLAYABLE_THRESHOLD) -> list[dict]:
    """Ranked positions per row: primary, secondary, and all playable roles."""
    Xf = X[meta["feature_cols"]].copy()
    for c in meta.get("cats", []):
        Xf[c] = Xf[c].fillna("unknown").astype(str)
    proba = model.predict_proba(Xf)
    classes = list(model.classes_)
    out = []
    for row in proba:
        ranked = sorted(zip(classes, row), key=lambda kv: kv[1], reverse=True)
        out.append({"primary": ranked[0][0],
                    "secondary": ranked[1][0] if len(ranked) > 1 else None,
                    "playable": [r for r, p in ranked if p >= playable_threshold],
                    "probs": {r: round(float(p), 3) for r, p in ranked}})
    return out


if __name__ == "__main__":
    r = train("role")
    s = train("side")
    lr = [k for k in s["per_class_f1"] if "Left" in k or "Right" in k]
    log.info("=== SIDE-AWARE L/R recovery (foot) ===")
    log.info("side model L/R per-class F1: %s", {k: s["per_class_f1"][k] for k in lr})
