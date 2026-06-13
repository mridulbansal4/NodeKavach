// KPI stat card with a top border in a given accent colour.
export default function KpiCard({
  label,
  value,
  sub,
  accent = "#00D4FF",
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="panel p-5" style={{ borderTop: `2px solid ${accent}` }}>
      <div className="font-body text-[12px] uppercase tracking-wider text-textSecondary">{label}</div>
      <div className="stat-value text-[40px] leading-tight mt-2">{value}</div>
      {sub && <div className="font-mono text-[11px] text-textMuted mt-1">{sub}</div>}
    </div>
  );
}
