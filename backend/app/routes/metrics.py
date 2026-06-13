"""GET /api/metrics — model validation metrics (Model A & Model B)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.engines.model_engine import ENGINE
from app.engines.validation_engine import compute_all, load_cached_metrics
from app.models.schemas import MetricsResponse

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("", response_model=MetricsResponse)
def get_metrics(recompute: bool = False):
    if not recompute:
        cached = load_cached_metrics()
        if cached is not None:
            return cached
    if not ENGINE.is_loaded:
        ENGINE.load()
    if not ENGINE.is_loaded:
        raise HTTPException(status_code=503, detail="Models not trained yet.")
    return compute_all(ENGINE)
