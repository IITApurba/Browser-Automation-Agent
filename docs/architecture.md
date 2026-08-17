# Architecture

## Overview

```
apps/dashboard (React)  <-->  apps/api (FastAPI)  <-->  packages/agent (LangGraph)
                                      |                        |
                                      v                        v
                                 packages/db (Postgres)   packages/browser_tools (Playwright)
                                      ^                        ^
                                      |                        |
                              packages/mcp_server  ------------+
```

## Data model (Postgres, `packages/db/models.py`)

- `Task` — a named goal + optional extraction schema.
- `Run` — one execution of a Task; tracks `status` (pending/running/paused_captcha/paused_error/completed/failed), `plan`, `current_step_index`, `error_message`.
- `Step` — one node execution within a run (index, type, input/output JSON, status, dom_fingerprint, screenshot_path).
- `Checkpoint` — a paused run (captcha/error/manual), storing `storage_state`, `extracted_so_far`, `scratchpad_memory` so a run can be resumed.
- `ExtractedData`, `Report`, `Credential`, `Session`, `MemoryEntry` — supporting tables for extraction output, generated reports, stored auth, and scratchpad persistence across a run.

## Agent graph (`packages/agent/graph.py`)

LangGraph `StateGraph` over `AgentState` (TypedDict): `planner -> worker -> {captcha_handler | replanner | advance | reporter}`. The planner emits a JSON subtask plan from an LLM (or the deterministic "fake" provider for tests). `worker` executes one subtask via `BrowserToolkit` and runs CAPTCHA detection after every action. `route_after_worker` decides whether to advance, retry via `replanner`, hand off to `captcha_handler`, or finish at `reporter`.

## Execution service (`packages/agent/runner.py`)

`GraphRunner.run(...)` drives the compiled graph with `.astream()`, persisting a `Step` row per node transition and keeping `Run.status`/`current_step_index` in sync. A `captcha_handler` transition creates a `Checkpoint` and pauses the run. `GraphRunner.resume_from_checkpoint(...)` reconstructs `AgentState` from a stored checkpoint and drives the worker/routing loop directly (bypassing `.astream()`, since resuming a compiled LangGraph mid-node isn't natively supported without a checkpoint-saver) until the run reaches a terminal state.

## MCP server (`packages/mcp_server/`)

`tool_definitions.py` exposes `BrowserToolkit` methods 1:1 as thin async functions (no reimplemented logic); `server.py` wraps each in a `FastMCP` `@mcp.tool()`. `run_stdio.py` runs the server over stdio for MCP-compatible clients (e.g. Claude Code).

## API (`apps/api/`)

FastAPI app exposing:
- `POST/GET /tasks`, `GET /tasks/{id}`
- `POST /tasks/{id}/runs`, `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/steps`, `GET /runs/{id}/report`, `GET /runs/{id}/report/download`
- `GET /checkpoints?resolved=false`, `POST /checkpoints/{id}/resume`
- `GET /runs/{id}/stream` — SSE, polling the `steps` table

## Dashboard (`apps/dashboard/`)

React + Vite + TypeScript, no UI framework. Pages: Run list, Run detail (live SSE log + screenshots), Checkpoints (resume captcha-paused runs), Report viewer.
