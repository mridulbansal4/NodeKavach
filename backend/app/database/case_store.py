"""
case_store.py — JSON-backed case persistence.

The runtime case store holds analysed accounts (demo cache + any uploaded /
single-account analyses). Backed by a single JSON file under backend/data/.
Deliberately simple: no external DB, fully offline, suitable for an air-gapped
bank security network.
"""
from __future__ import annotations

import json
import threading

from app.config import DATA_DIR
from app.models.schemas import AccountAnalysis, CaseRecord

_STORE_PATH = DATA_DIR / "cases.json"
_LOCK = threading.Lock()


def _read_all() -> dict[str, dict]:
    if not _STORE_PATH.exists():
        return {}
    try:
        return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_all(data: dict[str, dict]) -> None:
    _STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_case(record: CaseRecord) -> None:
    with _LOCK:
        data = _read_all()
        data[record.case_id] = record.model_dump(mode="json")
        _write_all(data)


def save_analysis(analysis: AccountAnalysis, *, is_demo: bool = False) -> CaseRecord:
    record = CaseRecord(
        case_id=analysis.case_id,
        risk_score=analysis.risk_score,
        severity=analysis.severity,
        typology=analysis.classification.typology,
        account_standing=analysis.account_profile.account_standing,
        occupation=analysis.account_profile.occupation,
        is_demo=is_demo,
        analysis=analysis,
    )
    save_case(record)
    return record


def get_case(case_id: str) -> CaseRecord | None:
    data = _read_all()
    if case_id in data:
        return CaseRecord.model_validate(data[case_id])
    return None


def list_cases() -> list[CaseRecord]:
    data = _read_all()
    records = [CaseRecord.model_validate(v) for v in data.values()]
    # Highest risk first.
    records.sort(key=lambda r: r.risk_score, reverse=True)
    return records


def clear_uploaded() -> int:
    """Remove non-demo cases (keep the demo library). Returns count removed."""
    with _LOCK:
        data = _read_all()
        kept = {k: v for k, v in data.items() if v.get("is_demo")}
        removed = len(data) - len(kept)
        _write_all(kept)
        return removed


def seed_demo_cases() -> int:
    """Ensure the 5 demo cases are present in the store. Returns count seeded."""
    from app.engines.investigation_cache import demo_case_records

    with _LOCK:
        data = _read_all()
        n = 0
        for rec in demo_case_records():
            if rec.case_id not in data:
                n += 1
            data[rec.case_id] = rec.model_dump(mode="json")
        _write_all(data)
        return n
