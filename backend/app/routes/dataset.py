"""
Dataset routes:
  GET  /api/dataset/stats   — descriptive stats + 18 domain-hint table
  POST /api/dataset/demo    — (re)load the bundled BOI dataset and run pipeline
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from app.analyzers.dataset_stats import compute_dataset_stats, load_cached_stats
from app.models.schemas import DatasetStats, JobStatus
from app.service import run_full_pipeline, start_pipeline

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


@router.get("/stats", response_model=DatasetStats)
def dataset_stats(recompute: bool = False):
    if not recompute:
        cached = load_cached_stats()
        if cached is not None:
            return cached
    return compute_dataset_stats()


@router.post("/demo", response_model=JobStatus)
def load_demo(background_tasks: BackgroundTasks):
    """Run the full pipeline over the bundled BOI dataset."""
    job = start_pipeline(dataset_path=None, retrain=False)
    background_tasks.add_task(run_full_pipeline, job.job_id, None, False)
    return job
