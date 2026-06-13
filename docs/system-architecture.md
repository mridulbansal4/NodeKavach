# MULEFLAGGER — System Architecture

## 1. Component diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND  (React 18 + TS)                          │
│  Vite dev server : port 3000                                               │
│  Pages: Dashboard · Investigation · Metrics · Dataset · Report             │
│  Components: RiskGauge (SVG) · ShapWaterfall · BehaviouralBars · SarModal  │
│  Typed API client (src/api) ── proxies /api ──┐                            │
└───────────────────────────────────────────────┼──────────────────────────┘
                                                 │ HTTP (localhost only)
┌────────────────────────────────────────────────▼─────────────────────────┐
│                       BACKEND  (FastAPI + Uvicorn)  port 8000              │
│                                                                            │
│  routes/        health · analyze · cases · metrics · investigation · data │
│       │                                                                    │
│  service.py     orchestration: analyze_account() · run_full_pipeline()     │
│       │                                                                    │
│  ┌────▼─────────┐   ┌──────────────────────────────┐   ┌────────────────┐ │
│  │ analyzers/   │   │ engines/                     │   │ ai/            │ │
│  │ dataset_     │──►│ model_engine  (XGBoost A/B)  │   │ ollama_client  │ │
│  │  loader      │   │ risk_engine   (score+bands)  │   │ report_        │ │
│  │ feature_     │   │ classification_engine        │──►│  generator     │ │
│  │  engineer    │   │ shap_engine   (TreeExplainer)│   │ (7 sections)   │ │
│  │ dataset_     │   │ validation_engine (metrics)  │   └───────┬────────┘ │
│  │  stats       │   │ investigation_cache (demo)   │           │          │
│  └──────────────┘   └──────────────────────────────┘           │          │
│  database/case_store.py  (JSON persistence)                     │          │
└─────────────────────────────────────────────────────────────────┼─────────┘
                                                                    │
                                          ┌─────────────────────────▼────────┐
                                          │  Ollama (local)  port 11434       │
                                          │  llama3.2:3b  /  qwen3:8b fallback │
                                          │  NO EXTERNAL CALLS                 │
                                          └────────────────────────────────────┘
```

## 2. Data flow: CSV upload → risk score → AI report

```
1. INGEST       uploads/<file>.csv  (SHA-256 recorded)
                       │
2. LOAD         dataset_loader: drop unnamed index, drop 63 fully-null columns,
                add missingness indicators (>5% null), encode F3889/F3891,
                separate target F3924
                       │
3. ENGINEER     feature_engineer: MI rank → top 200, prioritise 18 domain hints,
                median impute (fit on TRAIN split only)
                       │
4. MODEL        model_engine: XGBoost (scale_pos_weight=112), SMOTE-in-fold 5-CV,
                PR-curve threshold tuning; Model A (with F3912) + Model B (without)
                       │
5. SCORE        risk_engine: probability → 0-100 (threshold-anchored) → severity
                       │
6. EXPLAIN      shap_engine: TreeExplainer top-10  +  classification_engine: typology
                       │
7. NARRATE      report_generator → ollama_client (or deterministic fallback)
                       │
8. PERSIST      database/case_store.py (JSON) → surfaced via /api/cases, /api/report
```

Single-account requests (`POST /api/analyze/account`) run steps 5–7 against the
already-trained models. The full pipeline (`POST /api/analyze/dataset`) runs all
six staged steps and reports per-stage timings to the Dataset page.

## 3. Security boundaries

| Boundary | Control |
|----------|---------|
| Network egress | None at runtime. All inference local. No API keys. |
| LLM | Ollama on `localhost:11434`. No data leaves the host. |
| Upload storage | CSVs confined to `uploads/`. SHA-256 recorded per upload. |
| Persistence | Local JSON under `backend/data/`. No external DB. |
| Offline | Fully functional offline once Python + npm + Ollama deps are installed. |

The entire stack is designed to run inside an air-gapped bank security operations
network. The only outbound dependency is during initial install (pip / npm / ollama
pull); at runtime there are zero external calls.

## 4. Runtime processes

| Process | Port | Purpose |
|---------|------|---------|
| Vite dev server | 3000 | Serves the React app, proxies `/api` → 8000 |
| Uvicorn / FastAPI | 8000 | REST API, model serving, orchestration |
| Ollama | 11434 | Local LLM inference for investigation reports |

Models (`model_a.pkl`, `model_b.pkl`), metrics, demo cache, and dataset stats are
precomputed into `backend/cache/` so the API and demo start instantly.
