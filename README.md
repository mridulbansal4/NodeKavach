# MULEFLAGGER

**Intelligence Against Financial Crime** — an AI-powered mule-account detection
and suspicious-transaction classification platform for Indian banks.

Built for the **Bank of India × IIT Hyderabad CyberShield Hackathon 2026, Problem
Statement 2** (AI/ML Classification of Suspicious Mule Accounts).

> MULEFLAGGER is not a fraud classifier — it is a fraud-intelligence operating
> system. Every decision is explainable, every alert has a story, and every
> flagged account gets an AI-generated investigation narrative.

---

## What it does

- Trains an **XGBoost** mule-detector on the BOI dataset (9,082 accounts, 3,924
  anonymised features, **112:1 class imbalance**) with leakage-safe feature
  engineering, SMOTE-in-fold cross-validation, and PR-curve threshold tuning.
- Scores every account 0–100 and assigns a **severity band** (CRITICAL / HIGH /
  MEDIUM / LOW) with a recommended action.
- Explains every prediction with **SHAP** attributions (top-10 waterfall) and
  **8 behavioural risk indicators**.
- Classifies flagged accounts into **5 mule typologies** (Layer-1 Mule,
  Pass-Through, Dormant-Activated, Synthetic-Identity, Network-Hub).
- Generates a **7-section investigation report** with a **local LLM** (Ollama),
  with a deterministic fallback when Ollama is unavailable.
- Trains **two models** to expose feature leakage: Model A (with F3912, max
  performance) vs **Model B** (without F3912, the production model).

### Headline results (held-out 20% test split)

| Model | F3912 | PR-AUC (primary) | ROC-AUC | Precision | Recall | F1 |
|-------|-------|------------------|---------|-----------|--------|----|
| Model A | included | **1.000** | 1.000 | 1.000 | 1.000 | 1.000 |
| **Model B** (production) | excluded | **0.919** | 0.998 | 0.933 | 0.875 | 0.903 |

Model A's perfect score is the leakage tell — **F3912 is the #1 mutual-information
feature**. Model B is the honest, deployable number.

---

## Architecture

```
React 18 + TypeScript + Vite + Tailwind  (port 3000)
        │  proxies /api ──────────────► FastAPI + Uvicorn (port 8000)
                                              │
                 ┌────────────────────────────┼────────────────────────────┐
            analyzers/                    engines/                         ai/
       dataset_loader               model · risk · classification     ollama_client
       feature_engineer             shap · validation · cache         report_generator
                                              │
                                    Local Ollama (llama3.2:3b)  ── no external calls
```

All ML inference and LLM generation run **on-premises**. No external API calls at
runtime, no API keys. Suitable for deployment inside a bank security network.

See [`docs/system-architecture.md`](docs/system-architecture.md) and
[`docs/technical-design.md`](docs/technical-design.md) for details.

---

## Getting started

### 1. AI layer (Ollama)

```bash
ollama serve
ollama pull llama3.2:3b      # fast default; qwen3:8b is the fallback
```

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m app.engines.model_engine                  # pre-trains Model A + B (~3 min)
python -m app.engines.investigation_cache           # pre-builds the 5 demo accounts
uvicorn app.main:app --port 8000
```

### 3. Frontend

```bash
cd app
npm install
npm run dev
```

Open **http://localhost:3000** · API docs at **http://localhost:8000/docs**.

> On Windows, set `PYTHONUTF8=1` if you see console encoding errors in the
> self-tests. See [`docs/how-to-run.md`](docs/how-to-run.md) for troubleshooting.

---

## Demo flow (for judges)

1. **Dashboard** — KPI cards + recent cases with severity badges.
2. **Investigation** — click **Alpha-001** → instant CRITICAL Layer-1 Mule with
   risk gauge, SHAP waterfall, behavioural indicators, and an AI report.
   **Alpha-042** matches the fraud registry (F3912=1).
3. **Metrics** — PR-AUC as the giant primary metric; toggle Model A to see the
   leakage warning; note accuracy is explicitly deprioritised.
4. **Dataset** — load the BOI CSV and watch the 6-stage pipeline process 9,082
   accounts; inspect the 18 domain-hint features table.

The 5 demo accounts load instantly from cache — no upload required.

---

## Project layout

```
MULEFLAGGER/
├── app/            React + TypeScript + Vite + Tailwind frontend
├── backend/        FastAPI service (analyzers · engines · ai · routes · models)
├── datasets/       boi_dataset.csv · demo_accounts/ · labels_reference.csv
├── uploads/        runtime CSV intake
└── docs/           architecture · technical design · how-to-run · screenshots
```

Each backend engine has a standalone self-test: `python -m app.engines.<name>`.

---

## Security

- All ML inference on-premises; Ollama runs locally — no data leaves the host.
- CSV uploads stored only in `uploads/`; **SHA-256 hash recorded** for every upload.
- No API keys required or stored. Fully offline once dependencies are installed.

---

*Built for BOI × IITH CyberShield Hackathon 2026 · Problem Statement 2.*
