"""Tests for the explainability layer (driving factors for the LLM layer)."""

from pathlib import Path

import joblib
import pytest

from ml.models import explain

VALUE = Path("ml/artifacts/models/value_v1")
POT = Path("ml/artifacts/models/potential_v1")


def _driver_shape_ok(drivers):
    assert drivers, "expected at least one driver"
    for d in drivers:
        assert set(d) == {"feature", "label", "value", "effect", "weight"}
        assert d["effect"] in ("increases", "decreases")
        assert d["weight"] >= 0
    # sorted by descending magnitude
    assert [d["weight"] for d in drivers] == sorted((d["weight"] for d in drivers), reverse=True)


def test_label_fallback():
    assert explain._label("goals_p90") == "goals/90"
    assert explain._label("some_unknown_p90") == "some unknown/90"


@pytest.mark.skipif(not (VALUE / "model.txt").exists(), reason="value model not trained")
def test_explain_value():
    meta = joblib.load(VALUE / "meta.joblib")
    row = {c: 1.0 for c in meta["feature_cols"]}
    for c in meta["categoricals"]:
        row[c] = None
    out = explain.explain_value(row, top_n=5)
    assert out["predicted_value_eur"] >= 0
    assert len(out["drivers"]) == 5
    _driver_shape_ok(out["drivers"])


@pytest.mark.skipif(not (POT / "model_h3.txt").exists(), reason="potential model not trained")
def test_explain_potential():
    meta = joblib.load(POT / "meta.joblib")
    row = {c: 1.0 for c in meta["feature_cols"]}
    for c in meta["categoricals"]:
        row[c] = None
    out = explain.explain_potential(row, horizon=3, top_n=6)
    assert out["horizon_years"] == 3
    assert out["predicted_value_eur"] >= 0
    _driver_shape_ok(out["drivers"])
