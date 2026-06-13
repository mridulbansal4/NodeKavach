import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Investigation from "./pages/Investigation";
import Metrics from "./pages/Metrics";
import Dataset from "./pages/Dataset";
import Report from "./pages/Report";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/investigation" element={<Investigation />} />
        <Route path="/investigation/:id" element={<Investigation />} />
        <Route path="/metrics" element={<Metrics />} />
        <Route path="/dataset" element={<Dataset />} />
        <Route path="/report/:id" element={<Report />} />
      </Route>
    </Routes>
  );
}
