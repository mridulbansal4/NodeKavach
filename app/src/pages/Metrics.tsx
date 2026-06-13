import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { MetricsResponse, ModelMetrics } from "../api/types";

export default function Metrics() {
  const [data, setData] = useState<MetricsResponse | null>(null);
  const [tab, setTab] = useState<"A" | "B">("B");
  const [err, setErr] = useState(false);

  useEffect(() => {
    api.metrics().then(setData).catch(() => setErr(true));
  }, []);

  if (err) {
    return (
      <div className="panel p-8 text-high">
        Metrics unavailable — the model has not been trained yet. Run{" "}
        <span className="font-mono">python -m app.engines.model_engine</span> in the backend.
      </div>
    );
  }
  if (!data) return <div className="text-textMuted">Loading metrics…</div>;

  const m = tab === "A" ? data.model_a : data.model_b;

  return (
    <div>
      <header className="mb-6">
        <h1 className="font-display text-[28px] font-bold text-textPrimary">Model Analysis & Metrics</h1>
        <p className="text-[13px] text-textSecondary">{data.class_imbalance_note}</p>
      </header>

      <div className="flex gap-2 mb-6">
        <TabButton active={tab === "A"} onClick={() => setTab("A")}>
          Model A (with F3912)
        </TabButton>
        <TabButton active={tab === "B"} onClick={() => setTab("B")}>
          Model B (without F3912)
        </TabButton>
      </div>

      {tab === "A" && (
        <div className="mb-6 rounded-sm border border-high/40 bg-high/10 px-4 py-3 text-[13px] text-high">
          ⚠ {data.leakage_note}
        </div>
      )}

      {m ? <ModelPanel m={m} /> : <div className="text-textMuted">Model not available.</div>}
    </div>
  );
}

function ModelPanel({ m }: { m: ModelMetrics }) {
  const cm = m.confusion_matrix;
  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-6" style={{ gridTemplateColumns: "320px 1fr" }}>
        {/* Primary metric */}
        <div className="panel p-6 flex flex-col items-center justify-center" style={{ borderTop: "2px solid #34C759" }}>
          <div className="label-mono">PRIMARY METRIC · PR-AUC</div>
          <div className="font-display font-bold text-low" style={{ fontSize: 72, lineHeight: 1 }}>
            {m.pr_auc.toFixed(3)}
          </div>
          <div className="text-[12px] text-textSecondary mt-2">
            decision threshold {m.threshold.toFixed(3)} (tuned, not 0.5)
          </div>
        </div>

        {/* Metrics table */}
        <div className="panel p-6">
          <h3 className="section-header">Metrics</h3>
          <table className="w-full text-[13px]">
            <tbody>
              <MetricRow label="Precision" value={m.precision} />
              <MetricRow label="Recall" value={m.recall} />
              <MetricRow label="F1 Score" value={m.f1} />
              <MetricRow label="ROC-AUC" value={m.roc_auc} />
              <MetricRow label="KS Statistic" value={m.ks_statistic} />
              <MetricRow label="False Positive Rate" value={m.false_positive_rate} />
              <tr className="border-t border-border">
                <td className="py-2 text-textMuted">Accuracy (deprioritised)</td>
                <td className="py-2 text-right font-mono text-textMuted">{m.accuracy.toFixed(4)}</td>
              </tr>
            </tbody>
          </table>
          <p className="mt-3 text-[11px] text-textMuted leading-relaxed">{m.accuracy_warning}</p>
        </div>
      </div>

      <div className="grid gap-6" style={{ gridTemplateColumns: "1fr 1fr" }}>
        {/* Confusion matrix */}
        <div className="panel p-6">
          <h3 className="section-header">Confusion Matrix</h3>
          <div className="grid grid-cols-2 gap-2 max-w-sm">
            <ConfCell label="True Positive" value={cm.tp} color="#34C759" />
            <ConfCell label="False Negative" value={cm.fn} color="#FF9500" />
            <ConfCell label="False Positive" value={cm.fp} color="#FF9500" />
            <ConfCell label="True Negative" value={cm.tn} color="#1976D2" />
          </div>
        </div>

        {/* Precision@K */}
        <div className="panel p-6">
          <h3 className="section-header">Precision @ K</h3>
          <div className="flex flex-col gap-4 pt-2">
            {m.precision_at_k.map((p) => (
              <div key={p.k}>
                <div className="flex items-center justify-between mb-1 text-[12px]">
                  <span className="text-textSecondary">K = {p.k}</span>
                  <span className="font-mono text-accent">
                    {(p.precision * 100).toFixed(0)}% · {p.true_mules_in_top_k} true mules
                  </span>
                </div>
                <div className="h-3 bg-rowAlt rounded-sm overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-sm transition-all duration-500"
                    style={{ width: `${p.precision * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Feature importance */}
      <div className="panel p-6">
        <h3 className="section-header">Feature Importance — Top {m.feature_importance.length} (mean |SHAP|)</h3>
        <FeatureImportance items={m.feature_importance} />
      </div>
    </div>
  );
}

function FeatureImportance({ items }: { items: ModelMetrics["feature_importance"] }) {
  const max = Math.max(...items.map((i) => Math.abs(i.shap_value)), 1e-6);
  return (
    <div className="flex flex-col gap-1.5">
      {items.map((f) => (
        <div key={f.raw_feature} className="grid grid-cols-[220px_1fr_60px] items-center gap-2">
          <span className="truncate text-[12px] text-textSecondary" title={f.feature}>
            {f.feature}
          </span>
          <div className="h-3.5 bg-rowAlt rounded-sm overflow-hidden">
            <div
              className="h-full rounded-sm"
              style={{
                width: `${(Math.abs(f.shap_value) / max) * 100}%`,
                backgroundColor: f.raw_feature === "F3912" ? "#FF3B30" : "#00D4FF",
              }}
            />
          </div>
          <span className="text-right font-mono text-[11px] text-textMuted">
            {Math.abs(f.shap_value).toFixed(3)}
          </span>
        </div>
      ))}
    </div>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-sm text-[13px] font-medium border transition-colors ${
        active ? "border-accent bg-surface text-textPrimary" : "border-border text-textSecondary hover:bg-surface"
      }`}
    >
      {children}
    </button>
  );
}

function MetricRow({ label, value }: { label: string; value: number }) {
  return (
    <tr className="border-t border-border/50">
      <td className="py-2 text-textSecondary">{label}</td>
      <td className="py-2 text-right font-mono text-textPrimary">{value.toFixed(4)}</td>
    </tr>
  );
}

function ConfCell({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="panel-2 p-4 text-center" style={{ borderLeft: `2px solid ${color}` }}>
      <div className="font-display text-[32px] font-bold" style={{ color }}>
        {value}
      </div>
      <div className="text-[11px] uppercase tracking-wider text-textSecondary">{label}</div>
    </div>
  );
}
