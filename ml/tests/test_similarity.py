"""Tests for the Player Similarity model (Phase 4.1)."""

import json
from pathlib import Path

import pandas as pd
import pytest

ART = Path("ml/artifacts/models/similarity_v1")


@pytest.mark.skipif(not (ART / "metrics.json").exists(),
                    reason="similarity model not trained (run `python -m ml.models.similarity`)")
class TestTrainedSimilarity:
    def test_metrics_reasonable(self):
        m = json.loads((ART / "metrics.json").read_text())
        assert m["recon_mse"] < 0.5                     # autoencoder actually learned
        assert m["neighbor_position_purity"] > 0.6      # embedding captures role/style

    def test_embeddings_align_with_rows(self):
        import numpy as np
        Z = np.load(ART / "embeddings.npy")
        rows = pd.read_parquet(ART / "rows.parquet")
        assert Z.shape[0] == len(rows)
        assert Z.shape[1] == json.loads((ART / "meta.json").read_text())["latent_dim"]

    def test_find_similar_distinct_excludes_self_sorted(self):
        from ml.models.similarity import find_similar
        rows = pd.read_parquet(ART / "rows.parquet")
        pid = int(rows["player_id"].iloc[0])
        res = find_similar(pid, k=8)
        assert 0 < len(res) <= 8
        ids = [r["player_id"] for r in res]
        assert pid not in ids and len(ids) == len(set(ids))          # distinct, no self
        sims = [r["similarity"] for r in res]
        assert sims == sorted(sims, reverse=True)                    # ranked
        assert all(-1.001 <= s <= 1.001 for s in sims)               # cosine range

    def test_same_position_filter(self):
        from ml.models.similarity import find_similar
        rows = pd.read_parquet(ART / "rows.parquet")
        pid = int(rows["player_id"].iloc[0])
        qpos = rows[rows["player_id"] == pid].sort_values("start_year").iloc[-1]["position_group"]
        res = find_similar(pid, k=8, same_position=True)
        assert all(r["position_group"] == qpos for r in res)
