"""Tests for the Potential Growth model (Phase 4.4)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.models.dataset import feature_columns

ART = Path("ml/artifacts/models/potential_v1")


class TestFeatureColumnsRobust:
    """Regression: feature selection must never pull in model-added columns."""

    def test_ignores_added_columns(self):
        df = pd.DataFrame(columns=[
            "goals_p90", "tackles_p90", "pass_cmp_pct",       # real features
            "goals_p90_pct_pos", "ref_date", "future_3",       # must be excluded
            "cur_value_log", "label", "age", "market_value_eur",
        ])
        cols = feature_columns(df)
        assert {"goals_p90", "tackles_p90", "pass_cmp_pct"} <= set(cols)
        for junk in ["goals_p90_pct_pos", "ref_date", "future_3", "cur_value_log",
                     "label", "age", "market_value_eur"]:
            assert junk not in cols


@pytest.mark.skipif(not (ART / "metrics.json").exists(),
                    reason="potential model not trained (run `python -m ml.models.potential`)")
class TestTrainedPotential:
    def _m(self):
        return json.loads((ART / "metrics.json").read_text())

    def test_3yr_beats_flat_baseline(self):
        h3 = self._m()["h3"]
        assert not h3.get("skipped")
        assert h3["mae_eur"] < h3["flat_baseline_mae_eur"]     # beats "value unchanged"
        assert h3["growth_direction_acc"] > 0.6                 # calls up/down well

    def test_5yr_skipped_data_limited(self):
        # only ~980 pairs available -> correctly skipped, not silently wrong
        assert self._m()["h5"].get("skipped") is True

    def test_models_load_and_predict(self):
        import joblib
        import lightgbm as lgb
        meta = joblib.load(ART / "meta.joblib")
        n = 0
        for h in meta["horizons"]:
            f = ART / f"model_h{h}.txt"
            if not f.exists():
                continue
            booster = lgb.Booster(model_file=str(f))
            X = pd.DataFrame([{c: 1.0 for c in meta["feature_cols"]}])
            for c in meta["categoricals"]:
                X[c] = X[c].astype("category")
            pred = booster.predict(X[meta["feature_cols"]])
            assert np.isfinite(pred).all()
            n += 1
        assert n >= 2   # +1yr and +3yr trained
