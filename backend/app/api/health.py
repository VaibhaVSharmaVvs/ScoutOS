from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="scoutos-backend", version="0.1.0")


@router.get("/health/models")
def model_health() -> dict:
    """Which trained model artifacts are present for serving."""
    from app.ml.registry import available

    models = available()
    return {"status": "ok" if all(models.values()) else "degraded", "models": models}
