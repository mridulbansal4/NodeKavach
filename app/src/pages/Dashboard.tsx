import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { CaseRecord, MetricsResponse } from "../api/types";
import KpiCard from "../components/KpiCard";
import SeverityBadge from "../components/SeverityBadge";
import { typologyLabel } from "../lib/severity";

export default function Dashboard() {
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.listCases(), api.metrics().catch(() => null)])
      .then(([c, m]) => {
        setCases(c);
        setMetrics(m);
      })
      .finally(() => setLoading(false));
  }, []);

  const total = cases.length;
  const mules = cases.filter((c) => c.severity === "CRITICAL" || c.severity === "HIGH").length;
  const avgRisk =
    total > 0 ? Math.round(cases.reduce((s, c) => s + c.risk_score, 0) / total) : 0;
  const prAuc = metrics?.model_b?.pr_auc ?? null;

  return (
    <div>
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-[28px] font-bold text-textPrimary">Dashboard</h1>
          <p className="text-[13px] text-textSecondary">
            Fraud intelligence operating system — every alert has a story.
          </p>
        </div>
        <div className="font-mono text-[12px] text-textMuted">BOI × IITH Hackathon 2026</div>
      </header>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <KpiCard label="Accounts Analysed" value={String(total)} sub="demo + uploaded cases" accent="#00D4FF" />
        <KpiCard label="Mule Accounts Flagged" value={String(mules)} sub="CRITICAL + HIGH severity" accent="#FF3B30" />
        <KpiCard label="Average Risk Score" value={String(avgRisk)} sub="across all cases" accent="#FF9500" />
        <KpiCard
          label="Model PR-AUC"
          value={prAuc !== null ? prAuc.toFixed(3) : "—"}
          sub="Model B · primary metric"
          accent="#34C759"
        />
      </div>

      <section>
        <h2 className="section-header">Recent Cases</h2>
        <div className="panel overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[11px] uppercase tracking-wider text-textSecondary border-b border-border">
                <Th>Case ID</Th>
                <Th>Risk</Th>
                <Th>Severity</Th>
                <Th>Typology</Th>
                <Th>Standing</Th>
                <Th>Occupation</Th>
                <Th>Action</Th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-textMuted text-[13px]">
                    Loading cases…
                  </td>
                </tr>
              )}
              {!loading && cases.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-textMuted text-[13px]">
                    No accounts analysed yet. Load the BOI dataset to begin.
                  </td>
                </tr>
              )}
              {cases.map((c, i) => (
                <tr
                  key={c.case_id}
                  className="border-b border-border/50 hover:bg-border/40 transition-colors"
                  style={{ backgroundColor: i % 2 ? "#0A1828" : "transparent" }}
                >
                  <Td>
                    <span className="font-mono text-[13px] text-textPrimary">{c.case_id}</span>
                    {c.is_demo && (
                      <span className="ml-2 font-mono text-[10px] text-accent">DEMO</span>
                    )}
                  </Td>
                  <Td>
                    <span className="font-display font-semibold">{c.risk_score}</span>
                  </Td>
                  <Td>
                    <SeverityBadge severity={c.severity} size="sm" />
                  </Td>
                  <Td className="text-[13px] text-textSecondary">{typologyLabel(c.typology)}</Td>
                  <Td className="font-mono text-[12px] text-textSecondary">{c.account_standing ?? "—"}</Td>
                  <Td className="text-[13px] text-textSecondary">{c.occupation ?? "—"}</Td>
                  <Td>
                    <Link
                      to={c.is_demo ? `/investigation/${c.case_id}` : `/report/${c.case_id}`}
                      className="font-body text-[12px] text-accent hover:underline"
                    >
                      View Investigation →
                    </Link>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-4 py-3 font-medium">{children}</th>;
}
function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-4 py-3 ${className}`}>{children}</td>;
}
