import { useEffect, useState } from "react";
import type { Severity } from "../api/types";
import { scoreColor } from "../lib/severity";

// The signature MULEFLAGGER risk gauge: a 240° SVG arc, colour-coded by score,
// with the score in 72px Space Grotesk at the centre, a severity label below,
// a severity-matched glow, and a fill animation on load (0 -> score, 600ms).

const START_ANGLE = 150; // degrees — opens at the bottom with a 120° gap
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
      const eased = 1 - Math.pow(1 - p, 3); // ease-out cubic
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
        <defs>
          <filter id="gaugeGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {/* track */}
        <path
          d={trackPath}
          fill="none"
          stroke="#1E3A5F"
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
          filter="url(#gaugeGlow)"
          style={{ transition: "stroke 200ms linear" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ top: -size * 0.06 }}>
        <span
          className="font-display font-bold leading-none"
          style={{ fontSize: 72, color }}
        >
          {Math.round(animated)}
        </span>
        <span className="font-body text-[11px] text-textMuted mt-1">/ 100 RISK SCORE</span>
        <span
          className="font-mono text-[14px] uppercase tracking-[0.2em] mt-2"
          style={{ color }}
        >
          {severity}
        </span>
      </div>
    </div>
  );
}
