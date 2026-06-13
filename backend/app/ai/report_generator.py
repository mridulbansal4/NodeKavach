"""
report_generator.py — build the investigation-report prompt and render the
final 7-section narrative (via Ollama, with a deterministic structured
fallback when Ollama is unavailable).

The report always contains these EXACT sections:
  1. EXECUTIVE SUMMARY
  2. RISK ASSESSMENT
  3. KEY FRAUD INDICATORS
  4. MULE TYPOLOGY ASSESSMENT
  5. ACCOUNT PROFILE ANALYSIS
  6. RECOMMENDED ACTIONS
  7. REGULATORY NOTE

Run standalone:  python -m app.ai.report_generator
"""
from __future__ import annotations

from app.ai.ollama_client import CLIENT
from app.engines.risk_engine import recommended_action
from app.models.schemas import AccountAnalysis, Severity, ShapDirection

SYSTEM_PROMPT = (
    "You are an elite financial-crime intelligence analyst at Bank of India "
    "acting as an Investigator Copilot. You write concise, factual mule-account "
    "investigation reports. You specialize in explaining network topology, "
    "campaign-wide risk, and connected operation clusters. You never invent data; "
    "you reason only from the structured signals provided. Your tone is precise, "
    "professional, and decisive."
)

_RBI_NOTE = {
    Severity.CRITICAL: (
        "RBI Master Direction on KYC (2016, as amended) and the RBI mule-account "
        "advisories require immediate account freeze. File a Suspicious Transaction "
        "Report (STR) with FIU-IND under the PMLA, 2002. SAR recommended: YES."
    ),
    Severity.HIGH: (
        "Under the RBI KYC Master Direction, apply enhanced due diligence and "
        "step-up authentication. Prepare an STR draft for FIU-IND review. "
        "SAR recommended: YES (pending confirmation)."
    ),
    Severity.MEDIUM: (
        "RBI risk-based monitoring guidelines apply. Place under enhanced "
        "transaction monitoring; no STR at this stage. SAR recommended: NO (monitor)."
    ),
    Severity.LOW: (
        "No regulatory action indicated under current RBI guidance. Routine "
        "logging only. SAR recommended: NO."
    ),
}


# --------------------------------------------------------------------------- #
# Prompt construction
# --------------------------------------------------------------------------- #
def build_prompt(a: AccountAnalysis) -> str:
    top_shap = a.shap_values[:5]
    shap_lines = "\n".join(
        f"  - {s.feature} ({s.raw_feature}): SHAP {s.shap_value:+.3f} "
        f"({'increases' if s.direction == ShapDirection.INCREASES_RISK else 'reduces'} risk)"
        for s in top_shap
    ) or "  - (no SHAP attribution available)"

    matched = "\n".join(f"  - {m}" for m in a.classification.matched_indicators) or "  - none"
    typ = a.classification.typology.value if a.classification.typology else "None (legitimate profile)"
    p = a.account_profile

    return f"""Produce a mule-account investigation report for the account below.

STRUCTURED ANALYSIS
Case ID: {a.case_id}
Risk score: {a.risk_score}/100
Severity: {a.severity.value}
Model risk probability: {a.risk_probability:.4f}
Fraud-registry (F3912) match: {"YES" if a.f3912_flag else "no"}

Top SHAP fraud indicators:
{shap_lines}

Mule typology: {typ} (confidence {a.classification.confidence:.0%})
Matched typology evidence:
{matched}

Account profile:
  - Occupation: {p.occupation or "unknown"}
  - Account standing period: {p.account_standing or "unknown"}
  - Account holder age: {p.age if p.age is not None else "unknown"}
  - Account tenure: {p.account_tenure if p.account_tenure is not None else "unknown"}

INSTRUCTIONS
Write the report with EXACTLY these seven numbered sections and these exact
uppercase headers, in this order. Do not add or remove sections. Keep each
section tight (2-5 sentences or a short bullet list). Use plain professional
language a compliance officer can act on immediately.

1. EXECUTIVE SUMMARY
2. RISK ASSESSMENT
3. KEY FRAUD INDICATORS
4. MULE TYPOLOGY ASSESSMENT
5. ACCOUNT PROFILE ANALYSIS
6. RECOMMENDED ACTIONS
7. REGULATORY NOTE
"""


# --------------------------------------------------------------------------- #
# Deterministic fallback (no Ollama)
# --------------------------------------------------------------------------- #
def fallback_report(a: AccountAnalysis) -> str:
    p = a.account_profile
    typ = a.classification.typology.value if a.classification.typology else None
    action = recommended_action(a.severity)

    indicators = "\n".join(
        f"   - {s.feature} ({s.raw_feature}): {s.shap_value:+.3f} "
        f"{'increases' if s.direction == ShapDirection.INCREASES_RISK else 'reduces'} risk"
        for s in a.shap_values[:6]
    ) or "   - No SHAP attributions available."

    matched = "\n".join(f"   - {m}" for m in a.classification.matched_indicators) or "   - None matched."

    if typ:
        typ_block = (
            f"Classified as {typ} with {a.classification.confidence:.0%} confidence.\n"
            f"{a.classification.typology_description}\n"
            f"Supporting evidence:\n{matched}"
        )
    else:
        typ_block = (
            "No mule typology assigned. The account profile is consistent with "
            "legitimate usage despite the presence of some elevated features."
        )

    summary = (
        f"Account {a.case_id} scored {a.risk_score}/100 ({a.severity.value}). "
        + (f"It matches the {typ} mule typology and warrants action. "
           if typ else "It does not match a mule typology and appears legitimate. ")
        + ("This account matches the fraud registry (F3912) — treat as confirmed. "
           if a.f3912_flag else "")
    )

    return f"""1. EXECUTIVE SUMMARY
{summary}

2. RISK ASSESSMENT
Risk score {a.risk_score}/100 places this account in the {a.severity.value} band
(model probability {a.risk_probability:.4f}, decision threshold applied). {action}.

3. KEY FRAUD INDICATORS
The model attributes the score primarily to:
{indicators}

4. MULE TYPOLOGY ASSESSMENT
{typ_block}

5. ACCOUNT PROFILE ANALYSIS
Occupation: {p.occupation or "unknown"}. Account standing period: {p.account_standing or "unknown"}.
Account holder age: {p.age if p.age is not None else "unknown"}. Account tenure: {p.account_tenure if p.account_tenure is not None else "unknown"}.
These demographic and standing factors are weighed against BOI mule-rate priors.

6. RECOMMENDED ACTIONS
{action}. {"Escalate to the financial-crime unit immediately." if a.severity in (Severity.CRITICAL, Severity.HIGH) else "Continue routine handling with the noted monitoring level."}

7. REGULATORY NOTE
{_RBI_NOTE[a.severity]}
""".strip()


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def generate_report(a: AccountAnalysis, *, use_ollama: bool = True) -> tuple[str, str]:
    """Return (report_text, source) where source is 'ollama' or 'fallback'."""
    if use_ollama:
        text = CLIENT.generate(build_prompt(a), system=SYSTEM_PROMPT, temperature=0.3)
        if text and len(text) > 200 and "EXECUTIVE SUMMARY" in text.upper():
            # Append a deterministic regulatory note if the model omitted one.
            if "REGULATORY NOTE" not in text.upper():
                text += f"\n\n7. REGULATORY NOTE\n{_RBI_NOTE[a.severity]}"
            return text, "ollama"
    return fallback_report(a), "fallback"


def _selftest() -> None:
    from app.models.schemas import (
        AccountProfile,
        MuleClassification,
        MuleTypology,
        ShapFeature,
    )

    print("== report_generator self-test ==")
    a = AccountAnalysis(
        case_id="Alpha-001", risk_score=87.0, risk_probability=0.991,
        severity=Severity.CRITICAL,
        classification=MuleClassification(
            typology=MuleTypology.LAYER_1_MULE, confidence=0.91,
            matched_indicators=["High transaction velocity", "Newly opened account"],
            typology_description="Direct recipient of stolen funds.",
        ),
        shap_values=[
            ShapFeature(feature="High-Risk Flag", raw_feature="F670", shap_value=0.34,
                        direction=ShapDirection.INCREASES_RISK),
            ShapFeature(feature="Account Tenure", raw_feature="F2956", shap_value=0.28,
                        direction=ShapDirection.INCREASES_RISK),
        ],
        account_profile=AccountProfile(occupation="student", account_standing="L365D",
                                       age=23, account_tenure=28),
        f3912_flag=False,
    )
    text, src = generate_report(a)
    print(f"source: {src}\n")
    print(text[:1200])
    print("...\nOK")


if __name__ == "__main__":
    _selftest()
