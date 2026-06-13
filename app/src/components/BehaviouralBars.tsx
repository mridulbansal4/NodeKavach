import type { BehaviouralIndicator } from "../api/types";

// 8 behavioural risk indicators as labelled progress bars (0-1 fill).
// Bar colour shifts with magnitude: low=green, mid=amber, high=red.

function barColor(v: number): string {
  if (v >= 0.7) return "#FF3B30";
  if (v >= 0.45) return "#FF9500";
  if (v >= 0.25) return "#FFCC00";
  return "#34C759";
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
            <div className="h-2 w-full rounded-sm bg-rowAlt overflow-hidden">
              <div
                className="h-full rounded-sm transition-all duration-500"
                style={{ width: `${pct}%`, backgroundColor: color }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
