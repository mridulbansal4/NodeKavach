import { NavLink } from "react-router-dom";

const NAV = [
  { to: "/", label: "Operations Center", icon: GridIcon, end: true },
  { to: "/investigation", label: "Investigation", icon: SearchIcon },
  { to: "/metrics", label: "Analytics", icon: ChartIcon },
  { to: "/dataset", label: "Data Feed", icon: DbIcon },
];

export default function Sidebar() {
  return (
    <aside className="w-[220px] shrink-0 bg-surface border-r border-border flex flex-col">
      <div className="px-5 py-5 border-b border-border">
<<<<<<< HEAD
        <div className="font-display font-bold text-[20px] tracking-tight text-primary">
          MULE<span className="text-accent">FLAGGER</span>
=======
        <div className="font-display font-bold text-[20px] tracking-tight text-textPrimary">
          Node<span className="text-accent">Kavach</span>
>>>>>>> 7846f3af036684a27dd6db0a81f46b0878b43163
        </div>
        <div className="font-mono text-[9px] text-textMuted mt-1 tracking-[0.12em] uppercase">
          Financial Intelligence Platform
        </div>
      </div>
      <nav className="flex-1 py-3">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-5 py-2.5 text-[13px] font-medium border-l-2 transition-colors duration-150 ${
                isActive
                  ? "border-accent bg-surface2 text-primary"
                  : "border-transparent text-textSecondary hover:bg-surface2 hover:text-primary"
              }`
            }
          >
            <Icon />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-5 py-4 border-t border-border">
        <div className="font-mono text-[10px] text-textMuted">BOI × IITH</div>
        <div className="font-mono text-[10px] text-textMuted">CyberShield 2026 · PS2</div>
      </div>
    </aside>
  );
}

function GridIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <rect x="1" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.2" />
      <rect x="9" y="1" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.2" />
      <rect x="1" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.2" />
      <rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}
function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.2" />
      <path d="M11 11l4 4" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}
function ChartIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M1 15V1M1 15h14" stroke="currentColor" strokeWidth="1.2" />
      <rect x="4" y="8" width="2.5" height="5" rx="0.5" fill="currentColor" />
      <rect x="8" y="5" width="2.5" height="8" rx="0.5" fill="currentColor" />
      <rect x="12" y="10" width="2.5" height="3" rx="0.5" fill="currentColor" />
    </svg>
  );
}
function DbIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <ellipse cx="8" cy="3" rx="6" ry="2.2" stroke="currentColor" strokeWidth="1.2" />
      <path d="M2 3v10c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2V3" stroke="currentColor" strokeWidth="1.2" />
      <path d="M2 8c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}
