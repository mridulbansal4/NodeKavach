import type { ShapFeature } from "../api/types";

// Horizontal SHAP waterfall — muted red/green bars, enterprise palette.
export default function ShapWaterfall({ features }: { features: ShapFeature[] }) {
  if (!features.length) {
    return <div className="text-textMuted text-[13px]">No SHAP attributions available.</div>;
  }
  const maxAbs = Math.max(...features.map((f) => Math.abs(f.shap_value)), 1e-6);

  return (
    <div className="flex flex-col gap-1.5">
      {features.map((f) => {
        const pct = (Math.abs(f.shap_value) / maxAbs) * 50;
        const inc = f.direction === "increases_risk";
        const color = inc ? "#C53030" : "#2B6C3F";
        return (
          <div key={f.raw_feature} className="grid grid-cols-[180px_1fr_64px] items-center gap-2">
            <div className="truncate text-[13px] text-textSecondary" title={f.feature}>
              {f.feature}
            </div>
            <div className="relative h-5 bg-surface2 rounded-md">
              {/* centre axis */}
              <div className="absolute left-1/2 top-0 h-full w-px bg-border" />
              <div
                className="absolute top-0 h-full rounded-md"
                style={{
                  backgroundColor: `${color}CC`,
                  width: `${pct}%`,
                  left: inc ? "50%" : `${50 - pct}%`,
                }}
              />
            </div>
            <div
              className="text-right font-mono text-[12px]"
              style={{ color }}
            >
              {f.shap_value >= 0 ? "+" : ""}
              {f.shap_value.toFixed(2)}
            </div>
          </div>
        );
      })}
      <div className="mt-2 flex items-center gap-4 text-[11px] text-textMuted">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-3 rounded-sm" style={{ background: "#C53030" }} />
          increases risk
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-3 rounded-sm" style={{ background: "#2B6C3F" }} />
          reduces risk
        </span>
      </div>
    </div>
  );
}
