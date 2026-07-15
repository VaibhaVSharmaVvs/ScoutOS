"""Tests for Phase 3 feature engineering."""

from pathlib import Path

import numpy as np
import pytest

from ml.features.build import PER90, _pos_group


class TestPositionGroup:
    @pytest.mark.parametrize("pos,expected", [
        ("Goalkeeper", "GK"), ("GK", "GK"),
        ("Centre-Back", "DEF"), ("Left-Back", "DEF"), ("DF", "DEF"),
        ("Central Midfield", "MID"), ("Defensive Midfield", "MID"), ("MF", "MID"),
        ("Centre-Forward", "FWD"), ("Left Winger", "FWD"), ("FW", "FWD"),
        ("", "UNK"), (None, "UNK"),
    ])
    def test_groups(self, pos, expected):
        assert _pos_group(pos) == expected


class TestScalerArtifact:
    """Integration: exercised only when the v1 artifact has been built."""

    def _artifact_ready(self):
        return (Path("ml/artifacts/features_v1/scaler.joblib").exists()
                and Path("ml/artifacts/features_v1/feature_names.json").exists())

    def test_transform_shape_and_imputation(self):
        if not self._artifact_ready():
            pytest.skip("scaler artifact not built (run `python -m ml.features.scaler`)")
        from ml.features.scaler import load, transform
        _, names, _ = load("v1")
        # two rows: one full-ish, one nearly empty -> medians imputed, no NaN out
        rows = [{n: 1.0 for n in names[:5]}, {}]
        X = transform(rows, "v1")
        assert X.shape == (2, len(names))
        assert not np.isnan(X).any()

    def test_feature_contract_covers_core_per90(self):
        if not self._artifact_ready():
            pytest.skip("scaler artifact not built")
        from ml.features.scaler import load
        _, names, _ = load("v1")
        # core, always-populated per-90 metrics must be in the model contract
        # (degenerate all-null metrics are intentionally dropped by fit())
        core = ["goals", "assists", "xg", "tackles", "interceptions",
                "pass_prog", "carries_prog", "sca", "gca"]
        for m in core:
            assert f"{m}_p90" in names, f"missing {m}_p90"
        assert set(PER90)  # PER90 imported/non-empty
