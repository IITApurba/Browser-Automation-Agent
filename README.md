# Browser Automation Agent

An autonomous browser agent that plans and executes multi-step web workflows — navigation, authenticated flows, structured data extraction, and report generation — with resilience features built in: CAPTCHA human-handoff, DOM-change-tolerant selectors, and durable execution checkpoints so a run survives crashes and interruptions.

The browser control layer is a single Playwright-based toolkit shared by two front doors:
- a **LangGraph planner/worker agent** that runs tasks autonomously end-to-end, and
- an **MCP server** that re-exports the exact same tools so any MCP-compatible client (Claude Code, Claude Desktop) can drive the same browser session directly.

That shared-toolkit design is the point: the autonomous agent and a human driving it through an MCP client are never touching two different implementations of "click" or "extract."

```
apps/dashboard (React)  <-->  apps/api (FastAPI)  <-->  packages/agent (LangGraph planner/worker)
                                      |                        |
                                      v                        v
                                 packages/db (Postgres)   packages/browser_tools (Playwright)
                                      ^                        ^
                                      |                        |
                              packages/mcp_server  ------------+  (stdio, e.g. Claude Code)
```

Full design docs: [`docs/HLD.md`](docs/HLD.md) (system-level design, component responsibilities, data flow) and [`docs/LLD.md`](docs/LLD.md) (module-level design: schemas, state machine, algorithms, API contracts).

## Why it's built this way

- **Resilience over cleverness.** Every selector lookup goes through a fallback chain (explicit selector → ARIA role → visible text → attribute heuristics → retry-with-backoff → LLM-assisted repair) before it's allowed to fail a step. Sites change their DOM; a agent that breaks on the first `TimeoutError` isn't autonomous, it's brittle.
- **Nothing is lost on failure.** Every graph transition is persisted as a `Step` row, and every CAPTCHA/error pause is persisted as a `Checkpoint` with the full `AgentState` (plan, scratchpad, extracted data, browser storage state) — a run can be resumed hours later on a different process.
- **CAPTCHAs are a handoff, not a bypass.** The agent detects known CAPTCHA markers, checkpoints, and stops — a human resolves it in a visible browser and resumes the run via the API/dashboard. No solver services, no scraping-detection evasion.
- **One toolkit, two entry points.** `packages/browser_tools/toolkit.py` is the only place browser actions are implemented. Both `packages/agent/nodes/worker.py` and `packages/mcp_server/tool_definitions.py` call it directly.

## Repository layout

| Path | Responsibility |
|---|---|
| `apps/api` | FastAPI service — task/run/checkpoint/report endpoints, SSE log streaming |
| `apps/dashboard` | React + Vite + TS dashboard — run list, live run detail, checkpoint resolution, report viewer |
| `packages/agent` | LangGraph state machine: planner, worker, replanner, captcha_handler, reporter nodes; provider-agnostic LLM factory; `runner.py` execution/persistence service |
| `packages/browser_tools` | Playwright `BrowserToolkit`, selector fallback strategy, auth/session reuse, CAPTCHA detection, `browser-use` fallback adapter |
| `packages/mcp_server` | MCP server (FastMCP) re-exporting `BrowserToolkit` as tools, stdio entrypoint |
| `packages/db` | SQLAlchemy 2.0 async models (9 tables) + Alembic migrations |
| `packages/memory` | In-run scratchpad + Postgres-backed cross-run memory |
| `packages/extraction`, `packages/reporting` | Schema-driven extraction, Markdown report generation |
| `tests/fixtures/site` | Offline static HTML fixtures (login, listing, CAPTCHA mock) — no external network dependency for tests |
| `docs/` | HLD, LLD, demo script |

## Quickstart

```bash
cp .env.example .env               # fill in LLM_PROVIDER + API key, DATABASE_URL, etc.
docker compose up --build          # Postgres + Redis + API + dashboard

pip install -e .[dev]
playwright install chromium

cd apps/dashboard && npm install && npm run dev   # dashboard dev server, separate from Docker build
```

Attach the MCP server to Claude Code / Claude Desktop:

```bash
python -m packages.mcp_server.run_stdio
```

## Development

- `make dev` — run the API locally with reload
- `make test` — run the test suite (`pip install -e .[dev]`, `playwright install chromium` required for browser-backed tests)
- `make migrate` — apply Alembic migrations
- `make up` — `docker compose up --build`

See [`docs/HLD.md`](docs/HLD.md), [`docs/LLD.md`](docs/LLD.md), [`docs/architecture.md`](docs/architecture.md), and [`docs/demo_script.md`](docs/demo_script.md) for details.

## Status

This is a from-scratch reference implementation built to demonstrate the architecture end-to-end: all modules compile and the core graph/API/toolkit logic is implemented and unit-tested against offline fixtures. `docker compose up`, `npm install`, and `playwright install` need to be run in an environment with network access — they were not executable in the sandbox this was built in.
