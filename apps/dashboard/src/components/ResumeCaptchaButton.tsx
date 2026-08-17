import { useState } from "react";
import { resumeCheckpoint } from "../api/client";

export default function ResumeCaptchaButton({ checkpointId, onResumed }: { checkpointId: string; onResumed?: () => void }) {
  const [busy, setBusy] = useState(false);

  async function handleClick() {
    setBusy(true);
    try {
      await resumeCheckpoint(checkpointId, "dashboard-user");
      onResumed?.();
    } finally {
      setBusy(false);
    }
  }

  return (
    <button onClick={handleClick} disabled={busy}>
      {busy ? "Resuming..." : "Resume"}
    </button>
  );
}
