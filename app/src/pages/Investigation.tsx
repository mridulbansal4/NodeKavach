import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { AccountAnalysis } from "../api/types";
import { typologyLabel } from "../lib/severity";
import SeverityBadge from "../components/SeverityBadge";
import AccountWorkspace from "../components/AccountWorkspace";
import ReportView from "../components/ReportView";
import SarModal from "../components/SarModal";

export default function Investigation() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [library, setLibrary] = useState<AccountAnalysis[]>([]);
  const [selected, setSelected] = useState<AccountAnalysis | null>(null);
  const [sarOpen, setSarOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.demoLibrary().then((lib) => {
      setLibrary(lib);
      const pick = lib.find((a) => a.case_id === id) ?? lib[0] ?? null;
      setSelected(pick);
      if (!id && pick) navigate(`/investigation/${pick.case_id}`, { replace: true });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (id && library.length) {
      const found = library.find((a) => a.case_id === id);
      if (found) setSelected(found);
    }
  }, [id, library]);

  const copyReport = () => {
    if (selected) {
      navigator.clipboard.writeText(selected.ai_report);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  return (
    <div>
      <header className="mb-6">
        <h1 className="font-display text-[28px] font-bold text-textPrimary">Investigation Center</h1>
        <p className="text-[13px] text-textSecondary">
          Pre-cached demo accounts load instantly — every flagged account gets an AI investigation narrative.
        </p>
      </header>

      <div className="grid gap-6" style={{ gridTemplateColumns: "260px 1fr" }}>
        {/* Demo account library */}
        <div className="panel p-3 self-start">
          <div className="label-mono px-2 pb-2">DEMO ACCOUNT LIBRARY</div>
          <div className="flex flex-col gap-2">
            {library.map((a) => {
              const active = selected?.case_id === a.case_id;
              return (
                <button
                  key={a.case_id}
                  onClick={() => navigate(`/investigation/${a.case_id}`)}
                  className={`text-left rounded-sm border p-3 transition-colors ${
                    active
                      ? "border-accent bg-surface2"
                      : "border-border hover:bg-surface2"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[13px] text-textPrimary">{a.case_id}</span>
                    <SeverityBadge severity={a.severity} size="sm" />
                  </div>
                  <div className="mt-1.5 flex items-center justify-between">
                    <span className="text-[12px] text-textSecondary">
                      {typologyLabel(a.classification.typology)}
                    </span>
                    <span className="font-display text-[15px] font-semibold text-textPrimary">
                      {a.risk_score}
                    </span>
                  </div>
                  {a.f3912_flag && (
                    <div className="mt-1 font-mono text-[10px] text-critical">⚠ fraud registry</div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Workspace */}
        <div>
          {selected ? (
            <div className="flex flex-col gap-6">
              <AccountWorkspace a={selected} />

              <div className="panel p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="section-header mb-0">AI Investigation Report</h3>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-textMuted">
                      source: {selected.ai_report_source}
                    </span>
                    <button className="btn-ghost" onClick={copyReport}>
                      {copied ? "Copied" : "Copy Report"}
                    </button>
                    <button className="btn-primary" onClick={() => setSarOpen(true)}>
                      Generate SAR Draft
                    </button>
                  </div>
                </div>
                <ReportView report={selected.ai_report} />
              </div>
            </div>
          ) : (
            <div className="panel p-10 text-center text-textMuted">
              No accounts analysed yet. Load the BOI dataset to begin.
            </div>
          )}
        </div>
      </div>

      {sarOpen && selected && <SarModal analysis={selected} onClose={() => setSarOpen(false)} />}
    </div>
  );
}
