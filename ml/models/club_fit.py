"""Club Fit engine (Phase 4.5): transparent weighted scoring — NOT ML.

For a (player, club) pair it computes four interpretable sub-scores in [0,100]
and an overall weighted score:
  - Tactical : does the player's playing style match the club's? (cosine of
               z-scored per-90 style profiles: player-vs-players, club-vs-clubs)
  - Squad    : does the club need this position? (depth of regulars + up/downgrade)
  - Financial: can the club afford the player? (value vs the club's spend level)
  - Age      : does the player fit the club's age profile?
Weights live in config/club_fit_weights.json (tunable without redeploy).

    python -m ml.models.club_fit         # demo: face-validity examples
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.db.session import get_engine
from etl.load.db import log
from ml._paths import CLUB_FIT_CONFIG

SEASON = "2024-25"
FEATURE_SET_VERSION = "v1"
CONFIG = CLUB_FIT_CONFIG

# (player per-90 feature, team-profile per-90 key) — the shared style dimensions
STYLE_DIMS = [
    ("tackles_p90", "tackles_per90"), ("interceptions_p90", "interceptions_per90"),
    ("clearances_p90", "clearances_per90"), ("pass_prog_p90", "prog_passes_per90"),
    ("carries_prog_p90", "prog_carries_per90"), ("sca_p90", "sca_per90"),
    ("gca_p90", "gca_per90"), ("key_passes_p90", "key_passes_per90"),
    ("goals_p90", "goals_per90"), ("assists_p90", "assists_per90"),
    ("shots_p90", "shots_per90"),
]


def _z(frame: pd.DataFrame) -> pd.DataFrame:
    mu, sd = frame.mean(), frame.std(ddof=0).replace(0, np.nan)
    return ((frame - mu) / sd).fillna(0.0)


class ClubFitEngine:
    def __init__(self, season: str = SEASON, version: str = FEATURE_SET_VERSION):
        cfg = json.loads(CONFIG.read_text())
        self.weights = {k: cfg[k] for k in ("tactical", "squad", "financial", "age")}
        self.reg_minutes = cfg.get("playable_min_minutes", 900)
        self.prime_age = cfg.get("prime_age", 27)
        eng = get_engine()

        pf = pd.read_sql(
            "select pf.player_id, p.full_name, pf.position_group, pf.age, pf.minutes, "
            "pf.club_id, nullif(pf.market_value_eur,'NaN')::numeric as value, pf.features "
            "from player_features pf join players p on p.id=pf.player_id "
            "join seasons s on s.id=pf.season_id "
            f"where pf.feature_set_version='{version}' and s.label='{season}'", eng)
        feats = pd.json_normalize(pf["features"])
        self.players = pd.concat([pf.drop(columns=["features"]), feats], axis=1)
        self.players["value"] = pd.to_numeric(self.players["value"], errors="coerce")
        self.players = self.players.set_index("player_id")

        # player style z-matrix
        p_cols = [pc for pc, _ in STYLE_DIMS]
        self.player_z = _z(self.players[p_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0))

        # club style z-matrix from team profiles
        prof = pd.read_sql(
            "select ttp.club_id, c.name as club, ttp.profile from team_tactical_profiles ttp "
            "join clubs c on c.id=ttp.club_id join seasons s on s.id=ttp.season_id "
            f"where s.label='{season}'", eng)
        prof_feats = pd.json_normalize(prof["profile"])
        t_cols = [tc for _, tc in STYLE_DIMS]
        club_style = prof_feats.reindex(columns=t_cols).apply(pd.to_numeric, errors="coerce").fillna(0.0)
        club_style.index = prof["club_id"]
        self.club_name = dict(zip(prof["club_id"], prof["club"]))
        self.club_z = _z(club_style)

        # squads + budgets + age profile per club (from current-season players)
        self.squads = {cid: g for cid, g in self.players.reset_index().groupby("club_id")}
        self.club_budget, self.club_age = {}, {}
        for cid, g in self.squads.items():
            vals = g["value"].dropna()
            self.club_budget[cid] = float(vals.quantile(0.85)) if len(vals) else np.nan
            w = g["minutes"].clip(lower=1)
            self.club_age[cid] = float((g["age"] * w).sum() / w.sum()) if len(g) else np.nan

    # --- sub-scores ---
    def _tactical(self, pid, cid):
        if pid not in self.player_z.index or cid not in self.club_z.index:
            return None
        a, b = self.player_z.loc[pid].to_numpy(), self.club_z.loc[cid].to_numpy()
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 50.0
        cos = float(np.dot(a, b) / (na * nb))
        return round((cos + 1) / 2 * 100, 1)

    def _squad(self, player, cid):
        g = self.squads.get(cid)
        if g is None:
            return 50.0
        inc = g[(g["position_group"] == player["position_group"]) & (g["minutes"] >= self.reg_minutes)]
        n = len(inc[inc["player_id"] != player.name]) if hasattr(player, "name") else len(inc)
        base = {0: 100, 1: 80, 2: 55, 3: 35}.get(n, 20)
        if len(inc):
            inc_vals = inc["value"].dropna()
            pv = player["value"]
            if len(inc_vals) and pd.notna(pv):
                if pv >= inc_vals.quantile(0.75):      # clear upgrade
                    base = min(100, base + 15)
                elif pv <= inc_vals.quantile(0.40):    # downgrade on current options
                    base *= 0.7
        return round(float(base), 1)

    def _financial(self, player, cid):
        budget, pv = self.club_budget.get(cid), player["value"]
        if pd.isna(budget) or pd.isna(pv):
            return 50.0
        if pv <= budget:
            return 100.0
        return round(float(max(0.0, 100 * budget / pv)), 1)  # decays as value exceeds budget

    def _age(self, player, cid):
        ca = self.club_age.get(cid)
        target = min(ca, self.prime_age) if pd.notna(ca) else self.prime_age
        return round(float(max(0.0, 100 - 5 * abs(player["age"] - target))), 1)

    def score(self, player_id: int, club_id: int) -> dict | None:
        if player_id not in self.players.index or club_id not in self.club_name:
            return None
        p = self.players.loc[player_id]
        subs = {
            "tactical": self._tactical(player_id, club_id),
            "squad": self._squad(p, club_id),
            "financial": self._financial(p, club_id),
            "age": self._age(p, club_id),
        }
        if subs["tactical"] is None:
            subs["tactical"] = 50.0
        overall = round(sum(self.weights[k] * subs[k] for k in self.weights), 1)
        return {"player": p["full_name"], "club": self.club_name[club_id],
                **{f"{k}_fit": v for k, v in subs.items()}, "overall_fit": overall}

    def rank_clubs(self, player_id: int, top: int = 10) -> pd.DataFrame:
        # exclude the player's current club — they already fit that system, so
        # it's noise in a "where should they go next" ranking.
        current = None
        if player_id in self.players.index:
            cur = self.players.loc[player_id].get("club_id")
            current = int(cur) if pd.notna(cur) else None
        rows = [self.score(player_id, cid) for cid in self.club_name if cid != current]
        rows = [r for r in rows if r]
        return pd.DataFrame(rows).sort_values("overall_fit", ascending=False).head(top)


def _demo():
    eng = ClubFitEngine()
    players = pd.read_sql("select id, normalized_name from players", get_engine())
    for name in ["rodri", "erling haaland", "bruno guimaraes"]:
        ids = players.loc[players["normalized_name"] == name, "id"]
        # pick the id that has a 2024-25 feature row (active player)
        cand = [int(i) for i in ids if int(i) in eng.players.index]
        if cand:
            pid = cand[0]
            df = eng.rank_clubs(pid, top=4)
            if len(df):
                log.info("Top club fits for %s:", df.iloc[0]["player"])
                for _, r in df.iterrows():
                    log.info("  %-22s overall=%.0f (tac %.0f/squad %.0f/fin %.0f/age %.0f)",
                             r["club"], r["overall_fit"], r["tactical_fit"],
                             r["squad_fit"], r["financial_fit"], r["age_fit"])


if __name__ == "__main__":
    _demo()
