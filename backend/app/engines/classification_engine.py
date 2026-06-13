"""
classification_engine.py — assign a flagged account to one of 5 mule typologies.

Rule-based classifier over the engineered feature profile + behavioural
indicators. Each typology is a weighted set of predicates; the account is
assigned the highest-scoring typology, with a confidence proportional to how
many of that typology's signals matched. Low-risk accounts (score < 40) are
returned with no typology (legitimate).

Typologies:
  LAYER_1_MULE        high velocity + new account + transfers out (direct recipient)
  PASS_THROUGH        near-zero F2082 + high cash-flow ratio (receive & forward)
  DORMANT_ACTIVATED   very low tenure / long-lapsed account suddenly active
  SYNTHETIC_IDENTITY  F670=1 + student/agriculture + very new account
  NETWORK_HUB         high F115 + complex counterparty spread (layering hub)

Run standalone:  python -m app.engines.classification_engine
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from app.engines.risk_engine import _num, decode_occupation, decode_standing
from app.models.schemas import MuleClassification, MuleTypology

MIN_RISK_FOR_TYPOLOGY = 40.0

TYPOLOGY_DESCRIPTIONS = {
    MuleTypology.LAYER_1_MULE:
        "Direct recipient of stolen funds — high transaction velocity on a newly "
        "opened account with rapid outbound transfers.",
    MuleTypology.PASS_THROUGH:
        "Funds received and almost immediately forwarded. Near-zero legitimacy "
        "footprint with a high cash-flow ratio.",
    MuleTypology.DORMANT_ACTIVATED:
        "A long-lapsed or very new account that has suddenly become active — a "
        "classic dormancy-break laundering pattern.",
    MuleTypology.SYNTHETIC_IDENTITY:
        "Likely synthetic / borrowed identity — high-risk flag set, low-income "
        "occupation profile, and a very recently opened account.",
    MuleTypology.NETWORK_HUB:
        "Central node in a layering network — high activity with a complex, wide "
        "counterparty spread routing funds across many accounts.",
}


@dataclass
class _Predicate:
    label: str
    test: Callable[[dict, dict], bool]   # (features, ind_by_key) -> bool
    weight: float = 1.0


def _ind(ind_by_key: dict, key: str) -> float:
    bi = ind_by_key.get(key)
    return bi.value if bi is not None else 0.0


# --------------------------------------------------------------------------- #
# Per-typology predicate sets
# --------------------------------------------------------------------------- #
_RULES: dict[MuleTypology, list[_Predicate]] = {
    MuleTypology.LAYER_1_MULE: [
        _Predicate("High transaction velocity (F115 elevated)",
                   lambda f, i: _ind(i, "activity_flag") >= 0.7, 1.0),
        _Predicate("Newly opened account (low tenure F2956)",
                   lambda f, i: _ind(i, "dormancy_signal") >= 0.55, 1.0),
        _Predicate("High-risk flag set (F670=1)",
                   lambda f, i: _ind(i, "high_risk_flag") >= 0.9, 0.8),
        _Predicate("Missing legitimacy indicator (F2082=0)",
                   lambda f, i: _ind(i, "legitimacy_gap") >= 0.9, 0.8),
    ],
    MuleTypology.PASS_THROUGH: [
        _Predicate("Near-zero legitimacy footprint (F2082=0)",
                   lambda f, i: _ind(i, "legitimacy_gap") >= 0.9, 1.2),
        _Predicate("High cash-flow ratio (F1692 elevated)",
                   lambda f, i: (_num(f, "F1692") or 0) >= 0.6, 1.0),
        _Predicate("Elevated activity (F115)",
                   lambda f, i: _ind(i, "activity_flag") >= 0.6, 0.6),
    ],
    MuleTypology.DORMANT_ACTIVATED: [
        _Predicate("Very low / reactivated tenure (F2956 low)",
                   lambda f, i: (_num(f, "F2956") is not None and _num(f, "F2956") <= 25), 1.4),
        _Predicate("Strong dormancy-break signal",
                   lambda f, i: _ind(i, "dormancy_signal") >= 0.65, 1.0),
        _Predicate("Activity present after lapse (F115)",
                   lambda f, i: _ind(i, "activity_flag") >= 0.5, 0.7),
    ],
    MuleTypology.SYNTHETIC_IDENTITY: [
        _Predicate("High-risk flag set (F670=1)",
                   lambda f, i: _ind(i, "high_risk_flag") >= 0.9, 1.2),
        _Predicate("Low-income occupation (student/agriculture)",
                   lambda f, i: decode_occupation(f) in {"student", "agriculture"}, 1.2),
        _Predicate("Very new account (low tenure)",
                   lambda f, i: (_num(f, "F2956") is not None and _num(f, "F2956") <= 35), 1.0),
        _Predicate("Fraud registry match (F3912=1)",
                   lambda f, i: (_num(f, "F3912") or 0) >= 1, 0.8),
    ],
    MuleTypology.NETWORK_HUB: [
        _Predicate("High activity (F115)",
                   lambda f, i: _ind(i, "activity_flag") >= 0.75, 1.0),
        _Predicate("Wide inbound counterparty spread (F527)",
                   lambda f, i: (_num(f, "F527") or 0) >= 0.6, 1.0),
        _Predicate("Wide outbound counterparty spread (F531)",
                   lambda f, i: (_num(f, "F531") or 0) >= 0.6, 1.0),
    ],
}


def classify(
    features: dict[str, Any],
    behavioural_indicators: list,
    risk_score: float,
) -> MuleClassification:
    """Return the best-matching typology with confidence and matched evidence."""
    if risk_score < MIN_RISK_FOR_TYPOLOGY:
        return MuleClassification(
            typology=None, confidence=0.0, matched_indicators=[],
            typology_description="Profile consistent with legitimate usage — no mule typology assigned.",
        )

    ind_by_key = {bi.key: bi for bi in behavioural_indicators}

    best: Optional[MuleTypology] = None
    best_conf = 0.0
    best_matches: list[str] = []

    for typ, preds in _RULES.items():
        total_w = sum(p.weight for p in preds)
        matched = [p for p in preds if p.test(features, ind_by_key)]
        matched_w = sum(p.weight for p in matched)
        conf = matched_w / total_w if total_w else 0.0
        if conf > best_conf:
            best_conf = conf
            best = typ
            best_matches = [p.label for p in matched]

    if best is None or best_conf == 0.0:
        # Risk is elevated but no typology pattern dominates — default to the
        # most generic recipient typology with low confidence.
        best = MuleTypology.LAYER_1_MULE
        best_conf = 0.3
        best_matches = ["Elevated model risk score without a dominant typology signature"]

    # Blend rule confidence with the model risk score so a CRITICAL account
    # never reports an implausibly low confidence.
    blended = round(min(0.99, 0.6 * best_conf + 0.4 * (risk_score / 100.0)), 2)

    return MuleClassification(
        typology=best,
        confidence=blended,
        matched_indicators=best_matches,
        typology_description=TYPOLOGY_DESCRIPTIONS[best],
    )


def _selftest() -> None:
    from app.engines.risk_engine import compute_behavioural_indicators

    print("== classification_engine self-test ==")
    cases = {
        "Alpha-001 (layer-1)": ({"F115": 0.95, "F670": 1.0, "F2082": 0.0,
                                  "F3889": "L365D", "F3891": "student", "F2956": 28}, 87),
        "Alpha-117 (dormant)": ({"F115": 0.7, "F2082": 0.0, "F2956": 19,
                                 "F3891": "salaried"}, 71),
        "Alpha-042 (synthetic)": ({"F670": 1.0, "F3912": 1, "F2956": 22,
                                   "F3891": "agriculture", "F115": 0.8}, 94),
        "Alpha-099 (legit)": ({"F115": 0.3, "F2082": 1.0, "F2956": 70,
                               "F3891": "salaried"}, 18),
    }
    for name, (feat, score) in cases.items():
        inds = compute_behavioural_indicators(feat)
        c = classify(feat, inds, score)
        t = c.typology.value if c.typology else "None"
        print(f"  {name:<24} -> {t:<18} conf={c.confidence}  matched={len(c.matched_indicators)}")
    print("OK")


if __name__ == "__main__":
    _selftest()
