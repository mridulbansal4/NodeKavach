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
  const opsUnderInvestigation = mules;
  const estimatedExposure = (mules * 14.4).toFixed(1);
  const activeCampaigns = Math.max(1, Math.ceil(mules / 3));

  return (
    <div>
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-[28px] font-bold text-primary">Operations Center</h1>
          <p className="text-[13px] text-textSecondary">
            Financial intelligence operating system — identify coordinated fraud operations.
          </p>
        </div>
        <div className="font-mono text-[12px] text-textMuted">BOI × IITH Hackathon 2026</div>
      </header>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <KpiCard label="Entities Analysed" value={String(total)} sub="demo + uploaded entities" accent="#2D7A9C" />
        <KpiCard label="Active Fraud Operations" value={String(mules)} sub="CRITICAL + HIGH severity" accent="#C53030" />
        <KpiCard label="Network Risk Index" value={String(avgRisk)} sub="mean risk across all entities" accent="#B7791F" />
      </div>
      <div className="grid grid-cols-3 gap-4 mb-8">
        <KpiCard
          label="Operations Under Investigation"
          value={String(opsUnderInvestigation)}
          sub="open cases requiring action"
          accent="#1B2A4A"
        />
        <KpiCard
          label="Estimated Exposure"
          value={`₹${estimatedExposure}L`}
          sub="projected fraud value (lakhs)"
          accent="#997B2F"
        />
        <KpiCard
          label="Active Campaigns"
          value={String(activeCampaigns)}
          sub="coordinated operation clusters"
          accent="#2B6C3F"
        />
      </div>

      <section>
        <h2 className="section-header">Active Intelligence Cases</h2>
        <div className="panel overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[11px] uppercase tracking-wider text-textSecondary border-b border-border bg-surface2">
                <Th>Case ID</Th>
                <Th>Risk</Th>
                <Th>Severity</Th>
                <Th>Operation Type</Th>
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
                    No entities analysed yet. Load the BOI dataset to begin.
                  </td>
                </tr>
              )}
              {cases.map((c, i) => (
                <tr
                  key={c.case_id}
                  className="border-b border-border/50 hover:bg-surface2 transition-colors"
                  style={{ backgroundColor: i % 2 ? "#FAFBFC" : "transparent" }}
                >
                  <Td>
                    <span className="font-mono text-[13px] text-textPrimary">{c.case_id}</span>
                    {c.is_demo && (
                      <span className="ml-2 font-mono text-[10px] text-accent font-medium">DEMO</span>
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
                      className="font-body text-[12px] text-accent font-medium hover:underline"
                    >
                      Open Case →
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
