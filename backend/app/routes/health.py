"""GET /api/health — system health (model, Ollama, dataset)."""
from __future__ import annotations

from fastapi import APIRouter

from app.ai.ollama_client import CLIENT
from app.config import DEFAULT_DATASET
from app.engines.model_engine import ENGINE
from app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    if not ENGINE.is_loaded:
        ENGINE.load()
    ollama = CLIENT.health()
    dataset_loaded = DEFAULT_DATASET.exists()
    return HealthResponse(
        status="ok",
        model_loaded=ENGINE.is_loaded,
        active_model="Model B (F3912 excluded)",
        ollama=ollama,
        dataset_loaded=dataset_loaded,
        dataset_accounts=9082 if dataset_loaded else 0,
    )
