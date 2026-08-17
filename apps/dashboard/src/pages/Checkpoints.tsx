import { useEffect, useState } from "react";
import { listCheckpoints, type Checkpoint } from "../api/client";
import ResumeCaptchaButton from "../components/ResumeCaptchaButton";

export default function Checkpoints() {
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);

  function refresh() {
    listCheckpoints(false).then(setCheckpoints);
  }

  useEffect(refresh, []);

  return (
    <div>
      <h2>Pending Checkpoints</h2>
      {checkpoints.length === 0 && <p>No checkpoints awaiting resolution.</p>}
      {checkpoints.map((checkpoint) => (
        <div className="card" key={checkpoint.id}>
          <p>Reason: <span className="badge badge-paused_captcha">{checkpoint.reason}</span></p>
          <p>Run: {checkpoint.run_id}</p>
          <p>Page: {checkpoint.page_url}</p>
          <ResumeCaptchaButton checkpointId={checkpoint.id} onResumed={refresh} />
        </div>
      ))}
    </div>
  );
}
