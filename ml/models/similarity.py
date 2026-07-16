"""Player Similarity model (Phase 4.1): autoencoder embeddings + FAISS NN.

An autoencoder compresses each player-season's scaled style profile (the 40
base features) into a low-dim embedding; a FAISS index over the L2-normalized
embeddings powers cosine nearest-neighbour search ("players with a similar
playing style"). Unsupervised, so we evaluate via reconstruction loss and
position-purity of neighbours (do nearest players share the role?) + face-valid
example queries.

    python -m ml.models.similarity        # train, evaluate, persist
"""

from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
import torch
from torch import nn

from app.db.session import get_engine
from etl.load.db import log
from ml.features.scaler import transform as scale_features

MODEL_VERSION = "similarity_v1"
FEATURE_SET_VERSION = "v1"
LATENT_DIM = 16
EPOCHS, BATCH, LR = 120, 256, 1e-3
OUT = Path("ml/artifacts/models") / MODEL_VERSION
torch.manual_seed(42)
np.random.seed(42)


class AutoEncoder(nn.Module):
    def __init__(self, d_in: int, d_lat: int = LATENT_DIM):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(d_in, 64), nn.ReLU(), nn.Linear(64, 32),
                                 nn.ReLU(), nn.Linear(32, d_lat))
        self.dec = nn.Sequential(nn.Linear(d_lat, 32), nn.ReLU(), nn.Linear(32, 64),
                                 nn.ReLU(), nn.Linear(64, d_in))

    def forward(self, x):
        z = self.enc(x)
        return self.dec(z), z


def _load():
    df = pd.read_sql(
        "select pf.player_id, pf.season_id, s.start_year, pf.position_group, "
        "p.full_name, pf.minutes, pf.features "
        "from player_features pf join players p on p.id=pf.player_id "
        "join seasons s on s.id=pf.season_id "
        f"where pf.feature_set_version='{FEATURE_SET_VERSION}'", get_engine())
    X = scale_features(list(df["features"]), FEATURE_SET_VERSION).astype("float32")
    return df.drop(columns=["features"]), X


def _train_ae(X: np.ndarray) -> AutoEncoder:
    n = len(X)
    idx = np.random.permutation(n)
    val_n = int(n * 0.1)
    tr, va = idx[val_n:], idx[:val_n]
    Xt = torch.tensor(X)
    model = AutoEncoder(X.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.MSELoss()
    for ep in range(EPOCHS):
        model.train()
        for b in range(0, len(tr), BATCH):
            batch = Xt[tr[b:b + BATCH]]
            opt.zero_grad()
            recon, _ = model(batch)
            loss = loss_fn(recon, batch)
            loss.backward()
            opt.step()
        if ep % 30 == 0 or ep == EPOCHS - 1:
            model.eval()
            with torch.no_grad():
                vl = loss_fn(model(Xt[va])[0], Xt[va]).item()
            log.info("epoch %d/%d val_recon_mse=%.4f", ep + 1, EPOCHS, vl)
    return model


def _embeddings(model: AutoEncoder, X: np.ndarray) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        z = model.enc(torch.tensor(X)).numpy().astype("float32")
    faiss.normalize_L2(z)   # unit vectors -> inner product = cosine
    return z


def _position_purity(df, index, Z, k=5, sample=1500) -> float:
    rng = np.random.default_rng(0)
    rows = rng.choice(len(df), size=min(sample, len(df)), replace=False)
    pg = df["position_group"].to_numpy()
    hits = tot = 0
    D, I = index.search(Z[rows], k + 1)
    for r, neigh in zip(rows, I):
        for j in neigh:
            if j != r:
                hits += pg[j] == pg[r]
                tot += 1
    return round(hits / tot, 4)


def train() -> dict:
    df, X = _load()
    log.info("similarity: %d player-seasons, %d features -> %d-dim embedding",
             len(df), X.shape[1], LATENT_DIM)
    model = _train_ae(X)
    Z = _embeddings(model, X)
    index = faiss.IndexFlatIP(LATENT_DIM)
    index.add(Z)

    purity = _position_purity(df, index, Z)
    model.eval()
    with torch.no_grad():
        recon_mse = round(float(nn.MSELoss()(model(torch.tensor(X))[0], torch.tensor(X))), 4)

    OUT.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), OUT / "autoencoder.pt")
    faiss.write_index(index, str(OUT / "index.faiss"))
    np.save(OUT / "embeddings.npy", Z)
    df.reset_index(drop=True).to_parquet(OUT / "rows.parquet")
    joblib_meta = {"latent_dim": LATENT_DIM, "n_input": int(X.shape[1]),
                   "feature_set_version": FEATURE_SET_VERSION, "n_rows": len(df)}
    (OUT / "meta.json").write_text(json.dumps(joblib_meta, indent=2))
    metrics = {"recon_mse": recon_mse, "neighbor_position_purity": purity,
               "n_rows": len(df), "latent_dim": LATENT_DIM}
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))

    log.info("=== SIMILARITY MODEL ===")
    log.info("recon MSE %.4f | neighbour position-purity %.3f (share role)", recon_mse, purity)
    log.info("saved -> %s", OUT)
    return metrics


# --- inference ---------------------------------------------------------------
def find_similar(player_id: int, k: int = 10, same_position: bool = False) -> list[dict]:
    rows = pd.read_parquet(OUT / "rows.parquet")
    Z = np.load(OUT / "embeddings.npy")
    index = faiss.read_index(str(OUT / "index.faiss"))
    q = rows[rows["player_id"] == player_id]
    if q.empty:
        return []
    qi = q.sort_values("start_year").index[-1]   # latest season
    qpos = rows.at[qi, "position_group"]
    D, I = index.search(Z[qi:qi + 1], min(len(rows), 200))
    seen, out = {player_id}, []
    for score, j in zip(D[0], I[0]):
        pid = int(rows.at[j, "player_id"])
        if pid in seen:
            continue
        if same_position and rows.at[j, "position_group"] != qpos:
            continue
        seen.add(pid)
        out.append({"player": rows.at[j, "full_name"], "player_id": pid,
                    "position_group": rows.at[j, "position_group"],
                    "season": int(rows.at[j, "start_year"]),
                    "similarity": round(float(score), 3)})
        if len(out) >= k:
            break
    return out


if __name__ == "__main__":
    train()
