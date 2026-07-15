"""Position model (Phase 4.3): CatBoost multiclass from a player's stat profile.

Target: the player's detailed position (Transfermarkt sub-position), consolidated
to a clean taxonomy. Features: the per-90 / rate style features (NOT position or
league — those would leak). Split: by PLAYER (GroupShuffleSplit) so a player's
other seasons can't leak their label into test. Metrics: accuracy, macro-F1,
per-class F1, top confusions, vs majority-class baseline.

    python -m ml.models.position         # train, evaluate, persist
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit

from app.db.session import get_engine
from etl.load.db import log
from ml.models.dataset import feature_columns, load_features

MODEL_VERSION = "position_v1"
FEATURE_SET_VERSION = "v1"
MIN_MINUTES = 450
OUT = Path("ml/artifacts/models") / MODEL_VERSION

# Consolidate to SIDE-AGNOSTIC roles: a player's per-90 stat profile can't
# distinguish left from right (LB vs RB, LW vs RW are statistically identical),
# so we predict role, not side. Left/Right merge into Full-Back / Winger.
LABEL_MAP = {
    "GK": "Goalkeeper", "Second Striker": "Centre-Forward",
    "Left-Back": "Full-Back", "Right-Back": "Full-Back",
    "Left Winger": "Winger", "Right Winger": "Winger",
    "Left Midfield": "Winger", "Right Midfield": "Winger",
}
VALID = {
    "Goalkeeper", "Centre-Back", "Full-Back", "Defensive Midfield",
    "Central Midfield", "Attacking Midfield", "Winger", "Centre-Forward",
}


PLAYABLE_THRESHOLD = 0.15  # a role is "playable" if predicted prob >= this


def load_model():
    """Load the trained CatBoost model + metadata."""
    import joblib
    from catboost import CatBoostClassifier

    meta = joblib.load(OUT / "meta.joblib")
    model = CatBoostClassifier()
    model.load_model(str(OUT / "model.cbm"))
    return model, meta


def predict_positions(model, meta, X: pd.DataFrame,
                      playable_threshold: float = PLAYABLE_THRESHOLD) -> list[dict]:
    """Ranked positions per row: primary, secondary, and all playable roles.

    Returns [{primary, secondary, playable:[roles>=threshold], probs:{role:p}}].
    Surfaces the model's positional versatility instead of a single best guess.
    """
    proba = model.predict_proba(X[meta["feature_cols"]])
    classes = list(model.classes_)
    out = []
    for row in proba:
        ranked = sorted(zip(classes, row), key=lambda kv: kv[1], reverse=True)
        out.append({
            "primary": ranked[0][0],
            "secondary": ranked[1][0] if len(ranked) > 1 else None,
            "playable": [r for r, p in ranked if p >= playable_threshold],
            "probs": {r: round(float(p), 3) for r, p in ranked},
        })
    return out


def _prep():
    df = load_features(FEATURE_SET_VERSION)
    pos = pd.read_sql("select id as player_id, primary_position from players", get_engine())
    df = df.merge(pos, on="player_id", how="left")
    df = df[df["minutes"] >= MIN_MINUTES].copy()
    df["label"] = df["primary_position"].replace(LABEL_MAP)
    df = df[df["label"].isin(VALID)].copy()
    # style profile only (per-90 + rates); exclude the added label/position cols
    feat_cols = [c for c in feature_columns(df) if c not in ("label", "primary_position")]
    df[feat_cols] = df[feat_cols].apply(pd.to_numeric, errors="coerce")
    return df, feat_cols


def train() -> dict:
    df, feat_cols = _prep()
    # player-level split (no player in both train and test)
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr_idx, te_idx = next(gss.split(df, groups=df["player_id"]))
    train_df, test_df = df.iloc[tr_idx], df.iloc[te_idx]
    # carve a validation set (by player) from train for early stopping
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=1)
    t2, v2 = next(gss2.split(train_df, groups=train_df["player_id"]))
    fit_df, val_df = train_df.iloc[t2], train_df.iloc[v2]

    assert not (set(train_df["player_id"]) & set(test_df["player_id"])), "player leak!"
    log.info("position model: fit=%d val=%d test=%d | %d classes, %d features",
             len(fit_df), len(val_df), len(test_df), df["label"].nunique(), len(feat_cols))

    model = CatBoostClassifier(
        loss_function="MultiClass", iterations=1500, learning_rate=0.05, depth=6,
        l2_leaf_reg=5, random_seed=42, verbose=0, early_stopping_rounds=80,
    )
    model.fit(Pool(fit_df[feat_cols], fit_df["label"]),
              eval_set=Pool(val_df[feat_cols], val_df["label"]))

    y_true = test_df["label"].to_numpy()
    y_pred = model.predict(test_df[feat_cols]).ravel()

    labels = sorted(df["label"].unique())
    rep = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
    majority = df["label"].value_counts(normalize=True).iloc[0]
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    # top confusions (off-diagonal)
    conf = []
    for i, a in enumerate(labels):
        for j, b in enumerate(labels):
            if i != j and cm[i, j] > 0:
                conf.append((int(cm[i, j]), a, b))
    conf.sort(reverse=True)

    metrics = {
        "accuracy": round(rep["accuracy"], 4),
        "macro_f1": round(f1_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "weighted_f1": round(f1_score(y_true, y_pred, average="weighted", zero_division=0), 4),
        "baseline_majority_acc": round(float(majority), 4),
        "n_test": len(test_df), "n_classes": len(labels),
        "per_class_f1": {k: round(rep[k]["f1-score"], 3) for k in labels},
        "top_confusions": [f"{a} -> {b} ({n})" for n, a, b in conf[:8]],
    }

    OUT.mkdir(parents=True, exist_ok=True)
    model.save_model(str(OUT / "model.cbm"))
    joblib.dump({"feature_cols": feat_cols, "labels": labels,
                 "feature_set_version": FEATURE_SET_VERSION}, OUT / "meta.joblib")
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))

    log.info("=== POSITION MODEL ===")
    log.info("accuracy %.3f (baseline %.3f) | macro-F1 %.3f | weighted-F1 %.3f",
             metrics["accuracy"], metrics["baseline_majority_acc"],
             metrics["macro_f1"], metrics["weighted_f1"])
    log.info("per-class F1: %s", metrics["per_class_f1"])
    log.info("top confusions: %s", metrics["top_confusions"][:5])
    log.info("saved -> %s", OUT)
    return metrics


if __name__ == "__main__":
    train()
