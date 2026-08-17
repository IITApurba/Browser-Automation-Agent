import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getRun, getSteps, type Run, type Step } from "../api/client";
import StepLogStream from "../components/StepLogStream";
import ScreenshotGallery from "../components/ScreenshotGallery";

export default function RunDetail() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<Run | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);

  useEffect(() => {
    if (!runId) return;
    getRun(runId).then(setRun);
    getSteps(runId).then(setSteps);
  }, [runId]);

  if (!runId) return <p>No run selected.</p>;

  return (
    <div>
      <h2>Run {runId.slice(0, 8)}</h2>
      {run && (
        <div className="card">
          <p>Status: <span className={`badge badge-${run.status}`}>{run.status}</span></p>
          <p>Current step index: {run.current_step_index}</p>
          {run.error_message && <p className="badge badge-failed">{run.error_message}</p>}
          <p><Link to={`/runs/${runId}/report`}>View report</Link></p>
        </div>
      )}

      <h3>Live log</h3>
      <StepLogStream runId={runId} />

      <h3>Screenshots</h3>
      <ScreenshotGallery steps={steps} />
    </div>
  );
}
