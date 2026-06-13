import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { DatasetStats, JobStatus } from "../api/types";

export default function Dataset() {
  const [stats, setStats] = useState<DatasetStats | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [running, setRunning] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    api.datasetStats().then(setStats).catch(() => {});
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const poll = (jobId: string) => {
    pollRef.current = window.setInterval(async () => {
      const j = await api.jobStatus(jobId);
      setJob(j);
      if (j.status === "complete" || j.status === "error") {
        if (pollRef.current) clearInterval(pollRef.current);
        setRunning(false);
        api.datasetStats().then(setStats).catch(() => {});
      }
    }, 1200);
  };

  const runDemo = async () => {
    setRunning(true);
    const j = await api.loadDemoDataset();
    setJob(j);
    poll(j.job_id);
  };

  const onFile = async (file: File) => {
    setRunning(true);
    const j = await api.uploadDataset(file);
    setJob(j);
    poll(j.job_id);
  };

  return (
    <div>
      <header className="mb-6">
        <h1 className="font-display text-[28px] font-bold text-primary">Intelligence Data Feed</h1>
        <p className="text-[13px] text-textSecondary">
          Ingest entity transaction data and extract graph-ready signals. 9,082 entities, 3,924 anonymised features.
        </p>
      </header>

      {/* Upload zone */}
      <div
        className={`bg-surface p-8 mb-8 border border-dashed rounded-xl text-center transition-colors shadow-sm ${
          dragOver ? "border-accent bg-surface2" : "border-[#C8CED8]"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) onFile(f);
        }}
      >
        <div className="text-[14px] text-textSecondary mb-4">
          Drag and drop a CSV here, or
        </div>
        <div className="flex items-center justify-center gap-3">
          <label className="btn-ghost cursor-pointer bg-white">
            Choose CSV
            <input
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
            />
          </label>
          <button className="btn-primary" onClick={runDemo} disabled={running}>
            {running ? "Processing…" : "Load Demo Feed"}
          </button>
        </div>
      </div>

      {/* Pipeline progress */}
      {job && (
        <div className="panel p-6 mb-8">
          <h2 className="section-header">Intelligence Pipeline Progress</h2>
          <div className="flex flex-col gap-2">
            {job.stages.map((s, i) => (
              <div key={i} className="flex items-center gap-3 text-[13px]">
                <StageIcon status={s.status} />
                <span className="w-44 text-textPrimary font-medium">{`Stage ${i + 1}: ${s.name}`}</span>
                <span className="text-textSecondary flex-1">{s.detail}</span>
                {s.duration_ms !== null && (
                  <span className="font-mono text-[11px] text-textMuted">
                    {s.duration_ms.toFixed(0)} ms
                  </span>
                )}
              </div>
            ))}
          </div>
          {job.status === "complete" && (
            <div className="mt-4 text-[12px] font-mono text-primary font-medium p-3 bg-surface2 rounded-md border border-border">
              ✓ Pipeline Complete · {String((job.summary as any).flagged ?? "—")} entities flagged ·
              SHA-256 {String((job.summary as any).sha256 ?? "").slice(0, 16)}…
            </div>
          )}
        </div>
      )}

      {stats && (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-5 gap-4 mb-8">
            <StatCard label="Rows" value={stats.rows.toLocaleString()} />
            <StatCard label="Features" value={stats.features.toLocaleString()} />
            <StatCard label="Mule Entities" value={String(stats.mule_count)} color="#C53030" />
            <StatCard label="Imbalance" value={stats.imbalance_ratio} color="#B7791F" />
            <StatCard label="Sparsity" value={`${stats.sparsity_pct}%`} color="#2D7A9C" />
          </div>

          <div className="grid gap-6 mb-8" style={{ gridTemplateColumns: "320px 1fr" }}>
            {/* Feature type doughnut */}
            <div className="panel p-6">
              <h2 className="section-header">Feature Types</h2>
              <Doughnut stats={stats} />
            </div>

            {/* Domain hint table */}
            <div className="panel p-0 overflow-x-auto">
              <div className="p-6 pb-2">
                <h2 className="section-header mb-0">18 Domain-Hint Features</h2>
              </div>
              <table className="w-full text-left text-[12px]">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-textSecondary border-b border-border bg-surface2">
                    <th className="px-4 py-2">Feature</th>
                    <th className="px-4 py-2">Decoded Meaning</th>
                    <th className="px-4 py-2 text-right">Mule Mean</th>
                    <th className="px-4 py-2 text-right">Legit Mean</th>
                    <th className="px-4 py-2 text-right">KS</th>
                    <th className="px-4 py-2">Power</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.domain_hint_features.map((h, i) => (
                    <tr key={h.feature} className="border-b border-border/50 hover:bg-surface2 transition-colors" style={{ backgroundColor: i % 2 ? "#FAFBFC" : "transparent" }}>
                      <td className="px-4 py-2.5 font-mono text-accent font-medium">{h.feature}</td>
                      <td className="px-4 py-2.5 text-textPrimary">{h.decoded_meaning}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-textSecondary">
                        {h.mule_mean ?? "—"}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-textSecondary">
                        {h.legit_mean ?? "—"}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-textSecondary">
                        {h.ks_stat ?? "—"}
                      </td>
                      <td className="px-4 py-2.5">
                        <PowerBadge power={h.discriminative_power} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function StageIcon({ status }: { status: string }) {
  if (status === "done")
    return <span className="text-low font-bold animate-fadeIn">✓</span>;
  if (status === "running")
    return <span className="inline-block h-3 w-3 rounded-full border-2 border-accent border-t-transparent animate-spin" />;
  if (status === "error") return <span className="text-critical font-bold">✕</span>;
  return <span className="text-textMuted font-bold">○</span>;
}

function StatCard({ label, value, color = "#1B2A4A" }: { label: string; value: string; color?: string }) {
  return (
    <div className="panel p-4">
      <div className="text-[11px] uppercase tracking-wider text-textSecondary font-medium">{label}</div>
      <div className="font-display text-[26px] font-bold mt-1" style={{ color }}>
        {value}
      </div>
    </div>
  );
}

function PowerBadge({ power }: { power: string }) {
  const c = power === "High" ? "#C53030" : power === "Medium" ? "#B7791F" : power === "Low" ? "#997B2F" : "#5A6B7F";
  return (
    <span className="font-mono text-[11px] font-medium rounded-md px-2 py-0.5" style={{ color: c, backgroundColor: `${c}15`, border: `1px solid ${c}30` }}>
      {power}
    </span>
  );
}

function Doughnut({ stats }: { stats: DatasetStats }) {
  const b = stats.feature_type_breakdown;
  const data = [
    { label: "Binary", value: b.binary, color: "#1B2A4A" },
    { label: "Low-card", value: b.low_cardinality, color: "#2D7A9C" },
    { label: "Continuous", value: b.continuous, color: "#2B6C3F" },
    { label: "Categorical", value: b.categorical, color: "#B7791F" },
  ];
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const r = 60;
  const c = 2 * Math.PI * r;
  let offset = 0;

  return (
    <div className="flex items-center gap-6">
      <svg width="160" height="160" viewBox="0 0 160 160">
        <g transform="translate(80,80) rotate(-90)">
          {data.map((d) => {
            const frac = d.value / total;
            const dash = frac * c;
            const seg = (
              <circle
                key={d.label}
                r={r}
                fill="none"
                stroke={d.color}
                strokeWidth="22"
                strokeDasharray={`${dash} ${c - dash}`}
                strokeDashoffset={-offset}
              />
            );
            offset += dash;
            return seg;
          })}
        </g>
        <text x="80" y="76" textAnchor="middle" className="fill-textPrimary font-display" fontSize="22" fontWeight="700">
          {stats.features.toLocaleString()}
        </text>
        <text x="80" y="94" textAnchor="middle" className="fill-textMuted font-mono" fontSize="10">
          FEATURES
        </text>
      </svg>
      <div className="flex flex-col gap-2">
        {data.map((d) => (
          <div key={d.label} className="flex items-center gap-2 text-[12px]">
            <span className="inline-block h-3 w-3 rounded-[3px]" style={{ background: d.color }} />
            <span className="text-textSecondary w-20 font-medium">{d.label}</span>
            <span className="font-mono text-textPrimary">{d.value.toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
