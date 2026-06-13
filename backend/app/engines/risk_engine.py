"""
risk_engine.py — probability -> 0-100 risk score, severity bands, and the
8 behavioural risk indicators.

The risk score is anchored on the model's TUNED threshold so the score is
interpretable as distance from the decision boundary:
    prob == threshold  -> 60  (HIGH/MEDIUM boundary)
    prob == 1.0        -> 100
    prob == 0.0        -> 0
This keeps scores spread across severity bands even when the imbalance-tuned
model produces sharply peaked probabilities.

The 8 behavioural indicators are domain-informed proxies mapped from the
closest available BOI features (each documented inline with its provenance).

Run standalone:  python -m app.engines.risk_engine
"""
from __future__ import annotations

from typing import Any, Optional

from app.config import (
    F3889_ORDER,
    F3891_CATEGORIES,
    OCCUPATION_MULE_RATE,
    SEVERITY_BANDS,
    STANDING_MULE_RATE,
)
from app.models.schemas import BehaviouralIndicator, Severity


# --------------------------------------------------------------------------- #
# Feature access helpers (tolerate raw strings or encoded ints)
# --------------------------------------------------------------------------- #
def _num(features: dict, code: str) -> Optional[float]:
    v = features.get(code, None)
    if v is None:
        return None
    try:
        f = float(v)
        return f
    except (TypeError, ValueError):
        return None


def decode_standing(features: dict) -> Optional[str]:
    """F3889 -> account-standing label (handles raw label or encoded int)."""
    v = features.get("F3889", None)
    if v is None:
        return None
    if isinstance(v, str) and v.strip().upper() in F3889_ORDER:
        return v.strip().upper()
    try:
        i = int(float(v))
        if 0 <= i < len(F3889_ORDER):
            return F3889_ORDER[i]
    except (TypeError, ValueError):
        return None
    return None


def decode_occupation(features: dict) -> Optional[str]:
    """F3891 -> occupation label (handles raw label or encoded int)."""
    v = features.get("F3891", None)
    if v is None:
        return None
    if isinstance(v, str) and v.strip().lower() in F3891_CATEGORIES:
        return v.strip().lower()
    try:
        i = int(float(v))
        if 0 <= i < len(F3891_CATEGORIES):
            return F3891_CATEGORIES[i]
    except (TypeError, ValueError):
        return None
    return None


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


# --------------------------------------------------------------------------- #
# Score & severity
# --------------------------------------------------------------------------- #
def score_from_proba(prob: float, threshold: float = 0.5) -> float:
    """Threshold-anchored mapping of probability -> 0-100 risk score."""
    threshold = min(max(threshold, 1e-6), 1 - 1e-6)
    if prob >= threshold:
        score = 60.0 + 40.0 * (prob - threshold) / (1.0 - threshold)
    else:
        score = 60.0 * (prob / threshold)
    return round(max(0.0, min(100.0, score)), 1)


def severity_for(score: float) -> Severity:
    for lo, hi, name, _action in SEVERITY_BANDS:
        if lo <= score <= hi:
            return Severity(name)
    return Severity.LOW


def recommended_action(severity: Severity) -> str:
    for _lo, _hi, name, action in SEVERITY_BANDS:
        if name == severity.value:
            return action
    return "Allow, log only"


# --------------------------------------------------------------------------- #
# The 8 behavioural risk indicators
# --------------------------------------------------------------------------- #
def compute_behavioural_indicators(features: dict[str, Any]) -> list[BehaviouralIndicator]:
    inds: list[BehaviouralIndicator] = []

    # 1. Dormancy Signal — F2956 account-age proxy (mule median 41 vs legit 64).
    tenure = _num(features, "F2956")
    dormancy = _clip01((80.0 - tenure) / 80.0) if tenure is not None else 0.5
    inds.append(BehaviouralIndicator(
        key="dormancy_signal", label="Dormancy Signal", value=round(dormancy, 3),
        raw_value=tenure, source_feature="F2956",
        description="Low account tenure / dormancy-break signal. Mule median 41 vs legit 64.",
    ))

    # 2. Activity Flag — F115 (mules mean 0.72 vs legit 0.59).
    f115 = _num(features, "F115")
    activity = _clip01(f115) if f115 is not None else 0.5
    inds.append(BehaviouralIndicator(
        key="activity_flag", label="Activity Flag", value=round(activity, 3),
        raw_value=f115, source_feature="F115",
        description="Elevated transactional activity. Mules score ~22% higher (0.72 vs 0.59).",
    ))

    # 3. Legitimacy Gap — F2082 (ALL mule accounts have F2082 = 0).
    f2082 = _num(features, "F2082")
    legit_gap = 1.0 if (f2082 is not None and f2082 == 0) else (0.2 if f2082 is not None else 0.6)
    inds.append(BehaviouralIndicator(
        key="legitimacy_gap", label="Legitimacy Gap", value=round(legit_gap, 3),
        raw_value=f2082, source_feature="F2082",
        description="Missing legitimacy indicator. Every confirmed mule has F2082 = 0.",
    ))

    # 4. Missingness Pattern — F3043 null (82.7% of mules missing vs 64% legit).
    f3043 = features.get("F3043", "__absent__")
    f3043_missing = (f3043 is None) or (f3043 == "__absent__")
    missingness = 0.85 if f3043_missing else 0.25
    inds.append(BehaviouralIndicator(
        key="missingness_pattern", label="Missingness Pattern", value=round(missingness, 3),
        raw_value=None if f3043_missing else _num(features, "F3043"), source_feature="F3043",
        description="Activity-count field absent. 82.7% of mules missing it vs 64% of legit.",
    ))

    # 5. High-Risk Flag — F670 (=1 -> 2.29% mule rate, 2.6x average).
    f670 = _num(features, "F670")
    high_risk = 1.0 if (f670 is not None and f670 >= 1) else (0.1 if f670 is not None else 0.4)
    inds.append(BehaviouralIndicator(
        key="high_risk_flag", label="High-Risk Flag", value=round(high_risk, 3),
        raw_value=f670, source_feature="F670",
        description="F670 = 1 carries a 2.29% mule rate (2.6x the population average).",
    ))

    # 6. Risk Score — F115 normalised (kept distinct as the model-facing risk proxy).
    risk_proxy = _clip01(f115) if f115 is not None else 0.5
    inds.append(BehaviouralIndicator(
        key="risk_score", label="Risk Score", value=round(risk_proxy, 3),
        raw_value=f115, source_feature="F115",
        description="Normalised transaction risk score derived from F115.",
    ))

    # 7. Occupation Risk — F3891 (student 1.94%, agriculture 1.26%, housewife 0.45%).
    occ = decode_occupation(features)
    occ_rate = OCCUPATION_MULE_RATE.get(occ, 0.009) if occ else 0.009
    occ_norm = _clip01(occ_rate / 0.02)   # 0.02 ~= top occupation rate
    inds.append(BehaviouralIndicator(
        key="occupation_risk", label="Occupation Risk", value=round(occ_norm, 3),
        raw_value=None, source_feature="F3891",
        description=f"Occupation '{occ or 'unknown'}' carries a {occ_rate*100:.2f}% mule prior.",
    ))

    # 8. Account Standing — F3889 (L7D/L14D = 0% mule, L365D = 1.26% mule).
    standing = decode_standing(features)
    standing_rate = STANDING_MULE_RATE.get(standing, 0.006) if standing else 0.006
    standing_norm = _clip01(standing_rate / 0.0126)
    inds.append(BehaviouralIndicator(
        key="account_standing", label="Account Standing", value=round(standing_norm, 3),
        raw_value=None, source_feature="F3889",
        description=f"Standing '{standing or 'unknown'}' carries a {standing_rate*100:.2f}% mule prior.",
    ))

    return inds


def assess(prob: float, features: dict, threshold: float = 0.5) -> dict:
    """Convenience bundle: score + severity + action + indicators."""
    score = score_from_proba(prob, threshold)
    sev = severity_for(score)
    return {
        "risk_score": score,
        "risk_probability": round(prob, 6),
        "severity": sev,
        "recommended_action": recommended_action(sev),
        "behavioural_indicators": compute_behavioural_indicators(features),
    }


def _selftest() -> None:
    print("== risk_engine self-test ==")
    for p, thr in [(0.99, 0.8), (0.8, 0.8), (0.4, 0.8), (0.05, 0.8)]:
        s = score_from_proba(p, thr)
        print(f"  prob={p:<5} thr={thr} -> score={s:<6} severity={severity_for(s).value}")
    demo = {"F115": 0.95, "F670": 1.0, "F2082": 0.0, "F3889": "L365D",
            "F3891": "student", "F2956": 28, "F3043": None}
    print("demo Alpha-001 indicators:")
    for ind in compute_behavioural_indicators(demo):
        print(f"   {ind.label:<22} {ind.value:>5}  ({ind.source_feature})")
    print("OK")


if __name__ == "__main__":
    _selftest()
