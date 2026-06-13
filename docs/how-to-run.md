# NodeKavach — How to Run

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | A native CPython (not MSYS2) so binary wheels install cleanly |
| Node.js | 18+ | For the Vite frontend |
| Ollama | latest | Local LLM runtime |

## Full setup

### 1. Start Ollama and pull a model

```bash
ollama serve
ollama pull llama3.2:3b      # ~2 GB, fast. qwen3:8b is the automatic fallback.
```

Verify: `curl http://localhost:11434/api/tags` should list the model.

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate              # Windows PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Pre-train both models (~3 minutes — mutual-information + SMOTE 5-fold CV ×2)
python -m app.engines.model_engine

# Pre-build the 5 demo accounts (generates AI reports once, caches them)
python -m app.engines.investigation_cache

# Serve
uvicorn app.main:app --port 8000
```

API docs: **http://localhost:8000/docs**

### 3. Frontend

```bash
cd app
npm install
npm run dev
```

App: **http://localhost:3000**

## Verifying each backend component (standalone self-tests)

Every analyzer/engine runs independently:

```bash
python -m app.analyzers.dataset_loader        # load + clean (drops 63 null cols)
python -m app.analyzers.feature_engineer      # MI selection (top 200)
python -m app.analyzers.dataset_stats         # 18 domain-hint table + KS stats
python -m app.engines.model_engine            # trains + saves Model A & B
python -m app.engines.risk_engine             # score mapping + 8 indicators
python -m app.engines.classification_engine   # 5 typology rules
python -m app.engines.shap_engine             # SHAP attributions (needs models)
python -m app.engines.validation_engine       # held-out metrics (needs models)
python -m app.engines.investigation_cache     # builds the demo cache
python -m app.ai.ollama_client                # Ollama health + generation
python -m app.ai.report_generator             # 7-section report
```

> **Windows note:** if a self-test crashes on a Unicode console error
> (`charmap codec can't encode`), set `PYTHONUTF8=1` before running.

## Troubleshooting

### "Ollama unreachable at localhost:11434"
The platform degrades gracefully — investigation reports fall back to a
deterministic structured report built from the analysis data, and no error is
shown to the user. To enable live AI reports, run `ollama serve` and
`ollama pull llama3.2:3b`. The system status bar shows a red Ollama dot when
unreachable.

### "Models not trained yet" on the Metrics page
Run `python -m app.engines.model_engine` in the backend. This writes
`model_a.pkl` and `model_b.pkl` into `backend/cache/`. The server loads them at
startup.

### `ModuleNotFoundError: No module named 'pandas'` (or similar)
The venv isn't active or `pip install -r requirements.txt` didn't complete. On
Windows, ensure the venv was created with a **native** CPython (not MSYS2/MinGW),
otherwise binary wheels (xgboost, shap) may fail to install.

### Frontend can't reach the API
The Vite dev server proxies `/api` → `http://localhost:8000`. Make sure the
backend is running on port 8000. Check the bottom status bar — it polls
`/api/health` every 15 s and reports model/Ollama/dataset state.

### Pickle load error (`Can't get attribute 'TrainedModel'`)
Always (re)train via `python -m app.engines.model_engine` (the `__main__` block
delegates to the package module so models pickle under `app.engines.model_engine`,
not `__main__`). Don't pickle from an ad-hoc script that defines the class itself.

### Retrain on a new dataset
Replace `datasets/boi_dataset.csv`, then either re-run `model_engine` or POST the
CSV to `/api/analyze/dataset` (the Dataset page "Choose CSV" / drag-drop). Uploads
are stored in `uploads/` with their SHA-256 recorded.

## Ports summary

| Service | Port |
|---------|------|
| Frontend (Vite) | 3000 |
| Backend (FastAPI) | 8000 |
| Ollama | 11434 |
