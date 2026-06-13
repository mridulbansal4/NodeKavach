"""
Case routes:
  GET /api/cases             — all cases (demo cache + uploaded)
  GET /api/cases/{case_id}   — full case detail incl. AI report
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.database import case_store
from app.models.schemas import CaseRecord

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("", response_model=list[CaseRecord])
def list_cases():
    return case_store.list_cases()


@router.get("/{case_id}", response_model=CaseRecord)
def get_case(case_id: str):
    rec = case_store.get_case(case_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    return rec
