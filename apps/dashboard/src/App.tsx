import { NavLink, Route, Routes } from "react-router-dom";
import RunList from "./pages/RunList";
import RunDetail from "./pages/RunDetail";
import Checkpoints from "./pages/Checkpoints";
import ReportViewer from "./pages/ReportViewer";

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>Browser Agent</h1>
        <nav>
          <NavLink to="/" end>Runs</NavLink>
          <NavLink to="/checkpoints">Checkpoints</NavLink>
        </nav>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<RunList />} />
          <Route path="/runs/:runId" element={<RunDetail />} />
          <Route path="/checkpoints" element={<Checkpoints />} />
          <Route path="/runs/:runId/report" element={<ReportViewer />} />
        </Routes>
      </main>
    </div>
  );
}
