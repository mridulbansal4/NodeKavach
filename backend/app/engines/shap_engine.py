"""
shap_engine.py — per-prediction explainability via SHAP TreeExplainer.

For any account it returns the top-N features ranked by absolute SHAP
contribution, each mapped to a human-readable name with a risk direction:
    shap_value > 0  -> increases_risk   (red, extends right in the waterfall)
    shap_value < 0  -> reduces_risk     (green, extends left)

Also exposes global feature importance (mean |SHAP| over a sample) used by the
Metrics page feature-importance chart.

Run standalone:  python -m app.engines.shap_engine
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import shap

from app.config import feature_label
from app.models.schemas import ShapDirection, ShapFeature

# Cache one TreeExplainer per booster object (keyed by id()).
_EXPLAINERS: dict[int, Any] = {}


def _get_explainer(booster):
    key = id(booster)
    if key not in _EXPLAINERS:
        _EXPLAINERS[key] = shap.TreeExplainer(booster)
    return _EXPLAINERS[key]


def _to_2d_positive(shap_values) -> np.ndarray:
    """Normalise shap output to a 2D (n_samples, n_features) array for the
    positive class margin across SHAP/XGBoost versions."""
    sv = np.asarray(shap_values)
    if sv.ndim == 3:        # (n, features, classes) — take last class
        sv = sv[:, :, -1]
    return sv


def explain_row(trained_model, features: dict[str, Any], top_n: int = 10) -> list[ShapFeature]:
    """Top-N SHAP attributions for a single account."""
    fe = trained_model.feature_engineer
    row = pd.DataFrame([features])
    Xt = fe.transform(row)

    explainer = _get_explainer(trained_model.booster)
    sv = _to_2d_positive(explainer.shap_values(Xt.values))[0]

    cols = fe.selected_features
    order = np.argsort(np.abs(sv))[::-1][:top_n]

    out: list[ShapFeature] = []
    for idx in order:
        code = cols[idx]
        val = float(sv[idx])
        # The standing/occupation labels are already encoded; keep the F-code label.
        out.append(ShapFeature(
            feature=feature_label(code),
            raw_feature=code,
            shap_value=round(val, 4),
            direction=ShapDirection.INCREASES_RISK if val >= 0 else ShapDirection.REDUCES_RISK,
            feature_value=round(float(Xt.iloc[0, idx]), 4),
        ))
    return out


def global_importance(trained_model, X_sample: pd.DataFrame, top_n: int = 20) -> list[ShapFeature]:
    """Mean |SHAP| feature importance over a sample (for the Metrics chart)."""
    fe = trained_model.feature_engineer
    Xt = fe.transform(X_sample)
    explainer = _get_explainer(trained_model.booster)
    sv = _to_2d_positive(explainer.shap_values(Xt.values))
    mean_abs = np.abs(sv).mean(axis=0)
    mean_signed = sv.mean(axis=0)

    cols = fe.selected_features
    order = np.argsort(mean_abs)[::-1][:top_n]
    out: list[ShapFeature] = []
    for idx in order:
        code = cols[idx]
        out.append(ShapFeature(
            feature=feature_label(code),
            raw_feature=code,
            shap_value=round(float(mean_abs[idx]), 4),
            direction=ShapDirection.INCREASES_RISK if mean_signed[idx] >= 0 else ShapDirection.REDUCES_RISK,
            feature_value=None,
        ))
    return out


def _selftest() -> None:
    from app.engines.model_engine import ModelEngine

    print("== shap_engine self-test ==")
    eng = ModelEngine()
    if not eng.load():
        print("models not trained yet — run `python -m app.engines.model_engine` first.")
        return
    feats = {"F115": 0.95, "F670": 1.0, "F2082": 0.0, "F2956": 28,
             "F3889": 5, "F3891": 2}
    sv = explain_row(eng.model_b, feats, top_n=10)
    print("top SHAP features (Model B):")
    for s in sv:
        arrow = "+" if s.direction == ShapDirection.INCREASES_RISK else "-"
        print(f"   {arrow} {s.feature:<32} {s.shap_value:+.4f}  [{s.raw_feature}]")
    print("OK")


if __name__ == "__main__":
    _selftest()
