# Demo Script

1. `cp .env.example .env` and fill in values (or leave `LLM_PROVIDER=fake` for a fully offline demo).
2. `docker compose up --build` — starts Postgres, Redis, and the API.
3. `make migrate` (or `alembic upgrade head`) — apply migrations.
4. Seed a task:
   ```
   curl -X POST http://localhost:8000/tasks -H "Content-Type: application/json" \
     -d '{"name": "demo", "goal": "Extract listing items", "extraction_schema": {}}'
   ```
5. Launch a run: `curl -X POST http://localhost:8000/tasks/<task_id>/runs`
6. `cd apps/dashboard && npm install && npm run dev`, open http://localhost:5173, watch the run in Run Detail (live SSE log + screenshots).
7. To exercise the CAPTCHA pause path, point a run at `tests/fixtures/site/captcha_mock.html`; once paused, go to the Checkpoints page and click Resume.
8. View the generated report on the Report Viewer page, or download it via `GET /runs/{id}/report/download`.
9. Attach the MCP server to Claude Code: `python -m packages.mcp_server.run_stdio`, then register it as a stdio MCP server in your Claude Code MCP config.
