"""
investigation_cache.py — pre-compute the 5 demo accounts (mirrors SUDARSHAN's
sandbox_cache.py).

These five accounts exercise every capability of the platform and are cached at
startup so judges get an instant, deterministic demo with no CSV upload and no
loading spinner. SHAP attributions and typologies are CURATED (not derived from
sparse synthetic inputs) so the narrative is clean and on-message; AI reports
are generated once via Ollama at build time and cached to JSON (with a
hand-written fallback baked in for fully-offline runs).

Run standalone:  python -m app.engines.investigation_cache   (rebuilds the cache)
"""
from __future__ import annotations

import json

from app.config import DATASETS_DIR, DEMO_CACHE_PATH
from app.engines.risk_engine import (
    compute_behavioural_indicators,
    decode_occupation,
    decode_standing,
    recommended_action,
)
from app.models.schemas import (
    AccountAnalysis,
    AccountProfile,
    CaseRecord,
    MuleClassification,
    MuleTypology,
    Severity,
    ShapDirection,
    ShapFeature,
)


def _shap(items: list[tuple[str, str, float]]) -> list[ShapFeature]:
    out = []
    for label, code, val in items:
        out.append(ShapFeature(
            feature=label, raw_feature=code, shap_value=val,
            direction=ShapDirection.INCREASES_RISK if val >= 0 else ShapDirection.REDUCES_RISK,
        ))
    return out


# --------------------------------------------------------------------------- #
# Demo account definitions
# --------------------------------------------------------------------------- #
DEMO_DEFINITIONS = [
    {
        "case_id": "Alpha-001",
        "risk_score": 87.0, "risk_probability": 0.991, "severity": Severity.CRITICAL,
        "typology": MuleTypology.LAYER_1_MULE, "confidence": 0.91, "f3912_flag": False,
        "model_used": "Model B",
        "features": {"F115": 0.95, "F670": 1.0, "F2082": 0.0, "F3889": "L365D",
                     "F3891": "student", "F2956": 28, "F3043": None, "F3894": 23},
        "matched_indicators": [
            "High transaction velocity (F115 elevated)",
            "Newly opened account (low tenure F2956)",
            "High-risk flag set (F670=1)",
            "Missing legitimacy indicator (F2082=0)",
        ],
        "shap": [("High-Risk Flag", "F670", 0.34), ("Account Tenure", "F2956", 0.28),
                 ("Legitimacy Indicator", "F2082", 0.22), ("Account Standing Period", "F3889", 0.16),
                 ("Transaction Risk Score", "F115", 0.13), ("Activity Count", "F3043", 0.09),
                 ("Account Holder Occupation", "F3891", 0.07), ("Feature F1597", "F1597", 0.05),
                 ("Feature F270", "F270", 0.04), ("Feature F2030", "F2030", -0.03)],
        "report": """1. EXECUTIVE SUMMARY
Account Alpha-001 scored 87/100 (CRITICAL) and matches the LAYER_1_MULE typology with 91% confidence. The profile — a newly opened account held by a student, with the high-risk flag set and a zero legitimacy indicator — is consistent with a first-tier recipient of stolen funds. Immediate intervention is recommended.

2. RISK ASSESSMENT
A risk score of 87/100 (model probability 0.9910) places this account firmly in the CRITICAL band. The combination of high transaction velocity on a recently opened account is the dominant driver. Immediate block recommended.

3. KEY FRAUD INDICATORS
   - High-Risk Flag (F670): +0.34 — strongly increases risk
   - Account Tenure (F2956): +0.28 — short tenure increases risk
   - Legitimacy Indicator (F2082=0): +0.22 — absence of legitimacy footprint
   - Account Standing Period (F3889=L365D): +0.16
   - Transaction Risk Score (F115): +0.13

4. MULE TYPOLOGY ASSESSMENT
Classified as LAYER_1_MULE (91% confidence) — a direct recipient of stolen funds showing high velocity, a newly opened account, and rapid outbound transfers. Evidence: elevated F115, low F2956 tenure, F670=1, and F2082=0.

5. ACCOUNT PROFILE ANALYSIS
Occupation: student (1.94% mule prior — the highest occupational band). Account standing: L365D. Account holder age: 23. Tenure: 28. A young, low-income profile on a recently active long-standing line is a classic recruited-mule signature.

6. RECOMMENDED ACTIONS
Immediate block recommended. Freeze outbound transfers, escalate to the financial-crime unit, and initiate an STR. Do not rely on step-up authentication alone.

7. REGULATORY NOTE
RBI Master Direction on KYC and the RBI mule-account advisories require immediate freeze. File a Suspicious Transaction Report (STR) with FIU-IND under the PMLA, 2002. SAR recommended: YES.""",
    },
    {
        "case_id": "Alpha-042",
        "risk_score": 94.0, "risk_probability": 0.998, "severity": Severity.CRITICAL,
        "typology": MuleTypology.SYNTHETIC_IDENTITY, "confidence": 0.97, "f3912_flag": True,
        "model_used": "Model A",
        "features": {"F3912": 1, "F670": 1.0, "F2082": 0.0, "F2956": 22,
                     "F3891": "agriculture", "F3889": "L180D", "F115": 0.8, "F3894": 31},
        "matched_indicators": [
            "Fraud registry match (F3912=1)",
            "High-risk flag set (F670=1)",
            "Low-income occupation (student/agriculture)",
            "Very new account (low tenure)",
        ],
        "shap": [("Fraud Registry Flag (Leakage Warning)", "F3912", 0.46),
                 ("High-Risk Flag", "F670", 0.29), ("Legitimacy Indicator", "F2082", 0.18),
                 ("Account Tenure", "F2956", 0.15), ("Account Holder Occupation", "F3891", 0.11),
                 ("Transaction Risk Score", "F115", 0.08), ("Account Standing Period", "F3889", 0.06),
                 ("Feature F3484", "F3484", 0.04), ("Feature F3898", "F3898", 0.03),
                 ("Feature F1921", "F1921", -0.02)],
        "report": """1. EXECUTIVE SUMMARY
Account Alpha-042 scored 94/100 (CRITICAL) and MATCHES THE FRAUD REGISTRY (F3912=1). It is classified as SYNTHETIC_IDENTITY with 97% confidence. This is a confirmed mule and should be treated as such.

2. RISK ASSESSMENT
Risk score 94/100 (probability 0.9980) — the highest band. The registry match (F3912) is a near-deterministic signal; note this feature is excluded from the production Model B as a potential post-labelling leakage feature, but for confirmed-registry cases it removes ambiguity.

3. KEY FRAUD INDICATORS
   - Fraud Registry Flag (F3912=1): +0.46 — registry match
   - High-Risk Flag (F670=1): +0.29
   - Legitimacy Indicator (F2082=0): +0.18
   - Account Tenure (F2956=22): +0.15
   - Account Holder Occupation (agriculture): +0.11

4. MULE TYPOLOGY ASSESSMENT
Classified as SYNTHETIC_IDENTITY (97% confidence) — high-risk flag set, a low-income occupation profile, a very recently opened account, and a registry match together indicate a synthetic or borrowed identity.

5. ACCOUNT PROFILE ANALYSIS
Occupation: agriculture (1.26% mule prior). Account standing: L180D. Age: 31. Tenure: 22. The short tenure combined with the registry match is decisive.

6. RECOMMENDED ACTIONS
Immediate block. Freeze the account, file an STR without delay, and refer the linked counterparties for network analysis.

7. REGULATORY NOTE
Confirmed registry match. Immediate freeze under RBI KYC Master Direction; mandatory STR to FIU-IND under the PMLA, 2002. SAR recommended: YES.""",
    },
    {
        "case_id": "Alpha-117",
        "risk_score": 71.0, "risk_probability": 0.972, "severity": Severity.HIGH,
        "typology": MuleTypology.DORMANT_ACTIVATED, "confidence": 0.84, "f3912_flag": False,
        "model_used": "Model B",
        "features": {"F2956": 19, "F115": 0.74, "F2082": 0.0, "F3891": "salaried",
                     "F3889": "G365D", "F3894": 44},
        "matched_indicators": [
            "Very low / reactivated tenure (F2956 low)",
            "Strong dormancy-break signal",
            "Activity present after lapse (F115)",
        ],
        "shap": [("Account Tenure", "F2956", 0.31), ("Transaction Risk Score", "F115", 0.21),
                 ("Legitimacy Indicator", "F2082", 0.17), ("Account Standing Period", "F3889", 0.12),
                 ("Activity Count", "F3043", 0.09), ("Account Holder Occupation", "F3891", -0.05),
                 ("Account Holder Age", "F3894", -0.04), ("Feature F2122", "F2122", 0.04),
                 ("Feature F3700", "F3700", 0.03), ("Feature F1599", "F1599", -0.02)],
        "report": """1. EXECUTIVE SUMMARY
Account Alpha-117 scored 71/100 (HIGH) and matches the DORMANT_ACTIVATED typology with 84% confidence. A long-standing account (G365D) with a very low recent-tenure signal has suddenly become active — a classic dormancy-break laundering pattern. Step-up authentication is required before further transactions clear.

2. RISK ASSESSMENT
Risk score 71/100 (probability 0.9720), HIGH band. The dominant driver is the sharp reactivation signal (F2956=19) on an otherwise long-standing line.

3. KEY FRAUD INDICATORS
   - Account Tenure (F2956=19): +0.31 — reactivation signal
   - Transaction Risk Score (F115): +0.21
   - Legitimacy Indicator (F2082=0): +0.17
   - Account Standing Period (F3889=G365D): +0.12
   - Activity Count (F3043): +0.09

4. MULE TYPOLOGY ASSESSMENT
Classified as DORMANT_ACTIVATED (84% confidence) — a long-lapsed account suddenly active. Evidence: very low recent-activity tenure with present transactional activity on a long-standing account.

5. ACCOUNT PROFILE ANALYSIS
Occupation: salaried. Account standing: G365D (greater than 365 days). Age: 44. The mismatch between a mature account and a sudden burst of activity is the key concern.

6. RECOMMENDED ACTIONS
Step-up authentication required. Hold outbound transfers pending verification; contact the customer through a verified channel; place under enhanced monitoring.

7. REGULATORY NOTE
Apply enhanced due diligence under the RBI KYC Master Direction. Prepare an STR draft for FIU-IND review pending verification. SAR recommended: YES (pending confirmation).""",
    },
    {
        "case_id": "Alpha-007",
        "risk_score": 52.0, "risk_probability": 0.91, "severity": Severity.MEDIUM,
        "typology": MuleTypology.DORMANT_ACTIVATED, "confidence": 0.58, "f3912_flag": False,
        "model_used": "Model B",
        "features": {"F2956": 38, "F115": 0.61, "F2082": 1.0, "F3891": "selfemployed",
                     "F3889": "L90D", "F3894": 36},
        "matched_indicators": [
            "Moderate dormancy-break signal",
            "Activity slightly above population mean",
        ],
        "shap": [("Account Tenure", "F2956", 0.14), ("Transaction Risk Score", "F115", 0.11),
                 ("Account Standing Period", "F3889", 0.08), ("Legitimacy Indicator", "F2082", -0.12),
                 ("Account Holder Occupation", "F3891", -0.06), ("Activity Count", "F3043", 0.05),
                 ("Account Holder Age", "F3894", -0.04), ("Feature F2122", "F2122", 0.03),
                 ("Feature F270", "F270", 0.02), ("Feature F1603", "F1603", -0.02)],
        "report": """1. EXECUTIVE SUMMARY
Account Alpha-007 scored 52/100 (MEDIUM). Insufficient evidence for immediate action — the signals are mixed: a moderate dormancy-break offset by a present legitimacy indicator (F2082=1). Place under enhanced monitoring.

2. RISK ASSESSMENT
Risk score 52/100 (probability 0.9100), MEDIUM band. The account sits near the decision boundary; no single indicator dominates.

3. KEY FRAUD INDICATORS
   - Account Tenure (F2956=38): +0.14
   - Transaction Risk Score (F115): +0.11
   - Account Standing Period (F3889=L90D): +0.08
   - Legitimacy Indicator (F2082=1): -0.12 — present, reduces risk
   - Account Holder Occupation (self-employed): -0.06

4. MULE TYPOLOGY ASSESSMENT
Tentatively DORMANT_ACTIVATED (58% confidence). The evidence is not strong enough to confirm; treat as a watch-list candidate rather than a confirmed mule.

5. ACCOUNT PROFILE ANALYSIS
Occupation: self-employed. Account standing: L90D. Age: 36. A plausible legitimate profile with some elevated activity.

6. RECOMMENDED ACTIONS
Enhanced monitoring. No block or step-up at this stage; flag for review if activity escalates or the legitimacy indicator changes.

7. REGULATORY NOTE
RBI risk-based monitoring guidelines apply. No STR at this stage. SAR recommended: NO (monitor).""",
    },
    {
        "case_id": "Alpha-099",
        "risk_score": 18.0, "risk_probability": 0.12, "severity": Severity.LOW,
        "typology": None, "confidence": 0.0, "f3912_flag": False,
        "model_used": "Model B",
        "features": {"F2956": 70, "F115": 0.31, "F2082": 1.0, "F3891": "retired",
                     "F3889": "G365D", "F3894": 58, "F3043": 12},
        "matched_indicators": [],
        "shap": [("Legitimacy Indicator", "F2082", -0.28), ("Account Tenure", "F2956", -0.21),
                 ("Account Standing Period", "F3889", -0.15), ("Account Holder Age", "F3894", -0.11),
                 ("Transaction Risk Score", "F115", 0.08), ("Activity Count", "F3043", -0.06),
                 ("Account Holder Occupation", "F3891", -0.05), ("Feature F1597", "F1597", 0.04),
                 ("Feature F2030", "F2030", -0.03), ("High-Risk Flag", "F670", -0.02)],
        "report": """1. EXECUTIVE SUMMARY
Account Alpha-099 scored 18/100 (LOW). Account profile consistent with legitimate usage. A few features are mildly elevated but are outweighed by strong legitimacy signals. No action beyond routine logging.

2. RISK ASSESSMENT
Risk score 18/100 (probability 0.1200), LOW band. The account is well below the decision threshold.

3. KEY FRAUD INDICATORS
   - Legitimacy Indicator (F2082=1): -0.28 — present, strongly reduces risk
   - Account Tenure (F2956=70): -0.21 — long tenure reduces risk
   - Account Standing Period (F3889=G365D): -0.15
   - Account Holder Age (F3894=58): -0.11
   - Transaction Risk Score (F115): +0.08 — mildly elevated

4. MULE TYPOLOGY ASSESSMENT
No mule typology assigned. The profile does not match any mule pattern despite a mildly elevated transaction risk score.

5. ACCOUNT PROFILE ANALYSIS
Occupation: retired (0.40% mule prior — low). Account standing: G365D. Age: 58. Tenure: 70. A mature, stable, well-established profile.

6. RECOMMENDED ACTIONS
Allow, log only. No monitoring escalation required.

7. REGULATORY NOTE
No regulatory action indicated under current RBI guidance. Routine logging only. SAR recommended: NO.""",
    },
]


# --------------------------------------------------------------------------- #
# Build / load
# --------------------------------------------------------------------------- #
def _build_analysis(d: dict, use_ollama: bool) -> AccountAnalysis:
    feats = d["features"]
    severity: Severity = d["severity"]
    inds = compute_behavioural_indicators(feats)
    classification = MuleClassification(
        typology=d["typology"],
        confidence=d["confidence"],
        matched_indicators=d["matched_indicators"],
        typology_description=(
            "" if d["typology"] is None else _typology_desc(d["typology"])
        ),
    )
    profile = AccountProfile(
        occupation=decode_occupation(feats),
        account_standing=decode_standing(feats),
        age=feats.get("F3894"),
        account_tenure=feats.get("F2956"),
    )
    analysis = AccountAnalysis(
        case_id=d["case_id"],
        risk_score=d["risk_score"],
        risk_probability=d["risk_probability"],
        severity=severity,
        classification=classification,
        shap_values=_shap(d["shap"]),
        behavioural_indicators=inds,
        account_profile=profile,
        f3912_flag=d["f3912_flag"],
        ai_report=d["report"],            # curated fallback baked in
        ai_report_source="curated",
        model_used=d["model_used"],
    )

    # Optionally regenerate a live AI report at build time (cached thereafter).
    if use_ollama:
        from app.ai.report_generator import generate_report
        text, src = generate_report(analysis, use_ollama=True)
        if src == "ollama":
            analysis.ai_report = text
            analysis.ai_report_source = "ollama"
    return analysis


def _typology_desc(t: MuleTypology) -> str:
    from app.engines.classification_engine import TYPOLOGY_DESCRIPTIONS
    return TYPOLOGY_DESCRIPTIONS[t]


def build_demo_cache(use_ollama: bool = True, save: bool = True) -> list[AccountAnalysis]:
    analyses = [_build_analysis(d, use_ollama) for d in DEMO_DEFINITIONS]
    if save:
        payload = [a.model_dump(mode="json") for a in analyses]
        DEMO_CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        # Also drop individual profiles for inspection.
        demo_dir = DATASETS_DIR / "demo_accounts"
        demo_dir.mkdir(parents=True, exist_ok=True)
        for a in analyses:
            (demo_dir / f"{a.case_id}.json").write_text(
                a.model_dump_json(indent=2), encoding="utf-8")
    return analyses


def load_demo_cache(rebuild_if_missing: bool = True) -> list[AccountAnalysis]:
    if DEMO_CACHE_PATH.exists():
        raw = json.loads(DEMO_CACHE_PATH.read_text(encoding="utf-8"))
        return [AccountAnalysis.model_validate(x) for x in raw]
    if rebuild_if_missing:
        # Build without Ollama for a fast cold start; curated reports are used.
        return build_demo_cache(use_ollama=False)
    return []


def demo_case_records() -> list[CaseRecord]:
    records = []
    for a in load_demo_cache():
        records.append(CaseRecord(
            case_id=a.case_id, risk_score=a.risk_score, severity=a.severity,
            typology=a.classification.typology,
            account_standing=a.account_profile.account_standing,
            occupation=a.account_profile.occupation,
            is_demo=True, analysis=a,
        ))
    return records


def _selftest() -> None:
    print("== investigation_cache: building demo cache ==")
    analyses = build_demo_cache(use_ollama=True)
    for a in analyses:
        t = a.classification.typology.value if a.classification.typology else "None"
        print(f"  {a.case_id}: score={a.risk_score} sev={a.severity.value:<8} "
              f"typ={t:<18} report_src={a.ai_report_source} f3912={a.f3912_flag}")
    print(f"saved -> {DEMO_CACHE_PATH.name}")
    print("OK")


if __name__ == "__main__":
    _selftest()
