"""Passkey (WebAuthn) endpoint tests.

The full ceremony needs a real authenticator (browser + Windows Hello/Touch ID),
which can't run headless — that's verified manually. Here we cover the
option-generation and error paths, which are pure server logic.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _db_ready() -> bool:
    """Most passkey tests are pure server logic (challenge generation, error
    paths) and run anywhere. Only login/complete's unknown-passkey path reaches a
    DB lookup, so that one test is gated on a reachable DB (skips in bare CI)."""
    try:
        from sqlalchemy import create_engine, text

        from app.config import get_settings

        # dedicated short-timeout probe so it fails fast (never hangs) when the
        # DB host is unreachable rather than actively refusing.
        eng = create_engine(get_settings().database_url, connect_args={"connect_timeout": 3})
        try:
            with eng.connect() as conn:
                conn.execute(text("select 1"))
            return True
        finally:
            eng.dispose()
    except Exception:
        return False


def test_register_begin_returns_discoverable_options():
    r = client.post("/auth/passkey/register/begin", json={"display_name": "Laptop"})
    assert r.status_code == 200
    body = r.json()
    assert body["ceremony_id"]
    opt = body["options"]
    assert opt["rp"]["id"] == "localhost"
    assert opt["authenticatorSelection"]["residentKey"] == "required"
    assert opt["challenge"]
    assert opt["user"]["name"] == "Laptop"


def test_login_begin_is_usernameless():
    r = client.post("/auth/passkey/login/begin")
    assert r.status_code == 200
    body = r.json()
    assert body["ceremony_id"]
    # discoverable: no allowCredentials restriction
    assert not body["options"].get("allowCredentials")


def test_register_complete_bad_credential_is_400():
    begin = client.post("/auth/passkey/register/begin", json={}).json()
    r = client.post("/auth/passkey/register/complete",
                    json={"ceremony_id": begin["ceremony_id"], "credential": {"bad": "x"}})
    assert r.status_code == 400  # clean error, not a 500


def test_complete_with_expired_ceremony_is_400():
    r = client.post("/auth/passkey/login/complete",
                    json={"ceremony_id": "nope", "credential": {"id": "x"}})
    assert r.status_code == 400


@pytest.mark.skipif(not _db_ready(), reason="DB not available (unknown-passkey path does a DB lookup)")
def test_login_complete_unknown_passkey_is_404():
    begin = client.post("/auth/passkey/login/begin").json()
    r = client.post(
        "/auth/passkey/login/complete",
        json={"ceremony_id": begin["ceremony_id"], "credential": {"id": "unknown-cred"}},
    )
    assert r.status_code == 404
