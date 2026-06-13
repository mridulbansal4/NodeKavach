"""
validation_engine.py — held-out evaluation & Model A vs B comparison.

Evaluates each model on its deterministic 20% hold-out split (the positional
indices stored on the TrainedModel at training time, so the test rows are the
exact ones never seen during fitting / threshold tuning).

Reports:
  * PR-AUC      (PRIMARY — headlined everywhere)
  * ROC-AUC
  * Precision / Recall / F1   (at the tuned threshold)
  * KS statistic
  * Confusion matrix (TP/FP/TN/FN)
  * Precision@K for K = 50, 100
  * False positive rate
  * Accuracy   (computed but explicitly deprioritised — see schema warning)
  * Top-20 SHAP feature importance

Run standalone:  python -m app.engines.validation_engine
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from app.analyzers.dataset_loader import load_dataset
from app.config import METRICS_PATH
from app.engines.shap_engine import global_importance
from app.models.schemas import (
    ConfusionMatrix,
    MetricsResponse,
    ModelMetrics,
    PrecisionAtK,
)


def _precision_at_k(y_true: np.ndarray, proba: np.ndarray, k: int) -> PrecisionAtK:
    k = min(k, len(proba))
    top = np.argsort(proba)[::-1][:k]
    hits = int(y_true[top].sum())
    return PrecisionAtK(k=k, precision=round(hits / k, 4) if k else 0.0, true_mules_in_top_k=hits)


def _ks_statistic(y_true: np.ndarray, proba: np.ndarray) -> float:
    fpr, tpr, _ = roc_curve(y_true, proba)
    return float(np.max(tpr - fpr))


def compute_model_metrics(trained_model, X_full, y_full) -> ModelMetrics:
    te = np.asarray(trained_model.test_index, dtype=int)
    X_te = X_full.iloc[te]
    y_te = y_full.iloc[te].values

    proba = trained_model.predict_proba(X_te)
    thr = trained_model.threshold
    pred = (proba >= thr).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_te, pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    # Feature importance over a capped sample (SHAP is the expensive part).
    sample = X_te if len(X_te) <= 400 else X_te.sample(400, random_state=0)
    importance = global_importance(trained_model, sample, top_n=20)

    return ModelMetrics(
        model_name=trained_model.name,
        includes_f3912=trained_model.include_f3912,
        pr_auc=round(float(average_precision_score(y_te, proba)), 4),
        roc_auc=round(float(roc_auc_score(y_te, proba)), 4),
        precision=round(float(precision_score(y_te, pred, zero_division=0)), 4),
        recall=round(float(recall_score(y_te, pred, zero_division=0)), 4),
        f1=round(float(f1_score(y_te, pred, zero_division=0)), 4),
        ks_statistic=round(_ks_statistic(y_te, proba), 4),
        accuracy=round(float((pred == y_te).mean()), 4),
        false_positive_rate=round(float(fpr), 4),
        confusion_matrix=ConfusionMatrix(tp=int(tp), fp=int(fp), tn=int(tn), fn=int(fn)),
        precision_at_k=[_precision_at_k(y_te, proba, 50), _precision_at_k(y_te, proba, 100)],
        threshold=round(float(thr), 4),
        feature_importance=importance,
    )


def compute_all(engine, dataset_path=None, save: bool = True) -> MetricsResponse:
    ds = load_dataset(dataset_path) if dataset_path else load_dataset()
    resp = MetricsResponse()
    if engine.model_a is not None:
        resp.model_a = compute_model_metrics(engine.model_a, ds.X, ds.y)
    if engine.model_b is not None:
        resp.model_b = compute_model_metrics(engine.model_b, ds.X, ds.y)
    if save:
        METRICS_PATH.write_text(resp.model_dump_json(indent=2), encoding="utf-8")
    return resp


def load_cached_metrics() -> MetricsResponse | None:
    if METRICS_PATH.exists():
        return MetricsResponse.model_validate_json(METRICS_PATH.read_text(encoding="utf-8"))
    return None


def _selftest() -> None:
    from app.engines.model_engine import ModelEngine

    print("== validation_engine self-test ==")
    eng = ModelEngine()
    if not eng.load():
        print("models not trained — run model_engine first.")
        return
    resp = compute_all(eng)
    for m in (resp.model_a, resp.model_b):
        if not m:
            continue
        cm = m.confusion_matrix
        print(f"\n{m.model_name}  (F3912={'in' if m.includes_f3912 else 'out'})")
        print(f"  PR-AUC (PRIMARY) : {m.pr_auc}")
        print(f"  ROC-AUC          : {m.roc_auc}")
        print(f"  P / R / F1       : {m.precision} / {m.recall} / {m.f1}")
        print(f"  KS statistic     : {m.ks_statistic}")
        print(f"  threshold        : {m.threshold}")
        print(f"  confusion        : TP={cm.tp} FP={cm.fp} TN={cm.tn} FN={cm.fn}")
        print(f"  P@50 / P@100     : {m.precision_at_k[0].precision} / {m.precision_at_k[1].precision}")
        print(f"  accuracy (deprio): {m.accuracy}")
    print(f"\nsaved -> {METRICS_PATH.name}")
    print("OK")


if __name__ == "__main__":
    _selftest()
