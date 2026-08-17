import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getReport } from "../api/client";

export default function ReportViewer() {
  const { runId } = useParams<{ runId: string }>();
  const [markdown, setMarkdown] = useState<string>("");

  useEffect(() => {
    if (!runId) return;
    getReport(runId).then((res) => setMarkdown(res.markdown));
  }, [runId]);

  if (!runId) return <p>No run selected.</p>;

  return (
    <div>
      <h2>Report for {runId.slice(0, 8)}</h2>
      <div className="card">
        <pre className="log-stream">{markdown || "Loading report..."}</pre>
      </div>
    </div>
  );
}
