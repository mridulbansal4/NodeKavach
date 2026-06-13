import { useEffect, useState } from "react";
import type { Severity } from "../api/types";
import { scoreColor } from "../lib/severity";

// Risk gauge: 240° SVG arc, colour-coded by score, enterprise-style.
const START_ANGLE = 150;
const SWEEP = 240;

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const a = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}

function arcPath(cx: number, cy: number, r: number, start: number, end: number) {
  const s = polar(cx, cy, r, end);
  const e = polar(cx, cy, r, start);
  const large = end - start <= 180 ? 0 : 1;
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 0 ${e.x} ${e.y}`;
}

export default function RiskGauge({
  score,
  severity,
  size = 240,
}: {
  score: number;
  severity: Severity;
  size?: number;
}) {
  const [animated, setAnimated] = useState(0);

  useEffect(() => {
    const start = performance.now();
    const dur = 600;
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      setAnimated(score * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [score]);

  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 18;
  const stroke = 14;
  const color = scoreColor(score);

  const fullLen = (SWEEP / 360) * 2 * Math.PI * r;
  const fraction = Math.max(0, Math.min(1, animated / 100));
  const trackPath = arcPath(cx, cy, r, START_ANGLE, START_ANGLE + SWEEP);

  return (
    <div className="relative flex flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size * 0.82} viewBox={`0 0 ${size} ${size * 0.82}`}>
        {/* track */}
        <path
          d={trackPath}
          fill="none"
          stroke="#E2E6ED"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        {/* value arc */}
        <path
          d={trackPath}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={fullLen}
          strokeDashoffset={fullLen * (1 - fraction)}
          style={{ transition: "stroke 200ms linear" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ top: -size * 0.06 }}>
        <span
          className="font-display font-bold leading-none"
          style={{ fontSize: 64, color }}
        >
          {Math.round(animated)}
        </span>
        <span className="font-body text-[11px] text-textMuted mt-1">/ 100 ENTITY RISK</span>
        <span
          className="font-mono text-[13px] uppercase tracking-[0.15em] mt-2 font-medium"
          style={{ color }}
        >
          {severity}
        </span>
      </div>
    </div>
  );
}
