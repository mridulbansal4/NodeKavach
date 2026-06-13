import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { HealthResponse } from "../api/types";

// Bottom system status bar: model status, Ollama dot, dataset count.
export default function StatusBar() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = () =>
      api
        .health()
        .then((h) => alive && (setHealth(h), setErr(false)))
        .catch(() => alive && setErr(true));
    load();
    const id = setInterval(load, 15000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const ollamaOk = health?.ollama.reachable ?? false;

  return (
    <div className="border-t border-border bg-bg px-6 py-2 flex items-center gap-6 text-[11px] font-mono text-textSecondary">
      <span className="flex items-center gap-2">
        <Dot ok={health?.model_loaded ?? false} />
        {health ? health.active_model : "Model status…"}
      </span>
      <span className="flex items-center gap-2">
        <Dot ok={ollamaOk} />
        Ollama {ollamaOk ? `· ${health?.ollama.model}` : "offline"}
      </span>
      <span className="flex items-center gap-2">
        <Dot ok={health?.dataset_loaded ?? false} />
        {health ? `${health.dataset_accounts.toLocaleString()} accounts loaded` : "Dataset…"}
      </span>
      {err && (
        <span className="text-high">
          Backend unreachable at /api. Start the FastAPI server on :8000.
        </span>
      )}
      <span className="ml-auto text-textMuted">MULEFLAGGER v1.0 · on-premises · no external calls</span>
    </div>
  );
}

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className="inline-block h-2 w-2 rounded-full"
      style={{ backgroundColor: ok ? "#34C759" : "#FF3B30" }}
    />
  );
}
