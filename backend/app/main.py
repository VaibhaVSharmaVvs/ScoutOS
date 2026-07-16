import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.discover import router as discover_router
from app.api.health import router as health_router
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
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Phase 0: open. Tighten before deploy (Phase 8).
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(players_router)
app.include_router(predict_router)
app.include_router(discover_router)
app.include_router(analytics_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "Scout OS API", "version": "0.1.0", "docs": "/docs"}
