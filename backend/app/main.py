"""
main.py — MULEFLAGGER FastAPI application entry point.

Bootstraps the API, loads the pre-trained models and demo cache at startup,
and mounts all routers. Fully offline: all ML inference and LLM generation
happen on-premises (Ollama localhost), no external API calls at runtime.

Run:  uvicorn app.main:app --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.engines.model_engine import ENGINE
from app.routes import analyze, cases, dataset, health, investigation, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load pre-trained models (if present) and seed the demo case library.
    ENGINE.load()
    try:
        from app.database import case_store
        case_store.seed_demo_cases()
    except Exception as exc:  # noqa: BLE001 — never block startup
        print(f"[startup] demo seed skipped: {exc}")
    print(f"[startup] models loaded: {ENGINE.is_loaded}")
    yield


app = FastAPI(
    title="MULEFLAGGER API",
    description="Intelligence Against Financial Crime — AI mule-account detection "
                "for the BOI × IITH CyberShield Hackathon 2026.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(cases.router)
app.include_router(metrics.router)
app.include_router(investigation.router)
app.include_router(dataset.router)


@app.get("/")
def root():
    return {
        "name": "MULEFLAGGER",
        "tagline": "Intelligence Against Financial Crime",
        "docs": "/docs",
        "health": "/api/health",
    }
