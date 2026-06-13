"""
NodeKavach — shared configuration & domain knowledge.

Single source of truth for: paths, the target column, the human-readable
feature dictionary, the 18 BOI domain-hint features, categorical encodings,
and the leakage feature. Imported by every engine so the vocabulary stays
consistent across the whole platform.
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
BACKEND_DIR = Path(__file__).resolve().parent.parent          # .../backend
PROJECT_DIR = BACKEND_DIR.parent                               # .../NodeKavach
CACHE_DIR = BACKEND_DIR / "cache"
DATA_DIR = BACKEND_DIR / "data"
DATASETS_DIR = PROJECT_DIR / "datasets"
UPLOADS_DIR = PROJECT_DIR / "uploads"

DEFAULT_DATASET = DATASETS_DIR / "boi_dataset.csv"

for _d in (CACHE_DIR, DATA_DIR, UPLOADS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# Target / leakage
# --------------------------------------------------------------------------- #
TARGET_COLUMN = "F3924"        # 1 = mule, 0 = legitimate
LEAKAGE_FEATURE = "F3912"      # 96.3% precision for mules — handled via Model A/B
INDEX_COLUMN = "Unnamed: 0"    # the leading unnamed index column in the CSV

SCALE_POS_WEIGHT = 112         # class imbalance ~112:1
TOP_K_FEATURES = 200           # mutual-information retention
RANDOM_STATE = 42

# --------------------------------------------------------------------------- #
# Severity bands
# --------------------------------------------------------------------------- #
SEVERITY_BANDS = [
    # (min_inclusive, max_inclusive, name, recommended_action)
    (80, 100, "CRITICAL", "Immediate block recommended"),
    (60, 79, "HIGH", "Step-up authentication required"),
    (40, 59, "MEDIUM", "Enhanced monitoring"),
    (0, 39, "LOW", "Allow, log only"),
]

# --------------------------------------------------------------------------- #
# Human-readable feature dictionary
# --------------------------------------------------------------------------- #
FEATURE_NAMES: dict[str, str] = {
    "F115": "Transaction Risk Score",
    "F2956": "Account Tenure",
    "F670": "High-Risk Flag",
    "F2082": "Legitimacy Indicator",
    "F3043": "Activity Count",
    "F3889": "Account Standing Period",
    "F3891": "Account Holder Occupation",
    "F3894": "Account Holder Age",
    "F3912": "Fraud Registry Flag (Leakage Warning)",
}


def feature_label(code: str) -> str:
    """Map an F-code to a human-readable label, falling back to 'Feature F{n}'."""
    if code in FEATURE_NAMES:
        return FEATURE_NAMES[code]
    return f"Feature {code}"


# --------------------------------------------------------------------------- #
# The 18 BOI domain-hint features (prioritised in feature selection)
# --------------------------------------------------------------------------- #
DOMAIN_HINT_FEATURES = [
    "F115", "F321", "F527", "F531", "F670", "F1692", "F2082", "F2122",
    "F2582", "F2678", "F2737", "F2956", "F3043", "F3836", "F3887",
    "F3889", "F3891", "F3894",
]

# Decoded meanings for the dataset-analysis table. Where we have a concrete
# label from the spec we use it; otherwise a domain-informed best guess.
DOMAIN_HINT_MEANINGS: dict[str, str] = {
    "F115": "Transaction Risk Score",
    "F321": "Transfer Velocity Signal",
    "F527": "Inbound Counterparty Spread",
    "F531": "Outbound Counterparty Spread",
    "F670": "High-Risk Flag",
    "F1692": "Cash Flow Ratio",
    "F2082": "Legitimacy Indicator",
    "F2122": "Channel Usage Pattern",
    "F2582": "Balance Volatility",
    "F2678": "Geographic Risk Signal",
    "F2737": "Device / Session Anomaly",
    "F2956": "Account Tenure",
    "F3043": "Activity Count",
    "F3836": "KYC Completeness Score",
    "F3887": "Relationship Depth",
    "F3889": "Account Standing Period",
    "F3891": "Account Holder Occupation",
    "F3894": "Account Holder Age",
}

# --------------------------------------------------------------------------- #
# Categorical encodings
# --------------------------------------------------------------------------- #
# F3889 — account standing period (ordered, recent -> long-standing)
F3889_ORDER = ["L7D", "L14D", "L31D", "L90D", "L180D", "L365D", "G365D"]
F3889_ENCODING = {v: i for i, v in enumerate(F3889_ORDER)}

# F3891 — occupation
F3891_CATEGORIES = [
    "selfemployed", "salaried", "student", "agriculture",
    "housewife", "retired", "others",
]
F3891_ENCODING = {v: i for i, v in enumerate(F3891_CATEGORIES)}

# Mule rate priors per occupation (from BOI analysis) — used for occupation risk.
OCCUPATION_MULE_RATE = {
    "student": 0.0194,
    "agriculture": 0.0126,
    "housewife": 0.0045,
    "selfemployed": 0.0090,
    "salaried": 0.0070,
    "retired": 0.0040,
    "others": 0.0100,
}

# Mule rate priors per account-standing band.
STANDING_MULE_RATE = {
    "L7D": 0.0000,
    "L14D": 0.0000,
    "L31D": 0.0030,
    "L90D": 0.0060,
    "L180D": 0.0090,
    "L365D": 0.0126,
    "G365D": 0.0080,
}

# --------------------------------------------------------------------------- #
# Model artefact paths
# --------------------------------------------------------------------------- #
MODEL_A_PATH = CACHE_DIR / "model_a.pkl"   # with F3912 (max performance)
MODEL_B_PATH = CACHE_DIR / "model_b.pkl"   # without F3912 (production)
METRICS_PATH = CACHE_DIR / "metrics.json"
DEMO_CACHE_PATH = CACHE_DIR / "demo_accounts.json"
DATASET_STATS_PATH = CACHE_DIR / "dataset_stats.json"

# --------------------------------------------------------------------------- #
# Ollama
# --------------------------------------------------------------------------- #
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_FALLBACK_MODEL = "qwen3:8b"
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120"))
