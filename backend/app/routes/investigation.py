"""
Investigation routes:
  GET /api/investigation            — the demo account library (5 pre-cached)
  GET /api/investigation/{case_id}  — pre-cached investigation for a demo account
                                      (falls back to the runtime case store)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.database import case_store
from app.engines.investigation_cache import load_demo_cache
from app.models.schemas import AccountAnalysis

router = APIRouter(prefix="/api/investigation", tags=["investigation"])


@router.get("", response_model=list[AccountAnalysis])
def demo_library():
    return load_demo_cache()


@router.get("/{case_id}", response_model=AccountAnalysis)
def get_investigation(case_id: str):
    for a in load_demo_cache():
        if a.case_id == case_id:
            return a
    rec = case_store.get_case(case_id)
    if rec and rec.analysis:
        return rec.analysis
    raise HTTPException(status_code=404, detail=f"Investigation {case_id} not found.")
