"""
service.py — analysis orchestration.

Two entry points used by the routes:
  * analyze_account(features, ...)   -> full single-account AccountAnalysis
  * run_full_pipeline(job_id, path)  -> staged batch pipeline over a whole CSV,
    reporting progress per stage (Dataset Loading, Feature Engineering, Model
    Training/Ready, Batch Prediction, Metrics Computation, AI Reports).

Holds the in-memory job registry and the shared ModelEngine singleton.
"""
from __future__ import annotations

import time
import uuid

import pandas as pd

from app.analyzers.dataset_loader import load_dataset, sha256_of_file
from app.config import TARGET_COLUMN
from app.engines.classification_engine import classify
from app.engines.model_engine import ENGINE
from app.engines.risk_engine import (
    assess,
    decode_occupation,
    decode_standing,
)
from app.engines.shap_engine import explain_row
from app.engines.validation_engine import compute_all
from app.models.schemas import (
    AccountAnalysis,
    AccountProfile,
    JobStatus,
    PipelineStage,
    StageStatus,
)

# In-memory job registry (single-process demo).
JOBS: dict[str, JobStatus] = {}


# --------------------------------------------------------------------------- #
# Single-account analysis
# --------------------------------------------------------------------------- #
def analyze_account(
    features: dict,
    *,
    case_id: str | None = None,
    model: str = "B",
    use_ollama: bool = True,
    with_report: bool = True,
) -> AccountAnalysis:
    from app.ai.report_generator import generate_report

    if not ENGINE.is_loaded:
        ENGINE.load()
    case_id = case_id or f"ACC-{uuid.uuid4().hex[:8].upper()}"

    prob = ENGINE.predict_single(features, use_model=model)
    threshold = ENGINE.model_a.threshold if model.upper() == "A" else ENGINE.model_b.threshold
    a = assess(prob, features, threshold)

    classification = classify(features, a["behavioural_indicators"], a["risk_score"])
    trained = ENGINE.model_a if model.upper() == "A" else ENGINE.model_b
    shap_values = explain_row(trained, features, top_n=10)

    profile = AccountProfile(
        occupation=decode_occupation(features),
        account_standing=decode_standing(features),
        age=_get(features, "F3894"),
        account_tenure=_get(features, "F2956"),
    )
    f3912 = _get(features, "F3912")

    analysis = AccountAnalysis(
        case_id=case_id,
        risk_score=a["risk_score"],
        risk_probability=a["risk_probability"],
        severity=a["severity"],
        classification=classification,
        shap_values=shap_values,
        behavioural_indicators=a["behavioural_indicators"],
        account_profile=profile,
        f3912_flag=bool(f3912 is not None and f3912 >= 1),
        model_used=f"Model {model.upper()}",
    )
    if with_report:
        text, src = generate_report(analysis, use_ollama=use_ollama)
        analysis.ai_report = text
        analysis.ai_report_source = src
    return analysis


def _get(features: dict, code: str):
    v = features.get(code)
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Full-dataset pipeline (staged, runs in a background task)
# --------------------------------------------------------------------------- #
def _new_job() -> JobStatus:
    job = JobStatus(
        job_id=f"job-{uuid.uuid4().hex[:8]}",
        status="queued",
        stages=[
            PipelineStage(name="Dataset Loading"),
            PipelineStage(name="Feature Engineering"),
            PipelineStage(name="Model Training"),
            PipelineStage(name="Batch Prediction"),
            PipelineStage(name="Metrics Computation"),
            PipelineStage(name="AI Reports"),
        ],
    )
    JOBS[job.job_id] = job
    return job


def _stage(job: JobStatus, idx: int) -> PipelineStage:
    return job.stages[idx]


def run_full_pipeline(job_id: str, dataset_path: str | None = None,
                      retrain: bool = False, flag_threshold: float = 60.0) -> None:
    job = JOBS[job_id]
    job.status = "running"
    from app.database import case_store

    try:
        if not ENGINE.is_loaded and not retrain:
            ENGINE.load()

        # Stage 1: Dataset Loading
        s = _stage(job, 0); s.status = StageStatus.RUNNING; t = time.time()
        ds = load_dataset(dataset_path) if dataset_path else load_dataset()
        s.duration_ms = round((time.time() - t) * 1000, 1)
        s.status = StageStatus.DONE
        s.detail = f"{ds.n_rows} rows, {ds.n_features} features, {len(ds.dropped_null_columns)} null cols dropped"

        # Stage 2: Feature Engineering (already fitted in the loaded models)
        s = _stage(job, 1); s.status = StageStatus.RUNNING; t = time.time()
        n_feats = len(ENGINE.model_b.selected_features) if ENGINE.model_b else 0
        s.duration_ms = round((time.time() - t) * 1000, 1)
        s.status = StageStatus.DONE
        s.detail = f"{n_feats} features selected (top-200 MI, 18 domain hints prioritised)"

        # Stage 3: Model Training (or reuse)
        s = _stage(job, 2); s.status = StageStatus.RUNNING; t = time.time()
        if retrain or not ENGINE.is_loaded:
            ENGINE.train(dataset_path)
            s.detail = "Trained Model A + Model B (SMOTE-in-fold, scale_pos_weight=112)"
        else:
            s.detail = "Loaded pre-trained Model A + Model B from cache"
        s.duration_ms = round((time.time() - t) * 1000, 1)
        s.status = StageStatus.DONE

        # Stage 4: Batch Prediction (all accounts, Model B)
        s = _stage(job, 3); s.status = StageStatus.RUNNING; t = time.time()
        proba = ENGINE.predict_batch(ds.X, use_model="B")
        from app.engines.risk_engine import score_from_proba, severity_for
        thr = ENGINE.get_threshold()
        scores = [score_from_proba(float(p), thr) for p in proba]
        flagged_idx = [i for i, sc in enumerate(scores) if sc >= flag_threshold]
        s.duration_ms = round((time.time() - t) * 1000, 1)
        s.status = StageStatus.DONE
        s.detail = f"Scored {len(scores)} accounts; {len(flagged_idx)} flagged (score ≥ {flag_threshold:.0f})"

        # Stage 5: Metrics Computation
        s = _stage(job, 4); s.status = StageStatus.RUNNING; t = time.time()
        if ds.y is not None:
            compute_all(ENGINE, dataset_path)
        s.duration_ms = round((time.time() - t) * 1000, 1)
        s.status = StageStatus.DONE
        s.detail = "PR-AUC, ROC-AUC, P@K, confusion matrices computed for Model A & B"

        # Stage 6: AI Reports — build full analyses (SHAP + report) for the top
        # flagged accounts and persist them as case records. Uses the fast
        # deterministic fallback report (no Ollama) to keep batch latency low;
        # the demo library and single-account endpoint use live Ollama.
        s = _stage(job, 5); s.status = StageStatus.RUNNING; t = time.time()
        ranked = sorted(flagged_idx, key=lambda i: scores[i], reverse=True)[:25]
        case_store.clear_uploaded()
        for i in ranked:
            feats = ds.X.iloc[i].to_dict()
            analysis = analyze_account(
                feats, case_id=f"BOI-{i:05d}", model="B",
                use_ollama=False, with_report=True,
            )
            case_store.save_analysis(analysis, is_demo=False)
        s.duration_ms = round((time.time() - t) * 1000, 1)
        s.status = StageStatus.DONE
        s.detail = f"Built SHAP + reports for top {len(ranked)} flagged accounts"

        mule_count = int(ds.y.sum()) if ds.y is not None else None
        job.summary = {
            "rows": ds.n_rows,
            "features_selected": n_feats,
            "flagged": len(flagged_idx),
            "mule_count": mule_count,
            "sha256": ds.sha256,
            "model_b_threshold": thr,
        }
        job.status = "complete"
    except Exception as exc:  # noqa: BLE001
        job.status = "error"
        job.error = str(exc)
        for st in job.stages:
            if st.status == StageStatus.RUNNING:
                st.status = StageStatus.ERROR


def start_pipeline(dataset_path: str | None = None, retrain: bool = False) -> JobStatus:
    job = _new_job()
    return job
