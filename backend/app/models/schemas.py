"""
MULEFLAGGER — API contracts (Pydantic v2 schemas).

These models define every payload that crosses the backend boundary. Built
first so that all engines, routes, and the AI layer share one vocabulary.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #
class Severity(str, Enum):
    """Risk severity bands. Mapped from the 0-100 risk score."""

    CRITICAL = "CRITICAL"   # 80-100 — immediate block recommended
    HIGH = "HIGH"           # 60-79  — step-up authentication required
    MEDIUM = "MEDIUM"       # 40-59  — enhanced monitoring
    LOW = "LOW"             # 0-39   — allow, log only


class MuleTypology(str, Enum):
    """The five mule account typologies MULEFLAGGER classifies into."""

    LAYER_1_MULE = "LAYER_1_MULE"
    PASS_THROUGH = "PASS_THROUGH"
    DORMANT_ACTIVATED = "DORMANT_ACTIVATED"
    SYNTHETIC_IDENTITY = "SYNTHETIC_IDENTITY"
    NETWORK_HUB = "NETWORK_HUB"


class ShapDirection(str, Enum):
    INCREASES_RISK = "increases_risk"
    REDUCES_RISK = "reduces_risk"


# --------------------------------------------------------------------------- #
# Explainability / scoring primitives
# --------------------------------------------------------------------------- #
class ShapFeature(BaseModel):
    """A single SHAP attribution row."""

    feature: str = Field(..., description="Human-readable feature name")
    raw_feature: str = Field(..., description="Original column id, e.g. F115")
    shap_value: float = Field(..., description="Signed SHAP contribution")
    direction: ShapDirection
    feature_value: Optional[float] = Field(
        None, description="The account's value for this feature, if known"
    )


class BehaviouralIndicator(BaseModel):
    """One of the 8 behavioural risk indicators, normalised 0-1 for display."""

    key: str
    label: str
    value: float = Field(..., ge=0.0, le=1.0, description="Normalised 0-1 for bar fill")
    raw_value: Optional[float] = Field(None, description="Underlying raw feature value")
    source_feature: str
    description: str


class AccountProfile(BaseModel):
    """Demographic / standing context decoded from F3889/F3891/F3894."""

    occupation: Optional[str] = None        # F3891
    account_standing: Optional[str] = None  # F3889
    age: Optional[float] = None             # F3894
    account_tenure: Optional[float] = None  # F2956


class MuleClassification(BaseModel):
    typology: Optional[MuleTypology] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    matched_indicators: list[str] = Field(default_factory=list)
    typology_description: str = ""


# --------------------------------------------------------------------------- #
# Account analysis (the core unit)
# --------------------------------------------------------------------------- #
class AccountAnalysis(BaseModel):
    """Full analysis of a single account — the payload behind every investigation."""

    case_id: str
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_probability: float = Field(..., ge=0.0, le=1.0)
    severity: Severity
    classification: MuleClassification
    shap_values: list[ShapFeature] = Field(default_factory=list)
    behavioural_indicators: list[BehaviouralIndicator] = Field(default_factory=list)
    account_profile: AccountProfile = Field(default_factory=AccountProfile)
    f3912_flag: bool = Field(False, description="Matches fraud registry (leakage feature)")
    ai_report: str = ""
    ai_report_source: str = Field("fallback", description="'ollama' or 'fallback'")
    model_used: str = "Model B"


# --------------------------------------------------------------------------- #
# Cases / persistence
# --------------------------------------------------------------------------- #
class CaseRecord(BaseModel):
    """A persisted, listable case (demo cache + uploaded accounts)."""

    case_id: str
    risk_score: float
    severity: Severity
    typology: Optional[MuleTypology] = None
    account_standing: Optional[str] = None
    occupation: Optional[str] = None
    is_demo: bool = False
    created_at: str = ""
    analysis: Optional[AccountAnalysis] = None


# --------------------------------------------------------------------------- #
# Metrics / validation
# --------------------------------------------------------------------------- #
class ConfusionMatrix(BaseModel):
    tp: int
    fp: int
    tn: int
    fn: int


class PrecisionAtK(BaseModel):
    k: int
    precision: float
    true_mules_in_top_k: int


class ModelMetrics(BaseModel):
    model_name: str = Field(..., description="'Model A' or 'Model B'")
    includes_f3912: bool
    pr_auc: float = Field(..., description="PRIMARY metric")
    roc_auc: float
    precision: float
    recall: float
    f1: float
    ks_statistic: float
    accuracy: float = Field(..., description="Shown but deprioritised — see warning")
    accuracy_warning: str = (
        "Accuracy is meaningless at 112:1 class imbalance and is never used as a "
        "primary metric. PR-AUC is the headline metric."
    )
    false_positive_rate: float
    confusion_matrix: ConfusionMatrix
    precision_at_k: list[PrecisionAtK] = Field(default_factory=list)
    threshold: float = Field(..., description="Tuned decision threshold (not 0.5)")
    feature_importance: list[ShapFeature] = Field(default_factory=list)


class MetricsResponse(BaseModel):
    model_a: Optional[ModelMetrics] = None
    model_b: Optional[ModelMetrics] = None
    leakage_note: str = (
        "F3912 may be a post-labelling leakage feature (96.3% precision for mules). "
        "Model B excludes it and represents production performance."
    )
    class_imbalance_note: str = (
        "112:1 mule-to-legitimate ratio. Accuracy is meaningless here — "
        "we never report it as a primary metric."
    )


# --------------------------------------------------------------------------- #
# Dataset analysis
# --------------------------------------------------------------------------- #
class DomainHintFeature(BaseModel):
    feature: str
    decoded_meaning: str
    mule_mean: Optional[float] = None
    legit_mean: Optional[float] = None
    ks_stat: Optional[float] = None
    discriminative_power: str = "—"   # Low / Medium / High


class FeatureTypeBreakdown(BaseModel):
    binary: int = 0
    low_cardinality: int = 0
    continuous: int = 0
    categorical: int = 0


class DatasetStats(BaseModel):
    rows: int
    features: int
    mule_count: int
    legit_count: int
    imbalance_ratio: str
    sparsity_pct: float
    fully_null_columns: int
    feature_type_breakdown: FeatureTypeBreakdown = Field(default_factory=FeatureTypeBreakdown)
    domain_hint_features: list[DomainHintFeature] = Field(default_factory=list)
    sha256: Optional[str] = None


# --------------------------------------------------------------------------- #
# Pipeline jobs
# --------------------------------------------------------------------------- #
class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class PipelineStage(BaseModel):
    name: str
    status: StageStatus = StageStatus.PENDING
    duration_ms: Optional[float] = None
    detail: str = ""


class JobStatus(BaseModel):
    job_id: str
    status: str  # queued | running | complete | error
    stages: list[PipelineStage] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #
class AccountRequest(BaseModel):
    """Single-account analysis request — a raw feature dict (F-codes -> values)."""

    features: dict[str, Any] = Field(default_factory=dict)
    case_id: Optional[str] = None


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
class OllamaStatus(BaseModel):
    reachable: bool
    host: str
    model: Optional[str] = None
    available_models: list[str] = Field(default_factory=list)
    message: str = ""


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    active_model: str
    ollama: OllamaStatus
    dataset_loaded: bool
    dataset_accounts: int
