"""Tests for the Market Value model (Phase 4.2)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.models.dataset import feature_columns, time_split

ART = Path("ml/artifacts/models/value_v1")


class TestDatasetHelpers:
    def test_time_split_no_leakage(self):
        df = pd.DataFrame({"start_year": [2020, 2021, 2022, 2023, 2024],
                           "x": range(5)})
        train, val, test = time_split(df, test_start_year=2024, val_start_year=2023)
        assert set(train["start_year"]) == {2020, 2021, 2022}
        assert set(val["start_year"]) == {2023}
        assert set(test["start_year"]) == {2024}
        # strictly disjoint, and train is entirely before test
        assert train["start_year"].max() < test["start_year"].min()

    def test_feature_columns_excludes_percentiles_and_context(self):
        df = pd.DataFrame(columns=[
            "player_id", "season_id", "start_year", "market_value_eur", "age",
            "goals_p90", "tackles_p90", "goals_p90_pct_pos", "goals_p90_pct_lg",
        ])
        cols = feature_columns(df)
        assert "goals_p90" in cols and "tackles_p90" in cols
        assert not any(c.endswith(("_pct_pos", "_pct_lg")) for c in cols)
        assert "age" not in cols and "market_value_eur" not in cols


@pytest.mark.skipif(not (ART / "metrics.json").exists(),
                    reason="value model not trained (run `python -m ml.models.value`)")
class TestTrainedValueModel:
    def test_beats_baseline_and_reasonable_r2(self):
        m = json.loads((ART / "metrics.json").read_text())
        assert m["mae_eur"] < m["baseline_mae_eur"]      # beats predict-the-median
        assert m["r2_eur"] > 0.5                           # explains majority of variance
        assert m["test_season"] == 2024                    # evaluated on the future season

    def test_model_loads_and_predicts(self):
        import lightgbm as lgb
        import joblib
        booster = lgb.Booster(model_file=str(ART / "model.txt"))
        meta = joblib.load(ART / "meta.joblib")
        cols = meta["feature_cols"]
        # one synthetic row (categoricals as category) -> a finite prediction
        row = {c: 1.0 for c in cols}
        X = pd.DataFrame([row])
        for c in meta["categoricals"]:
            X[c] = X[c].astype("category")
        pred = booster.predict(X[cols])
        assert pred.shape == (1,) and np.isfinite(pred).all()
