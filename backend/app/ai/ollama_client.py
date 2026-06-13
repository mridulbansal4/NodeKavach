"""
ollama_client.py — local LLM inference via Ollama. No external API calls, ever.

Connects to a local Ollama instance (default http://localhost:11434), uses
llama3.2:3b by default with a qwen3:8b fallback, and exposes a health check
plus a synchronous text-generation call. All failures are swallowed and
surfaced as a `reachable=False` status so the report generator can fall back
to a structured non-AI report without ever showing the user an error.

Run standalone:  python -m app.ai.ollama_client
"""
from __future__ import annotations

import re

import httpx

from app.config import (
    OLLAMA_FALLBACK_MODEL,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
)
from app.models.schemas import OllamaStatus

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class OllamaClient:
    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL) -> None:
        self.host = host.rstrip("/")
        self.model = model

    # ------------------------------------------------------------------ #
    def health(self) -> OllamaStatus:
        try:
            r = httpx.get(f"{self.host}/api/tags", timeout=5.0)
            r.raise_for_status()
            models = [m.get("name", "") for m in r.json().get("models", [])]
            chosen = self._resolve_model(models)
            return OllamaStatus(
                reachable=True, host=self.host, model=chosen,
                available_models=models,
                message="Ollama reachable." if chosen else
                        "Ollama reachable but no preferred model pulled.",
            )
        except Exception as exc:  # noqa: BLE001 — degrade gracefully
            return OllamaStatus(
                reachable=False, host=self.host, model=None, available_models=[],
                message=f"Ollama unreachable at {self.host}. "
                        "Investigation reports will use cached analysis.",
            )

    def _resolve_model(self, available: list[str]) -> str | None:
        for candidate in (self.model, OLLAMA_FALLBACK_MODEL):
            if candidate in available:
                return candidate
        # accept a loose match (e.g. 'llama3.2:3b' vs 'llama3.2:latest')
        for candidate in (self.model, OLLAMA_FALLBACK_MODEL):
            base = candidate.split(":")[0]
            for a in available:
                if a.split(":")[0] == base:
                    return a
        return available[0] if available else None

    # ------------------------------------------------------------------ #
    def generate(self, prompt: str, *, system: str | None = None,
                 temperature: float = 0.3) -> str | None:
        """Return generated text, or None if Ollama is unavailable/errored."""
        status = self.health()
        if not status.reachable or not status.model:
            return None
        payload = {
            "model": status.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
            # qwen3 supports a thinking mode; disable it for clean report output.
            "think": False,
        }
        if system:
            payload["system"] = system
        try:
            r = httpx.post(f"{self.host}/api/generate", json=payload, timeout=OLLAMA_TIMEOUT)
            r.raise_for_status()
            text = r.json().get("response", "") or ""
            return _THINK_RE.sub("", text).strip()
        except Exception:  # noqa: BLE001
            return None


# Module-level singleton.
CLIENT = OllamaClient()


def _selftest() -> None:
    print("== ollama_client self-test ==")
    c = OllamaClient()
    st = c.health()
    print(f"reachable : {st.reachable}")
    print(f"host      : {st.host}")
    print(f"model     : {st.model}")
    print(f"available : {st.available_models}")
    if st.reachable:
        out = c.generate("Reply with exactly: NodeKavach ONLINE", temperature=0.0)
        print(f"generate  : {out!r}")
    print("OK")


if __name__ == "__main__":
    _selftest()
