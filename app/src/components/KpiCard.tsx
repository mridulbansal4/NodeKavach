// KPI stat card — left accent border, soft shadow, rounded corners.
export default function KpiCard({
  label,
  value,
  sub,
  accent = "#2D7A9C",
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="panel p-5" style={{ borderLeft: `3px solid ${accent}` }}>
      <div className="font-display text-[11px] uppercase tracking-wider text-textSecondary font-medium">{label}</div>
      <div className="stat-value text-[36px] leading-tight mt-2">{value}</div>
      {sub && <div className="font-mono text-[11px] text-textMuted mt-1">{sub}</div>}
    </div>
  );
}
