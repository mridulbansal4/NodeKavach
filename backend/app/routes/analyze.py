"""
Analysis routes:
  POST /api/analyze/dataset        — upload a CSV, kick off the staged pipeline
  GET  /api/analyze/status/{job}   — poll pipeline progress
  POST /api/analyze/account        — analyse a single account feature dict
"""
from __future__ import annotations

import shutil

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.analyzers.dataset_loader import sha256_of_file
from app.config import UPLOADS_DIR
from app.database import case_store
from app.models.schemas import AccountAnalysis, AccountRequest, JobStatus
from app.service import JOBS, analyze_account, run_full_pipeline, start_pipeline

router = APIRouter(prefix="/api/analyze", tags=["analyze"])


@router.post("/dataset", response_model=JobStatus)
async def analyze_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(default=None),
    retrain: bool = False,
):
    """Accept a CSV upload (or fall back to the bundled BOI dataset) and run the
    full pipeline as a background task. Records the SHA-256 of every upload."""
    dataset_path = None
    if file is not None:
        dest = UPLOADS_DIR / file.filename
        with open(dest, "wb") as out:
            shutil.copyfileobj(file.file, out)
        dataset_path = str(dest)
        digest = sha256_of_file(dest)
    else:
        digest = None

    job = start_pipeline(dataset_path, retrain=retrain)
    job.summary["upload_sha256"] = digest
    background_tasks.add_task(run_full_pipeline, job.job_id, dataset_path, retrain)
    return job


@router.get("/status/{job_id}", response_model=JobStatus)
def analyze_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return job


@router.post("/account", response_model=AccountAnalysis)
def analyze_single(req: AccountRequest, model: str = "B", use_ollama: bool = True):
    if not req.features:
        raise HTTPException(status_code=400, detail="No features supplied.")
    analysis = analyze_account(
        req.features, case_id=req.case_id, model=model, use_ollama=use_ollama
    )
    case_store.save_analysis(analysis, is_demo=False)
    return analysis
