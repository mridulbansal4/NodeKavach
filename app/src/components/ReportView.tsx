// Renders an AI investigation report. Splits on numbered/echoed section headers
// and styles each header in the analyst section style. Tolerant of both the
// Ollama markdown (**HEADER**) and the deterministic "1. HEADER" fallback.

const SECTIONS = [
  "EXECUTIVE SUMMARY",
  "RISK ASSESSMENT",
  "KEY FRAUD INDICATORS",
  "MULE TYPOLOGY ASSESSMENT",
  "ACCOUNT PROFILE ANALYSIS",
  "RECOMMENDED ACTIONS",
  "REGULATORY NOTE",
];

interface Block {
  header: string;
  body: string;
}

function parse(report: string): Block[] {
  const lines = report.split("\n");
  const blocks: Block[] = [];
  let current: Block | null = null;

  const matchHeader = (line: string): string | null => {
    const clean = line.replace(/[*#]/g, "").replace(/^\s*\d+\.\s*/, "").trim().toUpperCase();
    return SECTIONS.find((s) => clean === s || clean.startsWith(s)) ?? null;
  };

  for (const line of lines) {
    const h = matchHeader(line);
    if (h) {
      if (current) blocks.push(current);
      current = { header: h, body: "" };
    } else if (current) {
      current.body += line + "\n";
    }
  }
  if (current) blocks.push(current);
  if (!blocks.length) blocks.push({ header: "REPORT", body: report });
  return blocks;
}

export default function ReportView({ report }: { report: string }) {
  const blocks = parse(report);
  return (
    <div className="flex flex-col gap-6">
      {blocks.map((b, i) => (
        <section key={i} className="animate-fadeIn">
          <h3 className="section-header text-[14px]">{b.header}</h3>
          <div className="text-[13px] leading-relaxed text-textPrimary whitespace-pre-wrap font-body">
            {b.body.trim().replace(/\*\*/g, "")}
          </div>
        </section>
      ))}
    </div>
  );
}
