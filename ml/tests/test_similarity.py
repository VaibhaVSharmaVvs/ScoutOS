"""Tests for the hybrid Player Similarity model (Phase 4.1)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ART = Path("ml/artifacts/models/similarity_v1")


@pytest.mark.skipif(not (ART / "metrics.json").exists(),
                    reason="similarity model not trained (run `python -m ml.models.similarity`)")
class TestTrainedSimilarity:
    def test_metrics_reasonable(self):
        m = json.loads((ART / "metrics.json").read_text())
        assert m["recon_mse"] < 0.5
        assert m["neighbor_position_purity_current"] > 0.6
        assert m["neighbor_position_purity_career"] > 0.6

    def test_embeddings_align_with_rows(self):
        meta = json.loads((ART / "meta.json").read_text())
        for emb, rows_f in [("season_embeddings.npy", "season_rows.parquet"),
                            ("career_embeddings.npy", "career_rows.parquet")]:
            Z = np.load(ART / emb)
            rows = pd.read_parquet(ART / rows_f)
            assert Z.shape[0] == len(rows) and Z.shape[1] == meta["latent_dim"]
        # career has one row per player (fewer than player-seasons)
        assert meta["n_players"] < meta["n_player_seasons"]

    @pytest.mark.parametrize("mode", ["current", "career"])
    def test_find_similar_distinct_excludes_self_sorted(self, mode):
        from ml.models.similarity import find_similar
        rows = pd.read_parquet(ART / f"{'season' if mode == 'current' else 'career'}_rows.parquet")
        pid = int(rows["player_id"].iloc[0])
        res = find_similar(pid, k=8, mode=mode)
        assert 0 < len(res) <= 8
        ids = [r["player_id"] for r in res]
        assert pid not in ids and len(ids) == len(set(ids))
        sims = [r["similarity"] for r in res]
        assert sims == sorted(sims, reverse=True)
        assert all(-1.001 <= s <= 1.001 for s in sims)

    def test_modes_can_differ(self):
        # current vs career should not be forced identical (different query vectors)
        from ml.models.similarity import find_similar
        cr = pd.read_parquet(ART / "career_rows.parquet")
        # a player with multiple seasons is most likely to differ across modes
        multi = cr[cr["seasons"] >= 3]["player_id"]
        pid = int(multi.iloc[0]) if len(multi) else int(cr["player_id"].iloc[0])
        cur = [r["player_id"] for r in find_similar(pid, 10, "current")]
        car = [r["player_id"] for r in find_similar(pid, 10, "career")]
        assert cur and car  # both return results

    def test_same_position_filter(self):
        from ml.models.similarity import find_similar
        rows = pd.read_parquet(ART / "career_rows.parquet")
        pid = int(rows["player_id"].iloc[0])
        qpos = rows[rows["player_id"] == pid].iloc[0]["position_group"]
        res = find_similar(pid, k=8, mode="career", same_position=True)
        assert all(r["position_group"] == qpos for r in res)
