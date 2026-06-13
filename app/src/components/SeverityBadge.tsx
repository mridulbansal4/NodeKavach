import type { Severity } from "../api/types";
import { severityColor } from "../lib/severity";

// Soft rectangular badge — muted colors, rounded corners, enterprise feel.
export default function SeverityBadge({
  severity,
  size = "md",
}: {
  severity: Severity;
  size?: "sm" | "md";
}) {
  const color = severityColor(severity);
  const pad = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-[12px]";
  return (
    <span
      className={`inline-block rounded-md font-mono font-medium uppercase tracking-wider ${pad} ${
        severity === "CRITICAL" ? "animate-pulseCritical" : ""
      }`}
      style={{
        color,
        backgroundColor: `${color}12`,
        border: `1px solid ${color}35`,
      }}
    >
      {severity}
    </span>
  );
}
