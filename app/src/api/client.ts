// Typed API client. All calls go through the Vite proxy to the FastAPI backend.
import type {
  AccountAnalysis,
  CaseRecord,
  DatasetStats,
  HealthResponse,
  JobStatus,
  MetricsResponse,
  IntelligenceGraph,
  NetworkRisk,
} from "./types";

const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<HealthResponse>("/health"),

  // Cases
  listCases: () => get<CaseRecord[]>("/cases"),
  getCase: (id: string) => get<CaseRecord>(`/cases/${id}`),

  // Investigations / demo library
  demoLibrary: () => get<AccountAnalysis[]>("/investigation"),
  getInvestigation: (id: string) => get<AccountAnalysis>(`/investigation/${id}`),

  // Metrics
  metrics: () => get<MetricsResponse>("/metrics"),

  // Dataset
  datasetStats: () => get<DatasetStats>("/dataset/stats"),
  loadDemoDataset: () => post<JobStatus>("/dataset/demo"),
  jobStatus: (jobId: string) => get<JobStatus>(`/analyze/status/${jobId}`),

  // Upload CSV (multipart)
  async uploadDataset(file: File): Promise<JobStatus> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/analyze/dataset`, { method: "POST", body: form });
    if (!res.ok) throw new Error(`upload failed: ${res.status}`);
    return res.json() as Promise<JobStatus>;
  },

  // Single account
  analyzeAccount: (features: Record<string, unknown>, caseId?: string) =>
    post<AccountAnalysis>("/analyze/account", { features, case_id: caseId }),

  // Network Intelligence
  getEntityGraph: (caseId: string) => get<IntelligenceGraph>(`/intelligence/${caseId}/graph`),
  getCampaign: (caseId: string) => get<NetworkRisk>(`/intelligence/${caseId}/campaign`),
};
