"""Phase 5 API tests. These hit the real Postgres + trained model artifacts, so
they skip cleanly when the DB or a model is unavailable (e.g. bare CI)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _db_ready() -> bool:
    try:
        return client.get("/players/search", params={"q": "haaland"}).status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_ready(), reason="DB/data not available")


@pytest.fixture(scope="module")
def haaland_id() -> int:
    hits = client.get("/players/search", params={"q": "Haaland"}).json()
    match = [h for h in hits if h["full_name"] == "Erling Haaland"]
    if not match:
        pytest.skip("Haaland not in dataset")
    return match[0]["id"]


def test_health_models():
    body = client.get("/health/models").json()
    assert set(body["models"]) == {
        "value", "potential", "position_role", "position_side", "similarity", "club_fit",
    }


def test_search_min_length():
    assert client.get("/players/search", params={"q": "a"}).status_code == 422


def test_profile(haaland_id):
    body = client.get(f"/players/{haaland_id}").json()
    assert body["full_name"] == "Erling Haaland"
    assert body["seasons"]  # has season history
    assert body["market_value_eur"] > 0


def test_profile_404():
    assert client.get("/players/99999999").status_code == 404


def test_predict_value(haaland_id):
    body = client.get(f"/players/{haaland_id}/predict/value").json()
    assert body["predicted_value_eur"] > 0
    assert body["drivers"] and all("effect" in d for d in body["drivers"])


def test_predict_potential(haaland_id):
    body = client.get(f"/players/{haaland_id}/predict/potential", params={"horizon": 3}).json()
    assert body["horizon_years"] == 3
    assert body["predicted_value_eur"] > 0


def test_predict_potential_bad_horizon(haaland_id):
    assert client.get(
        f"/players/{haaland_id}/predict/potential", params={"horizon": 2}
    ).status_code == 400


def test_predict_position(haaland_id):
    body = client.get(f"/players/{haaland_id}/predict/position").json()
    assert body["primary"] == "Centre-Forward"
    assert abs(sum(body["probs"].values()) - 1.0) < 0.02
    assert body["side_aware"] is not None  # Haaland has a known foot


def test_similar_with_traits(haaland_id):
    body = client.get(f"/players/{haaland_id}/similar", params={"k": 5}).json()
    assert len(body["results"]) == 5
    top = body["results"][0]
    assert 0 <= top["similarity"] <= 1
    assert top["shared_traits"]  # explain=True by default


def test_club_fit_ranking(haaland_id):
    body = client.get(f"/players/{haaland_id}/club-fit", params={"top": 5}).json()
    assert len(body["results"]) == 5
    fits = [r["overall_fit"] for r in body["results"]]
    assert fits == sorted(fits, reverse=True)
    for r in body["results"]:
        assert 0 <= r["overall_fit"] <= 100


def test_squad_analysis(haaland_id):
    # get a real club_id from Haaland's club-fit ranking
    fits = client.get(f"/players/{haaland_id}/club-fit", params={"top": 1}).json()
    club_id = fits["results"][0]["club_id"]
    body = client.get(f"/clubs/{club_id}/squad-analysis").json()
    assert body["squad_size"] > 0
    assert {d["position_group"] for d in body["depth"]} == {"GK", "DEF", "MID", "FWD"}
    assert isinstance(body["gaps"], list)


def test_squad_analysis_404():
    assert client.get("/clubs/99999999/squad-analysis").status_code == 404


def test_career_simulation(haaland_id):
    body = client.get(f"/players/{haaland_id}/career-simulation").json()
    labels = [p["label"] for p in body["trajectory"]]
    assert labels == ["current", "+1yr", "+3yr"]
    assert body["trajectory"][0]["value_eur"] > 0
    assert body["trajectory"][-1]["drivers"]  # projected points carry drivers


def test_cache_header_present():
    r = client.get("/players/search", params={"q": "Haaland"})
    assert r.headers.get("X-Cache") in ("HIT", "MISS")


def test_auth_flow():
    email, pw = "pytest-user@example.com", "secret-pw-123"
    reg = client.post("/auth/register", json={"email": email, "password": pw})
    assert reg.status_code in (201, 409)  # idempotent across runs
    assert client.get("/auth/me").status_code == 401  # no token
    token = client.post(
        "/auth/login", data={"username": email, "password": pw}
    ).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == email
    assert client.post(
        "/auth/login", data={"username": email, "password": "wrong"}
    ).status_code == 401


def test_rate_limit():
    from fastapi import FastAPI

    from app.middleware import RateLimitMiddleware

    app2 = FastAPI()
    app2.add_middleware(RateLimitMiddleware, limit=3, window=60)

    @app2.get("/ping")
    def ping():
        return {"ok": True}

    cc = TestClient(app2)
    codes = [cc.get("/ping").status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3:] == [429, 429]
