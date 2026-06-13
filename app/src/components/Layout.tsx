import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import StatusBar from "./StatusBar";

// Page-level grid: fixed sidebar | (scrolling content + status bar).
export default function Layout() {
  return (
    <div className="grid h-full" style={{ gridTemplateColumns: "220px 1fr" }}>
      <Sidebar />
      <div className="grid h-full overflow-hidden" style={{ gridTemplateRows: "1fr auto" }}>
        <main className="overflow-y-auto bg-bg">
          <div className="mx-auto max-w-content p-6">
            <Outlet />
          </div>
        </main>
        <StatusBar />
      </div>
    </div>
  );
}
