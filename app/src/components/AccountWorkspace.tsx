import type { AccountAnalysis } from "../api/types";
import { typologyLabel } from "../lib/severity";
import RiskGauge from "./RiskGauge";
import BehaviouralBars from "./BehaviouralBars";
import ShapWaterfall from "./ShapWaterfall";

// Investigation workspace: gauge + classification + behavioural + SHAP.
export default function AccountWorkspace({ a }: { a: AccountAnalysis }) {
  return (
    <div className="flex flex-col gap-6">
      {/* gauge + typology */}
      <div className="grid gap-6" style={{ gridTemplateColumns: "280px 1fr" }}>
        <div className="panel p-6 flex flex-col items-center justify-center">
          <RiskGauge score={a.risk_score} severity={a.severity} />
          {a.f3912_flag && (
            <div className="mt-3 rounded-md border border-critical/30 bg-critical/5 px-3 py-1.5 text-[12px] font-mono text-critical">
              ⚠ Matches fraud registry (F3912 = 1)
            </div>
          )}
        </div>

        <div className="panel p-6">
          <h3 className="section-header">Fraud Operation Classification</h3>
          {a.classification.typology ? (
            <>
              <div className="flex items-baseline gap-3">
                <span className="font-display text-[24px] font-semibold text-textPrimary">
                  {typologyLabel(a.classification.typology)}
                </span>
                <span className="font-mono text-[13px] text-accent font-medium">
                  {Math.round(a.classification.confidence * 100)}% confidence
                </span>
              </div>
              <p className="mt-2 text-[13px] text-textSecondary leading-relaxed">
                {a.classification.typology_description}
              </p>
              <div className="mt-4">
                <div className="label-mono mb-2">MATCHED INDICATORS</div>
                <ul className="flex flex-col gap-1.5">
                  {a.classification.matched_indicators.map((m, i) => (
                    <li key={i} className="flex items-start gap-2 text-[13px] text-textPrimary">
                      <span className="text-accent mt-0.5">▸</span>
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          ) : (
            <div className="text-[14px] text-low font-medium">
              Entity cleared — no fraud pattern detected.
            </div>
          )}
          <div className="mt-5 grid grid-cols-2 gap-3 text-[12px]">
            <ProfileItem label="Occupation" value={a.account_profile.occupation} />
            <ProfileItem label="Account Standing" value={a.account_profile.account_standing} />
            <ProfileItem label="Account Holder Age" value={fmt(a.account_profile.age)} />
            <ProfileItem label="Account Tenure" value={fmt(a.account_profile.account_tenure)} />
          </div>
        </div>
      </div>

      {/* behavioural + shap */}
      <div className="grid gap-6" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div className="panel p-6">
          <h3 className="section-header">Behavioural Risk Indicators</h3>
          <BehaviouralBars indicators={a.behavioural_indicators} />
        </div>
        <div className="panel p-6">
          <h3 className="section-header">SHAP Attribution — Top 10</h3>
          <ShapWaterfall features={a.shap_values} />
        </div>
      </div>
    </div>
  );
}

function ProfileItem({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="panel-2 px-3 py-2 rounded-lg">
      <div className="text-textMuted uppercase tracking-wider text-[10px] font-medium">{label}</div>
      <div className="font-mono text-[13px] text-textPrimary mt-0.5">{value ?? "—"}</div>
    </div>
  );
}

function fmt(v: number | null): string | null {
  return v === null || v === undefined ? null : String(v);
}
