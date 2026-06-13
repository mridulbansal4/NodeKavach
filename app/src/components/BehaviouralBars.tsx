import type { BehaviouralIndicator } from "../api/types";

// 8 behavioural risk indicators — muted enterprise bars.
function barColor(v: number): string {
  if (v >= 0.7) return "#C53030";
  if (v >= 0.45) return "#B7791F";
  if (v >= 0.25) return "#997B2F";
  return "#2B6C3F";
}

export default function BehaviouralBars({ indicators }: { indicators: BehaviouralIndicator[] }) {
  return (
    <div className="grid grid-cols-1 gap-3">
      {indicators.map((ind) => {
        const color = barColor(ind.value);
        const pct = Math.round(ind.value * 100);
        return (
          <div key={ind.key} title={ind.description}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[13px] text-textSecondary">{ind.label}</span>
              <span className="font-mono text-[11px]" style={{ color }}>
                {pct}% <span className="text-textMuted">[{ind.source_feature}]</span>
              </span>
            </div>
            <div className="h-2 w-full rounded-md bg-surface2 overflow-hidden">
              <div
                className="h-full rounded-md transition-all duration-500"
                style={{ width: `${pct}%`, backgroundColor: color }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
