"""Phase 6 LLM explanation-layer tests.

The live Anthropic call can't run here (no key), so the real provider path is
verified with a mock; the stub path and the full pipeline run against the real
DB + models. Skips cleanly when the DB is unavailable.
"""

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


def test_report_is_grounded(haaland_id):
    body = client.get(f"/players/{haaland_id}/explain").json()
    assert body["kind"] == "report"
    assert body["narrative"]
    g = body["grounding"]
    # every narrative claim must be backed by these model outputs
    assert "value_model" in g and "top_drivers" in g["value_model"]
    assert "position_model" in g
    assert g["bio"]["name"] == "Erling Haaland"


def test_report_stub_without_key(haaland_id):
    # no ANTHROPIC_API_KEY in the test env -> deterministic stub
    body = client.get(f"/players/{haaland_id}/explain").json()
    assert body["provider"] in ("stub", "stub-fallback")


def test_club_fit_explain(haaland_id):
    fits = client.get(f"/players/{haaland_id}/club-fit", params={"top": 1}).json()
    club_id = fits["results"][0]["club_id"]
    body = client.get(f"/players/{haaland_id}/explain/club-fit/{club_id}").json()
    assert set(body["grounding"]["sub_scores"]) == {"tactical", "squad", "financial", "age"}


def test_comparison_explain(haaland_id):
    sims = client.get(f"/players/{haaland_id}/similar", params={"k": 1}).json()
    other = sims["results"][0]["player_id"]
    body = client.get(f"/players/{haaland_id}/explain/comparison/{other}").json()
    assert "player_a" in body["grounding"] and "player_b" in body["grounding"]


def test_explain_404():
    assert client.get("/players/99999999/explain").status_code == 404


# --- provider + cache unit tests (no DB needed) ------------------------------
def test_stub_provider_reads_facts():
    from app.llm.client import _stub

    user = "intro\n\nFACTS:\n- Alpha fact.\n- Beta fact."
    out = _stub(user)
    assert "Alpha fact." in out and "Beta fact." in out
    assert out.startswith("[stub explanation")


def test_anthropic_path_mocked(monkeypatch):
    """Verify the real provider wiring without a live call."""
    import anthropic

    from app.config import get_settings
    from app.llm import client as llm_client

    calls = {}

    class FakeBlock:
        type = "text"
        text = "Scout narrative."

    class FakeMessages:
        def create(self, **kwargs):
            calls.update(kwargs)
            return type("Msg", (), {"content": [FakeBlock()]})()

    class FakeAnthropic:
        def __init__(self, api_key=None):
            calls["api_key"] = api_key
            self.messages = FakeMessages()

    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)
    get_settings.cache_clear()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
    try:
        text, provider = llm_client.generate("SYS", "- fact one")
        assert provider == "anthropic"
        assert text == "Scout narrative."
        assert calls["system"] == "SYS"
        assert calls["messages"][0]["content"] == "- fact one"
        assert calls["temperature"] <= 0.3  # guardrail: low temperature
    finally:
        get_settings.cache_clear()


def test_cache_roundtrip(monkeypatch):
    from app.llm import service

    store: dict[str, bytes] = {}
    monkeypatch.setattr(service, "get_bytes", lambda k: store.get(k))
    monkeypatch.setattr(service, "set_bytes", lambda k, v, ttl: store.__setitem__(k, v))

    facts = {"model_versions": {"x": "v1"}, "bio": {"name": "Test"}}
    monkeypatch.setattr(service.prompts, "RENDERERS",
                        {"report": lambda f: "- a fact"})
    first = service._run("report", "42", facts)
    assert first["cached"] is False
    second = service._run("report", "42", facts)
    assert second["cached"] is True
    assert second["narrative"] == first["narrative"]
