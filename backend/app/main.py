from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.discover import router as discover_router
from app.api.health import router as health_router
from app.api.players import router as players_router
from app.api.predict import router as predict_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Scout OS API",
    version="0.1.0",
    description="AI-powered football scouting platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Phase 0: open. Tighten before deploy (Phase 8).
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(players_router)
app.include_router(predict_router)
app.include_router(discover_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "Scout OS API", "version": "0.1.0", "docs": "/docs"}
