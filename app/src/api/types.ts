// MULEFLAGGER API response interfaces — mirror the backend Pydantic schemas.

export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type MuleTypology =
  | "LAYER_1_MULE"
  | "PASS_THROUGH"
  | "DORMANT_ACTIVATED"
  | "SYNTHETIC_IDENTITY"
  | "NETWORK_HUB";

export type ShapDirection = "increases_risk" | "reduces_risk";

export interface ShapFeature {
  feature: string;
  raw_feature: string;
  shap_value: number;
  direction: ShapDirection;
  feature_value: number | null;
}

export interface BehaviouralIndicator {
  key: string;
  label: string;
  value: number;
  raw_value: number | null;
  source_feature: string;
  description: string;
}

export interface AccountProfile {
  occupation: string | null;
  account_standing: string | null;
  age: number | null;
  account_tenure: number | null;
}

export interface MuleClassification {
  typology: MuleTypology | null;
  confidence: number;
  matched_indicators: string[];
  typology_description: string;
}

export interface AccountAnalysis {
  case_id: string;
  risk_score: number;
  risk_probability: number;
  severity: Severity;
  classification: MuleClassification;
  shap_values: ShapFeature[];
  behavioural_indicators: BehaviouralIndicator[];
  account_profile: AccountProfile;
  f3912_flag: boolean;
  ai_report: string;
  ai_report_source: string;
  model_used: string;
}

export interface CaseRecord {
  case_id: string;
  risk_score: number;
  severity: Severity;
  typology: MuleTypology | null;
  account_standing: string | null;
  occupation: string | null;
  is_demo: boolean;
  created_at: string;
  analysis: AccountAnalysis | null;
}

export interface ConfusionMatrix {
  tp: number;
  fp: number;
  tn: number;
  fn: number;
}

export interface PrecisionAtK {
  k: number;
  precision: number;
  true_mules_in_top_k: number;
}

export interface ModelMetrics {
  model_name: string;
  includes_f3912: boolean;
  pr_auc: number;
  roc_auc: number;
  precision: number;
  recall: number;
  f1: number;
  ks_statistic: number;
  accuracy: number;
  accuracy_warning: string;
  false_positive_rate: number;
  confusion_matrix: ConfusionMatrix;
  precision_at_k: PrecisionAtK[];
  threshold: number;
  feature_importance: ShapFeature[];
}

export interface MetricsResponse {
  model_a: ModelMetrics | null;
  model_b: ModelMetrics | null;
  leakage_note: string;
  class_imbalance_note: string;
}

export interface DomainHintFeature {
  feature: string;
  decoded_meaning: string;
  mule_mean: number | null;
  legit_mean: number | null;
  ks_stat: number | null;
  discriminative_power: string;
}

export interface FeatureTypeBreakdown {
  binary: number;
  low_cardinality: number;
  continuous: number;
  categorical: number;
}

export interface DatasetStats {
  rows: number;
  features: number;
  mule_count: number;
  legit_count: number;
  imbalance_ratio: string;
  sparsity_pct: number;
  fully_null_columns: number;
  feature_type_breakdown: FeatureTypeBreakdown;
  domain_hint_features: DomainHintFeature[];
  sha256: string | null;
}

export type StageStatus = "pending" | "running" | "done" | "error";

export interface PipelineStage {
  name: string;
  status: StageStatus;
  duration_ms: number | null;
  detail: string;
}

export interface JobStatus {
  job_id: string;
  status: string;
  stages: PipelineStage[];
  summary: Record<string, unknown>;
  error: string | null;
}

export interface OllamaStatus {
  reachable: boolean;
  host: string;
  model: string | null;
  available_models: string[];
  message: string;
}

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  active_model: string;
  ollama: OllamaStatus;
  dataset_loaded: boolean;
  dataset_accounts: number;
}

// --------------------------------------------------------------------------- //
// Network Intelligence
// --------------------------------------------------------------------------- //
export interface IntelligenceNode {
  id: string;
  type: string;
  label: string;
  risk_score: number;
  is_mule: boolean;
  attributes: Record<string, unknown>;
}

export interface IntelligenceLink {
  source: string;
  target: string;
  type: string;
  weight: number;
}

export interface IntelligenceGraph {
  nodes: IntelligenceNode[];
  links: IntelligenceLink[];
}

export interface NetworkRisk {
  community_id: string;
  size: number;
  mean_risk: number;
  mule_count: number;
  exposure_lakhs: number;
  central_hubs: string[];
}
