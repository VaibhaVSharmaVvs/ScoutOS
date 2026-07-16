"""Redis-backed response cache — degrades to a no-op when Redis is unreachable.

Every call is guarded: if Redis is down or slow, the API still serves (just
without caching). Short socket timeouts keep a dead Redis from stalling requests.
"""

from __future__ import annotations

import logging

from app.config import get_settings

log = logging.getLogger("scoutos.cache")

_client = None
_disabled = False


def _redis():
    global _client, _disabled
    if _disabled:
        return None
    if _client is None:
        try:
            from redis import Redis

            _client = Redis.from_url(
                get_settings().redis_url,
                socket_connect_timeout=0.3, socket_timeout=0.3,
            )
        except Exception as exc:  # noqa: BLE001 - never let cache setup break serving
            log.warning("redis unavailable, caching disabled: %s", exc)
            _disabled = True
            return None
    return _client


def get_bytes(key: str) -> bytes | None:
    client = _redis()
    if client is None:
        return None
    try:
        return client.get(key)
    except Exception:  # noqa: BLE001
        return None


def set_bytes(key: str, value: bytes, ttl: int) -> None:
    client = _redis()
    if client is None:
        return
    try:
        client.set(key, value, ex=ttl)
    except Exception:  # noqa: BLE001
        pass
