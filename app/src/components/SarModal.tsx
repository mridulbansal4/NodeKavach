import type { AccountAnalysis } from "../api/types";
import { typologyLabel } from "../lib/severity";

// SAR / STR draft modal — enterprise style overlay.
export default function SarModal({
  analysis,
  onClose,
}: {
  analysis: AccountAnalysis;
  onClose: () => void;
}) {
  const a = analysis;
  const draft = `SUSPICIOUS TRANSACTION REPORT (STR) — DRAFT
Filed under the Prevention of Money Laundering Act, 2002 (FIU-IND)

REPORTING ENTITY      : Bank of India
SUBJECT ACCOUNT       : ${a.case_id}
RISK SCORE / SEVERITY : ${a.risk_score}/100 (${a.severity})
MULE TYPOLOGY         : ${typologyLabel(a.classification.typology)} (${Math.round(
    a.classification.confidence * 100
  )}% confidence)
FRAUD REGISTRY MATCH  : ${a.f3912_flag ? "YES (F3912 = 1)" : "No"}
MODEL                 : ${a.model_used} (SHAP-attributed)

GROUNDS FOR SUSPICION
${a.classification.matched_indicators.map((m) => `  - ${m}`).join("\n") || "  - Elevated model risk score"}

TOP CONTRIBUTING SIGNALS (SHAP)
${a.shap_values
  .slice(0, 5)
  .map(
    (s) =>
      `  - ${s.feature} (${s.raw_feature}): ${s.shap_value >= 0 ? "+" : ""}${s.shap_value.toFixed(
        3
      )} (${s.direction === "increases_risk" ? "increases" : "reduces"} risk)`
  )
  .join("\n")}

ACCOUNT PROFILE
  Occupation       : ${a.account_profile.occupation ?? "unknown"}
  Account standing : ${a.account_profile.account_standing ?? "unknown"}
  Account age      : ${a.account_profile.age ?? "unknown"}

RECOMMENDED ACTION    : ${
    a.severity === "CRITICAL"
      ? "Immediate freeze + STR filing"
      : a.severity === "HIGH"
      ? "Step-up authentication + STR draft"
      : a.severity === "MEDIUM"
      ? "Enhanced monitoring"
      : "Routine logging"
  }

Prepared by MULEFLAGGER Financial Intelligence Platform · BOI × IITH CyberShield Hackathon 2026`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/25 p-6 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-surface w-full max-w-2xl max-h-[80vh] overflow-y-auto rounded-xl shadow-xl border border-border"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <h3 className="section-header mb-0 text-[14px]">SAR / STR Draft</h3>
          <button className="btn-ghost" onClick={onClose}>
            Close
          </button>
        </div>
        <pre className="px-5 py-4 font-mono text-[12px] leading-relaxed text-textPrimary whitespace-pre-wrap">
          {draft}
        </pre>
        <div className="flex justify-end gap-2 border-t border-border px-5 py-3">
          <button
            className="btn-primary"
            onClick={() => navigator.clipboard.writeText(draft)}
          >
            Copy SAR Draft
          </button>
        </div>
      </div>
    </div>
  );
}
