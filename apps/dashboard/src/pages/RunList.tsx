import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listRuns, type Run } from "../api/client";

export default function RunList() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listRuns().then(setRuns).catch((err) => setError(String(err)));
  }, []);

  return (
    <div>
      <h2>Runs</h2>
      {error && <p className="badge badge-failed">{error}</p>}
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Run</th>
              <th>Task</th>
              <th>Status</th>
              <th>Step</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td><Link to={`/runs/${run.id}`}>{run.id.slice(0, 8)}</Link></td>
                <td>{run.task_id.slice(0, 8)}</td>
                <td><span className={`badge badge-${run.status}`}>{run.status}</span></td>
                <td>{run.current_step_index}</td>
                <td>{new Date(run.updated_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
