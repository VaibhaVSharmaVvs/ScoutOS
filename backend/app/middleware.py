"""HTTP middleware: response caching and simple rate limiting.

- ResponseCacheMiddleware: caches 200 responses for cacheable GET paths in Redis
  (TTL-based). No-ops transparently when Redis is down.
- RateLimitMiddleware: fixed-window per-client limiter (in-memory). Good enough
  for a single process / dev; a multi-worker deploy should move the counter to
  Redis (Phase 8).
"""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.cache import get_bytes, set_bytes

# path prefixes worth caching, with TTL seconds
CACHE_TTL = 300
CACHEABLE_PREFIXES = ("/players", "/clubs")


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method != "GET" or not path.startswith(CACHEABLE_PREFIXES):
            return await call_next(request)

        key = f"resp:{path}?{request.url.query}"
        hit = get_bytes(key)
        if hit is not None:
            return Response(content=hit, media_type="application/json",
                            headers={"X-Cache": "HIT"})

        response = await call_next(request)
        if response.status_code == 200:
            body = b"".join([chunk async for chunk in response.body_iterator])
            set_bytes(key, body, ttl=CACHE_TTL)
            headers = {"X-Cache": "MISS"}
            return Response(content=body, status_code=200,
                            media_type=response.media_type, headers=headers)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window: `limit` requests per `window` seconds per client IP."""

    def __init__(self, app, limit: int = 120, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/health"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - self.window
        hits = [t for t in self._hits[client] if t > window_start]
        if len(hits) >= self.limit:
            return Response(content='{"detail":"rate limit exceeded"}', status_code=429,
                            media_type="application/json",
                            headers={"Retry-After": str(self.window)})
        hits.append(now)
        self._hits[client] = hits
        return await call_next(request)
