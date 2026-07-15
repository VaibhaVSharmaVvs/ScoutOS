"""Phase 3c: fit and persist the feature scaler for a feature-set version.

Models (Phase 4) must train and serve on identical scaling, so we persist one
artifact set per feature-set version:
  - scaler.joblib     StandardScaler fit on median-imputed base features
  - feature_names.json ordered base-feature list (the model input contract)
  - medians.json      per-feature medians for imputing missing values at serve
  - metadata.json     version / counts

Percentile features (…_pct_pos / …_pct_lg) are already in [0,1] and are NOT
scaled — models can use them directly.

    python -m ml.features.scaler          # fit + save
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from app.db.session import get_engine
from etl.load.db import log
from ml.features.build import FEATURE_SET_VERSION

ARTIFACT_ROOT = Path("ml/artifacts")


def _base_feature_frame(version: str) -> pd.DataFrame:
    eng = get_engine()
    df = pd.read_sql(
        "select features from player_features where feature_set_version = "
        f"'{version}'", eng
    )
    feats = pd.json_normalize(df["features"])
    base = [c for c in feats.columns if not c.endswith(("_pct_pos", "_pct_lg"))]
    return feats[sorted(base)]


def fit(version: str = FEATURE_SET_VERSION) -> Path:
    X = _base_feature_frame(version).apply(pd.to_numeric, errors="coerce")
    medians = X.median()
    # Drop degenerate features (all-NaN -> NaN median): no source populates them
    # (e.g. carries_prog_dist, dribblers_challenged, prog_rec, take_on_pct).
    keep = [c for c in X.columns if pd.notna(medians[c])]
    dropped = [c for c in X.columns if c not in keep]
    if dropped:
        log.info("dropping %d degenerate (all-null) features: %s", len(dropped), dropped)
    X, medians = X[keep], medians[keep]
    X_imp = X.fillna(medians)
    scaler = StandardScaler().fit(X_imp.to_numpy())

    out = ARTIFACT_ROOT / f"features_{version}"
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, out / "scaler.joblib")
    (out / "feature_names.json").write_text(json.dumps(list(X.columns), indent=2))
    (out / "medians.json").write_text(json.dumps(
        {k: round(float(v), 6) for k, v in medians.items()}, indent=2))
    (out / "metadata.json").write_text(json.dumps(
        {"feature_set_version": version, "n_features": X.shape[1],
         "n_rows": int(X.shape[0])}, indent=2))
    log.info("scaler saved: %s (%d features, %d rows)", out, X.shape[1], X.shape[0])
    return out


def load(version: str = FEATURE_SET_VERSION):
    out = ARTIFACT_ROOT / f"features_{version}"
    scaler = joblib.load(out / "scaler.joblib")
    names = json.loads((out / "feature_names.json").read_text())
    medians = json.loads((out / "medians.json").read_text())
    return scaler, names, medians


def transform(feature_dicts: list[dict], version: str = FEATURE_SET_VERSION) -> np.ndarray:
    """Turn player_features JSONB dicts into a scaled model-input matrix."""
    scaler, names, medians = load(version)
    df = pd.DataFrame(feature_dicts).reindex(columns=names)
    df = df.fillna(pd.Series(medians))
    return scaler.transform(df.to_numpy())


if __name__ == "__main__":
    fit()
