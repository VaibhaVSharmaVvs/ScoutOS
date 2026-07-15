"""Tests for the Club Fit engine (Phase 4.5). No ground truth -> validate the
scoring math + face-validity invariants."""

import json
from pathlib import Path

import pytest

CFG = Path("config/club_fit_weights.json")


def test_weights_sum_to_one():
    w = json.loads(CFG.read_text())
    assert abs(sum(w[k] for k in ("tactical", "squad", "financial", "age")) - 1.0) < 1e-6


@pytest.fixture(scope="module")
def engine():
    try:
        from ml.models.club_fit import ClubFitEngine
        eng = ClubFitEngine()
        if not len(eng.players) or not eng.club_name:
            pytest.skip("no data loaded (run the load + feature pipeline)")
        return eng
    except Exception as e:  # noqa: BLE001 - DB/data may be unavailable in CI
        pytest.skip(f"club fit engine unavailable: {e}")


def test_score_bounds_and_weighted_sum(engine):
    pid = int(engine.players.index[0])
    cid = int(next(iter(engine.club_name)))
    r = engine.score(pid, cid)
    for k in ("tactical_fit", "squad_fit", "financial_fit", "age_fit", "overall_fit"):
        assert 0 <= r[k] <= 100
    expected = sum(engine.weights[k] * r[f"{k}_fit"] for k in engine.weights)
    assert abs(r["overall_fit"] - expected) < 0.6   # overall is the weighted sum


def test_rank_clubs_sorted(engine):
    pid = int(engine.players.index[0])
    df = engine.rank_clubs(pid, top=5)
    assert len(df) <= 5
    assert list(df["overall_fit"]) == sorted(df["overall_fit"], reverse=True)


def test_financial_tracks_budget_for_expensive_player(engine):
    # for the most valuable player, financial fit should be higher at a richer
    # club than a poorer one, and clearly discriminate (unaffordable somewhere)
    pid = int(engine.players["value"].idxmax())
    valid = {c: b for c, b in engine.club_budget.items() if b == b and c in engine.club_name}
    rich, poor = max(valid, key=valid.get), min(valid, key=valid.get)
    fit_rich = engine.score(pid, int(rich))["financial_fit"]
    fit_poor = engine.score(pid, int(poor))["financial_fit"]
    assert fit_rich > fit_poor
    fins = [engine.score(pid, int(c))["financial_fit"] for c in engine.club_name]
    assert min(fins) < 30      # genuinely unaffordable at the smallest clubs
