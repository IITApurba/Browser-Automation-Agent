# High-Level Design

## 1. Purpose and scope

The Browser Automation Agent takes a natural-language task goal (e.g. "log into site X, find all products under $50, extract name/price/url, and give me a report") and executes it autonomously in a real browser, producing structured data and a report — while surviving the three things that break naive scrapers: DOM changes, CAPTCHAs, and crashes mid-run.

It also doubles as an MCP tool provider, so the same browser capability is available interactively inside Claude Code / Claude Desktop, not only through the autonomous loop.

## 2. System context

```
                        ┌─────────────────────────┐
   Human operator ────▶ │   Dashboard (React)      │
                        └────────────┬─────────────┘
                                     │ REST + SSE
                                     ▼
                        ┌─────────────────────────┐
                        │   API (FastAPI)          │
                        └────────────┬─────────────┘
                                     │ invokes / persists
                    ┌────────────────┼─────────────────┐
                    ▼                                   ▼
        ┌───────────────────────┐            ┌───────────────────────┐
        │  Agent (LangGraph)     │            │  PostgreSQL            │
        │  planner/worker/       │◀──────────▶│  runs, steps,          │
        │  critic/replanner/     │  persists   │  checkpoints,          │
        │  captcha/reporter      │            │  extracted_data,       │
        └───────────┬────────────┘            │  reports, sessions,    │
                    │ tool calls               │  memory_entries        │
                    ▼                          └───────────────────────┘
        ┌───────────────────────┐
        │  Browser Toolkit       │
        │  (Playwright, single   │
        │  source of truth,      │
        │  policy-gated)         │◀───────────┐
        └───────────┬────────────┘             │ same toolkit
                    ▼                          │
        ┌───────────────────────┐   ┌───────────────────────┐
        │  Chromium instance     │   │  MCP Server (stdio)    │
        └───────────────────────┘   └───────────┬───────────┘
                                                  ▼
                                       Claude Code / Claude Desktop

  Cross-cutting: packages/agent/tracing.py (span per node, OTel-shaped)
                 packages/agent/llm_cache.py (prompt-hash + semantic cache)
                 packages/agent/structured_output.py (Pydantic validate+retry)
                 packages/browser_tools/policy.py (action/URL guardrails)
                 packages/evals/ (offline eval harness -> pass rate, latency,
                 cache hit rate, cost — see README "Results")
```

## 3. Components and responsibilities

| Component | Responsibility | Does NOT do |
|---|---|---|
| **Dashboard** | Visualize runs, stream live step logs, surface paused checkpoints for human action, render reports | Never talks to Playwright or the DB directly — API only |
| **API (FastAPI)** | Task/run CRUD, launches agent execution as a background task, exposes SSE log stream, checkpoint resume endpoint | Never contains browser-automation or planning logic |
| **Agent (LangGraph)** | Decomposes a goal into a plan, executes it step by step via the toolkit, has an independent critic judge each result, detects failures/CAPTCHAs, adaptively replans, produces a report | Never talks to Postgres directly for browser state — goes through the toolkit/runner |
| **Critic (`agent/nodes/critic.py`)** | Supervisor-pattern reviewer: given the worker's result and a post-action DOM snapshot, independently judges (via a Pydantic-validated LLM verdict) whether the subtask's *intent* was met, not just whether the toolkit call didn't throw | Never executes browser actions itself — read-only judgment, feeds back into routing via `should_replan` |
| **Runner (`agent/runner.py`)** | Drives the compiled graph, persists one `Step` per transition, creates `Checkpoint`s on pause, resumes from a checkpoint | Not a queue system — v1 runs in-process via FastAPI background tasks |
| **Browser Toolkit** | The only implementation of navigate/click/type/extract/screenshot/dom_snapshot/captcha-check — used by both the agent worker and the MCP server; every action passes an `ActionPolicy` guardrail check first | Never makes planning decisions — it's a dumb, reliable, policy-gated actuator |
| **Tracing (`agent/tracing.py`)** | Wraps every graph node in an OTel-shaped `Span` (trace_id/span_id/duration/attributes), logged as structured JSON | Not a full OTel SDK — a stdlib-only, drop-in-compatible shape so a real exporter can be swapped in later without touching call sites |
| **LLM cache (`agent/llm_cache.py`)** | Exact-match (hash) cache always on; optional cosine-similarity semantic layer behind a flag; tracks token/cost totals per run | Never calls an external embedding API — semantic matching is local bag-of-words, deliberately, so tests stay network-free |
| **Policy (`browser_tools/policy.py`)** | Denylist/allowlist guardrail checked before every navigate/type action; raises `PolicyViolationError`, caught upstream and turned into a checkpointed error | Not a full sandbox — a pre-action gate, not runtime isolation |
| **Evals (`packages/evals`)** | Runs a fixed task suite through the real graph against offline fixtures with the fake LLM provider; reports pass rate, latency percentiles, retries, cache hit rate, cost | Not a substitute for integration tests against live sites — offline-only by design so it runs in CI |
| **MCP Server** | Thin adapter exposing Toolkit methods as MCP tools over stdio | Zero automation logic of its own |
| **Postgres** | System of record for runs, steps, checkpoints, extracted data, reports, sessions, memory | Not used as a queue (Redis fills that role) |
| **Redis** | Pub/sub backbone for live log fan-out (SSE), future task-queue upgrade path | Not the system of record |

## 3a. Multi-agent pattern: supervisor / worker / critic

This is a **supervisor/worker/critic** multi-agent design, not a single monolithic agent loop:

- **planner** (supervisor) — decomposes the goal into subtasks and owns overall strategy.
- **worker** — the only agent that touches the browser; purely executes one subtask via the toolkit.
- **critic** — a second, independent LLM call that reviews the worker's result against the subtask's *stated intent*, using a fresh DOM snapshot. This catches classes of silent failure a raw exception-based check can't: a `click` that "succeeded" but landed on the wrong element, an `extract` that returned an empty list on a page that clearly had data, a `navigate` that 200'd to the wrong URL after a redirect.
- **replanner** — re-engaged when either the worker raises an error *or* the critic flags `should_replan`, so recovery isn't limited to hard failures.

Routing (`agent/routing.py`): `route_after_worker` sends hard errors straight to `error_retry`/`error_exhausted`, otherwise always to `critic`; `route_after_critic` then decides `more_subtasks` / `done` / `error_retry` based on the critic's verdict.

## 4. Key design decisions

**One toolkit, two front doors.** The autonomous agent and the MCP-attached interactive client both call `BrowserToolkit` directly. This was chosen specifically so the project is credibly "Claude-in-Chrome-like" — a human can take over via Claude Code mid-task using the identical tool surface the agent used, not a parallel reimplementation.

**Checkpoints are first-class, not a side effect.** A `Checkpoint` row captures the entire resumable state — plan, scratchpad, extracted-so-far, and Playwright `storage_state` — at the moment of a CAPTCHA or unrecoverable error. This makes a paused run a durable object a human can act on hours later, from a different process, rather than a live-only in-memory pause.

**CAPTCHA handling is human-in-the-loop by policy, not by limitation.** The system does not attempt to bypass or auto-solve CAPTCHAs. Detection triggers a pause + notification; a human solves it in a visible browser; the run resumes from the exact checkpoint. This keeps the project's automation posture defensive/ethical and matches how a careful production scraper should behave.

**Selector resolution degrades gracefully.** Rather than one CSS selector per action (which breaks on any markup change), every targeting request goes through an ordered fallback chain, escalating to an LLM-assisted repair step only when deterministic strategies are exhausted — and successful repairs are cached so the cost is paid once per site, not once per run.

**Provider-agnostic LLM, deterministic test mode.** The agent's LLM calls go through a factory keyed off `LLM_PROVIDER`, so OpenAI/Anthropic/others are interchangeable, and a `"fake"` deterministic provider lets the full graph run offline in CI without hitting a real model.

**Two automation strategies, used for different problems.** Playwright wrappers are the deterministic, checkpointable default. `browser-use` is invoked only for planner-flagged "unstructured" subtasks (e.g. "find the pricing info somewhere on this site") where a fixed selector strategy doesn't apply — this is a deliberate scope split, not redundant tooling.

## 5. Data flow: a single run, happy path

1. Dashboard/API client creates a `Task` (goal + optional extraction schema) → `Run` (status `pending`).
2. API schedules `GraphRunner.run(...)` as a background task; `Run.status → running`.
3. `planner` node calls the LLM, produces an ordered subtask plan, written to `Run.plan`.
4. `worker` node executes the current subtask via `BrowserToolkit`; `dom_check`-equivalent routing inspects the result.
5. Each transition is persisted as a `Step` row (input/output, status, dom_fingerprint, screenshot path) — the dashboard's SSE stream picks these up live.
6. On success and more subtasks remaining → loop to `worker`. On plan exhaustion → `reporter`.
7. `reporter` assembles `extracted_data` + step history into a Markdown report, writes a `Report` row, `Run.status → completed`.

## 6. Data flow: CAPTCHA pause and resume

1. `worker` performs an action; CAPTCHA detection heuristics trip.
2. Routing sends control to `captcha_handler`, which persists a `Checkpoint` (plan, scratchpad, extracted-so-far, `storage_state`, page URL) and sets `Run.status → paused_captcha`. Execution stops.
3. Dashboard's Checkpoints page lists it; a human solves the CAPTCHA in the (non-headless) browser window.
4. Human calls `POST /checkpoints/{id}/resume`.
5. API reconstructs `AgentState` from the checkpoint and calls `GraphRunner.resume_from_checkpoint(...)`, which re-enters the worker/routing loop at the same subtask index using the restored browser session.
6. Execution proceeds as in the happy path from step 4 onward.

## 7. Non-functional considerations

- **Idempotent persistence**: steps are append-only; resuming never rewrites history, only continues it.
- **Offline testability**: fixture HTML pages + the `"fake"` LLM provider let the entire graph and toolkit be exercised in CI with zero external dependencies.
- **Secret handling**: credentials are referenced by env-var name in Postgres (`Credential.username_ref`), never stored as plaintext in the DB.
- **Extensibility**: adding an LLM provider is a factory-function change; adding a browser action is a new `BrowserToolkit` method automatically available to both the agent and MCP surfaces.

See [`docs/LLD.md`](LLD.md) for schemas, the exact state machine, and module-level contracts.
