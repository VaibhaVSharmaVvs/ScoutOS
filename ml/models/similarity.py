"""Player Similarity model (Phase 4.1): autoencoder embeddings + FAISS NN.

Hybrid — two search modes over the same learned embedding space:
  - "current" : per player-SEASON embeddings; query = the player's latest season.
                "who plays like X right now / in their current role."
  - "career"  : one embedding per player = weighted average of their season
                embeddings (weight = minutes played x recency decay); query =
                that career vector. "who is X's career-style doppelganger."

The autoencoder compresses the 40 scaled style features -> a 16-dim embedding;
FAISS IndexFlatIP over L2-normalized embeddings gives cosine NN. Unsupervised, so
we evaluate via reconstruction loss + neighbour position-purity (both modes) +
face-valid example queries.

    python -m ml.models.similarity        # train, evaluate, persist
"""

from __future__ import annotations

import json
from functools import lru_cache
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
RECENCY_DECAY = 0.7   # career weight: minutes * DECAY**(latest_year - season_year)
OUT = Path("ml/artifacts/models") / MODEL_VERSION

# Raw autoencoder cosines cluster tightly near 1.0 for a player's closest matches
# (all top neighbours ~0.98-0.99), so shown as-is every result looks ~100%.
# Map cosine -> an interpretable "style match" in [0,1]: anchor 1.0 = identical,
# a fixed floor = unrelated, and raise to a power to spread the crowded top end.
# Monotonic, so ranking is unchanged; only self (excluded) reaches 100%.
SIM_FLOOR = 0.30
SIM_GAMMA = 10


def match_score(cosine: float) -> float:
    n = max(0.0, min(1.0, (cosine - SIM_FLOOR) / (1.0 - SIM_FLOOR)))
    return round(n**SIM_GAMMA, 3)
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
        f"where pf.feature_set_version='{FEATURE_SET_VERSION}'", get_engine()
    ).reset_index(drop=True)
    X = scale_features(list(df["features"]), FEATURE_SET_VERSION).astype("float32")
    return df.drop(columns=["features"]), X


def _train_ae(X: np.ndarray) -> AutoEncoder:
    n = len(X)
    idx = np.random.permutation(n)
    va, tr = idx[: int(n * 0.1)], idx[int(n * 0.1):]
    Xt = torch.tensor(X)
    model = AutoEncoder(X.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.MSELoss()
    for ep in range(EPOCHS):
        model.train()
        for b in range(0, len(tr), BATCH):
            batch = Xt[tr[b:b + BATCH]]
            opt.zero_grad()
            loss = loss_fn(model(batch)[0], batch)
            loss.backward()
            opt.step()
        if ep % 30 == 0 or ep == EPOCHS - 1:
            model.eval()
            with torch.no_grad():
                vl = loss_fn(model(Xt[va])[0], Xt[va]).item()
            log.info("epoch %d/%d val_recon_mse=%.4f", ep + 1, EPOCHS, vl)
    return model


def _raw_embeddings(model: AutoEncoder, X: np.ndarray) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        return model.enc(torch.tensor(X)).numpy().astype("float32")


def _career_embeddings(df: pd.DataFrame, Z_raw: np.ndarray):
    """Per-player weighted-average embedding: minutes x recency decay."""
    latest = int(df["start_year"].max())
    w = df["minutes"].clip(lower=1).to_numpy() * (RECENCY_DECAY ** (latest - df["start_year"].to_numpy()))
    vecs, rows = [], []
    for pid, g in df.groupby("player_id"):
        gw = w[g.index][:, None]
        vecs.append((Z_raw[g.index] * gw).sum(0) / gw.sum())
        rep = g.loc[g["minutes"].idxmax()]   # representative season = most minutes
        rows.append({"player_id": int(pid), "full_name": rep["full_name"],
                     "position_group": rep["position_group"],
                     "total_minutes": int(g["minutes"].sum()), "seasons": len(g)})
    return np.vstack(vecs).astype("float32"), pd.DataFrame(rows)


def _norm_index(Z_raw: np.ndarray):
    Z = Z_raw.copy()
    faiss.normalize_L2(Z)
    index = faiss.IndexFlatIP(Z.shape[1])
    index.add(Z)
    return Z, index


def _position_purity(pg, index, Z, k=5, sample=1500) -> float:
    rng = np.random.default_rng(0)
    rows = rng.choice(len(Z), size=min(sample, len(Z)), replace=False)
    _, I = index.search(Z[rows], k + 1)
    hits = tot = 0
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
    Z_raw = _raw_embeddings(model, X)

    Zn, season_index = _norm_index(Z_raw)                     # current mode
    C_raw, career_df = _career_embeddings(df, Z_raw)
    Cn, career_index = _norm_index(C_raw)                     # career mode

    purity_season = _position_purity(df["position_group"].to_numpy(), season_index, Zn)
    purity_career = _position_purity(career_df["position_group"].to_numpy(), career_index, Cn)
    model.eval()
    with torch.no_grad():
        recon_mse = round(float(nn.MSELoss()(model(torch.tensor(X))[0], torch.tensor(X))), 4)

    OUT.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), OUT / "autoencoder.pt")
    faiss.write_index(season_index, str(OUT / "season_index.faiss"))
    faiss.write_index(career_index, str(OUT / "career_index.faiss"))
    np.save(OUT / "season_embeddings.npy", Zn)
    np.save(OUT / "career_embeddings.npy", Cn)
    df.reset_index(drop=True).to_parquet(OUT / "season_rows.parquet")
    career_df.reset_index(drop=True).to_parquet(OUT / "career_rows.parquet")
    (OUT / "meta.json").write_text(json.dumps(
        {"latent_dim": LATENT_DIM, "n_input": int(X.shape[1]),
         "feature_set_version": FEATURE_SET_VERSION, "n_player_seasons": len(df),
         "n_players": len(career_df), "recency_decay": RECENCY_DECAY}, indent=2))
    metrics = {"recon_mse": recon_mse, "n_player_seasons": len(df), "n_players": len(career_df),
               "neighbor_position_purity_current": purity_season,
               "neighbor_position_purity_career": purity_career, "latent_dim": LATENT_DIM}
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))

    log.info("=== SIMILARITY MODEL (hybrid) ===")
    log.info("recon MSE %.4f | position-purity: current %.3f, career %.3f",
             recon_mse, purity_season, purity_career)
    log.info("saved -> %s", OUT)
    return metrics


# --- inference ---------------------------------------------------------------
@lru_cache(maxsize=2)
def _load_mode(mode: str):
    """Load (rows, embeddings, FAISS index) for a mode once, then keep resident.

    Called at API startup (registry.warmup) so the index lives in memory instead
    of being re-read from disk on every request.
    """
    prefix = "career" if mode == "career" else "season"
    rows = pd.read_parquet(OUT / f"{prefix}_rows.parquet")
    Z = np.load(OUT / f"{prefix}_embeddings.npy")
    index = faiss.read_index(str(OUT / f"{prefix}_index.faiss"))
    return rows, Z, index


def find_similar(player_id: int, k: int = 10, mode: str = "current",
                 same_position: bool = False) -> list[dict]:
    """Similar players by 'current' (latest-season) or 'career' style."""
    if mode not in ("current", "career"):
        raise ValueError("mode must be 'current' or 'career'")

    rows, Z, index = _load_mode(mode)
    if mode == "career":
        match = rows.index[rows["player_id"] == player_id]
        if len(match) == 0:
            return []
        qi = int(match[0])
    else:
        q = rows[rows["player_id"] == player_id]
        if q.empty:
            return []
        qi = int(q.sort_values("start_year").index[-1])       # latest season

    qpos = rows.at[qi, "position_group"]
    D, I = index.search(Z[qi:qi + 1], min(len(rows), 250))
    seen, out = {player_id}, []
    for score, j in zip(D[0], I[0]):
        pid = int(rows.at[j, "player_id"])
        if pid in seen or (same_position and rows.at[j, "position_group"] != qpos):
            continue
        seen.add(pid)
        entry = {"player": rows.at[j, "full_name"], "player_id": pid,
                 "position_group": rows.at[j, "position_group"],
                 "similarity": match_score(float(score))}
        if mode == "current":
            entry["season"] = int(rows.at[j, "start_year"])
        out.append(entry)
        if len(out) >= k:
            break
    return out


if __name__ == "__main__":
    train()
