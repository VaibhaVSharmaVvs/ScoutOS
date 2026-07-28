import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# NOTE: app/__init__.py bootstraps the repo root onto sys.path so the lazy
# `ml`/`etl` imports in the serving layer resolve regardless of launch cwd.
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.discover import router as discover_router
from app.api.explain import router as explain_router
from app.api.health import router as health_router
from app.api.passkey import router as passkey_router
from app.api.players import router as players_router
from app.api.predict import router as predict_router
from app.config import get_settings
from app.middleware import RateLimitMiddleware, ResponseCacheMiddleware

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load models + FAISS indexes once at startup (best-effort — see warmup()).
    from app.ml.registry import warmup

    warmup()
    yield


app = FastAPI(
    title="Scout OS API",
    version="0.1.0",
    description="AI-powered football scouting platform",
    lifespan=lifespan,
)

# Middleware runs outermost-first in reverse registration order: rate-limit
# guards first, then the response cache, then CORS.
app.add_middleware(ResponseCacheMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    limit=settings.rate_limit_requests,
    window=settings.rate_limit_window_seconds,
)
_cors = settings.cors_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    # credentials can't be combined with a wildcard origin per the CORS spec
    allow_credentials="*" not in _cors,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(passkey_router)
app.include_router(players_router)
app.include_router(predict_router)
app.include_router(discover_router)
app.include_router(analytics_router)
app.include_router(explain_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "Scout OS API", "version": "0.1.0", "docs": "/docs"}
