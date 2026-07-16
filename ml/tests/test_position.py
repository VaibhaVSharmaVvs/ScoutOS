"""Tests for the Position models (Phase 4.3): role (side-agnostic) + side-aware."""

import json
from pathlib import Path

import pandas as pd
import pytest

from ml.models.position import ROLE_MAP, ROLE_VALID, SIDE_VALID

ROLE = Path("ml/artifacts/models/position_v1")
SIDE = Path("ml/artifacts/models/position_side_v1")


class TestTaxonomy:
    def test_role_is_side_agnostic(self):
        assert not any("Left" in v or "Right" in v for v in ROLE_VALID)
        assert ROLE_MAP["Left-Back"] == "Full-Back" == ROLE_MAP["Right-Back"]

    def test_side_keeps_left_right(self):
        assert {"Left-Back", "Right-Back", "Left Winger", "Right Winger"} <= SIDE_VALID


@pytest.mark.skipif(not (ROLE / "metrics.json").exists(),
                    reason="role model not trained")
class TestRoleModel:
    def test_beats_baseline(self):
        m = json.loads((ROLE / "metrics.json").read_text())
        assert m["accuracy"] > m["baseline_majority_acc"] * 2
        assert m["macro_f1"] > 0.6
        assert m["per_class_f1"]["Goalkeeper"] > 0.9

    def test_features_no_leak(self):
        import joblib
        meta = joblib.load(ROLE / "meta.joblib")
        assert "label" not in meta["feature_cols"] and "primary_position" not in meta["feature_cols"]
        assert meta["cats"] == []   # role model uses no categorical (style only)

    def test_predict_positions(self):
        from ml.models.position import load_model, predict_positions
        model, meta = load_model("role")
        X = pd.DataFrame([{c: 1.0 for c in meta["feature_cols"]}])
        res = predict_positions(model, meta, X)[0]
        assert res["primary"] in set(meta["labels"])
        assert res["secondary"] != res["primary"]
        assert abs(sum(res["probs"].values()) - 1.0) < 0.01


@pytest.mark.skipif(not (SIDE / "metrics.json").exists(),
                    reason="side-aware model not trained")
class TestSideModel:
    def test_foot_recovers_fullback_side(self):
        m = json.loads((SIDE / "metrics.json").read_text())
        # foot lets the model separate LB from RB well (stats alone gave ~0.35/0.53)
        assert m["per_class_f1"]["Left-Back"] > 0.7
        assert m["per_class_f1"]["Right-Back"] > 0.7
        assert m["accuracy"] > m["baseline_majority_acc"] * 2

    def test_uses_foot_feature(self):
        import joblib
        meta = joblib.load(SIDE / "meta.joblib")
        assert "foot" in meta["cats"] and "foot" in meta["feature_cols"]

    def test_predict_positions_with_foot(self):
        from ml.models.position import load_model, predict_positions
        model, meta = load_model("side")
        row = {c: 1.0 for c in meta["feature_cols"]}
        row["foot"] = "left"
        res = predict_positions(model, meta, pd.DataFrame([row]))[0]
        assert res["primary"] in set(meta["labels"])
