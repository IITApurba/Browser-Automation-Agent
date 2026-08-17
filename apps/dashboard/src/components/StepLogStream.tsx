import { useEffect, useRef, useState } from "react";
import { streamUrl } from "../api/client";

interface StepEvent {
  index: number;
  type: string;
  status: string;
  output: unknown;
}

export default function StepLogStream({ runId }: { runId: string }) {
  const [lines, setLines] = useState<string[]>([]);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const source = new EventSource(streamUrl(runId));
    sourceRef.current = source;

    source.addEventListener("step", (event) => {
      const data: StepEvent = JSON.parse((event as MessageEvent).data);
      setLines((prev) => [...prev, `[${data.index}] ${data.type} — ${data.status}`]);
    });

    source.addEventListener("done", (event) => {
      const data = JSON.parse((event as MessageEvent).data);
      setLines((prev) => [...prev, `-- run finished: ${data.status} --`]);
      source.close();
    });

    source.onerror = () => {
      source.close();
    };

    return () => source.close();
  }, [runId]);

  return (
    <div className="log-stream">
      {lines.length === 0 ? "Waiting for steps..." : lines.join("\n")}
    </div>
  );
}
