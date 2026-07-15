"""Tests for the Position model (Phase 4.3)."""

import json
from pathlib import Path

import pandas as pd
import pytest

from ml.models.position import LABEL_MAP, VALID

ART = Path("ml/artifacts/models/position_v1")


class TestTaxonomy:
    def test_side_agnostic(self):
        # no Left/Right classes survive (side isn't statistically determinable)
        assert not any("Left" in v or "Right" in v for v in VALID)
        assert LABEL_MAP["Left-Back"] == "Full-Back" == LABEL_MAP["Right-Back"]
        assert LABEL_MAP["Left Winger"] == "Winger" == LABEL_MAP["Right Winger"]


@pytest.mark.skipif(not (ART / "metrics.json").exists(),
                    reason="position model not trained (run `python -m ml.models.position`)")
class TestTrainedPositionModel:
    def test_beats_baseline_and_reasonable_f1(self):
        m = json.loads((ART / "metrics.json").read_text())
        assert m["accuracy"] > m["baseline_majority_acc"] * 2   # well above majority
        assert m["macro_f1"] > 0.6
        assert m["per_class_f1"]["Goalkeeper"] > 0.9            # GK is highly separable

    def test_features_exclude_label_leakage(self):
        import joblib
        meta = joblib.load(ART / "meta.joblib")
        assert "label" not in meta["feature_cols"]
        assert "primary_position" not in meta["feature_cols"]

    def test_model_loads_and_predicts_valid_label(self):
        import joblib
        from catboost import CatBoostClassifier
        meta = joblib.load(ART / "meta.joblib")
        model = CatBoostClassifier()
        model.load_model(str(ART / "model.cbm"))
        X = pd.DataFrame([{c: 1.0 for c in meta["feature_cols"]}])
        pred = model.predict(X).ravel()[0]
        assert pred in set(meta["labels"])
