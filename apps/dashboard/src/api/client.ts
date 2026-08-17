const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000";

export interface Task {
  id: string;
  name: string;
  goal: string;
  extraction_schema: Record<string, unknown> | null;
  created_at: string;
}

export interface Run {
  id: string;
  task_id: string;
  status: string;
  plan: Record<string, unknown> | null;
  current_step_index: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Step {
  id: string;
  run_id: string;
  index: number;
  type: string;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  status: string;
  dom_fingerprint: string | null;
  screenshot_path: string | null;
  created_at: string;
}

export interface Checkpoint {
  id: string;
  run_id: string;
  step_id: string | null;
  reason: string;
  page_url: string;
  extracted_so_far: unknown;
  resolved_at: string | null;
  resolved_by: string | null;
  created_at: string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${await response.text()}`);
  }
  return response.json() as Promise<T>;
}

export function listTasks(): Promise<Task[]> {
  return request("/tasks");
}

export function createTask(payload: { name: string; goal: string; extraction_schema?: Record<string, unknown> }): Promise<Task> {
  return request("/tasks", { method: "POST", body: JSON.stringify(payload) });
}

export function listRuns(): Promise<Run[]> {
  return request("/runs");
}

export function getRun(runId: string): Promise<Run> {
  return request(`/runs/${runId}`);
}

export function getSteps(runId: string): Promise<Step[]> {
  return request(`/runs/${runId}/steps`);
}

export function listCheckpoints(resolved?: boolean): Promise<Checkpoint[]> {
  const query = resolved === undefined ? "" : `?resolved=${resolved}`;
  return request(`/checkpoints${query}`);
}

export function resumeCheckpoint(checkpointId: string, resolvedBy?: string): Promise<Checkpoint> {
  return request(`/checkpoints/${checkpointId}/resume`, {
    method: "POST",
    body: JSON.stringify({ resolved_by: resolvedBy ?? null }),
  });
}

export function getReport(runId: string): Promise<{ run_id: string; markdown: string }> {
  return request(`/runs/${runId}/report`);
}

export function streamUrl(runId: string): string {
  return `${API_BASE_URL}/runs/${runId}/stream`;
}

export function createRun(taskId: string): Promise<Run> {
  return request(`/tasks/${taskId}/runs`, { method: "POST", body: JSON.stringify({}) });
}
