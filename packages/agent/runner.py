"""Execution service that drives the LangGraph agent graph and persists progress to Postgres.

Design note on resume_from_checkpoint: LangGraph's `.astream()` always starts from the graph's
entry point (planner). Re-entering "mid-graph" at the worker node isn't natively supported by a
compiled StateGraph without checkpoint-saver plumbing we don't have wired up yet, so instead we
build the same compiled graph and directly drive `worker_node`/the routing helpers in a small
manual loop, reusing the exact node functions the graph uses. This keeps behavior identical to a
normal run while avoiding rebuilding a partial graph. Simpler than teaching LangGraph to resume.
"""

import uuid

from packages.agent.graph import build_graph
from packages.agent.nodes.reporter import reporter_node
from packages.agent.nodes.worker import worker_node
from packages.agent.routing import advance_subtask, route_after_worker
from packages.agent.state import AgentState
from packages.db.models import Checkpoint, Run, RunStatus, Step, StepStatus


def _new_state(task_goal: str, extraction_schema: dict | None, run_id: str) -> AgentState:
    return {
        "task_goal": task_goal,
        "extraction_schema": extraction_schema,
        "plan": [],
        "current_subtask_index": 0,
        "scratchpad": {},
        "last_action_result": None,
        "error": None,
        "retry_count": 0,
        "captcha_detected": False,
        "checkpoint_id": None,
        "extracted_data": [],
        "run_id": run_id,
    }


class GraphRunner:
    async def run(
        self,
        task_id: str,
        run_id: str,
        task_goal: str,
        extraction_schema: dict | None,
        session_factory,
        llm=None,
        toolkit=None,
    ) -> None:
        owns_toolkit = toolkit is None
        if toolkit is None:
            from packages.browser_tools.toolkit import BrowserToolkit

            toolkit = BrowserToolkit()
            await toolkit.start()

        await self._set_run_status(session_factory, run_id, RunStatus.running)

        compiled = build_graph(llm=llm, toolkit=toolkit)
        initial_state = _new_state(task_goal, extraction_schema, run_id)

        final_state: AgentState | None = None
        step_index = 0
        try:
            async for event in compiled.astream(initial_state):
                for node_name, node_state in event.items():
                    final_state = node_state
                    await self._record_step(session_factory, run_id, step_index, node_name, node_state, toolkit)
                    step_index += 1

                    await self._update_run_progress(session_factory, run_id, node_state)

                    if node_name == "captcha_handler":
                        await self._create_checkpoint_from_state(session_factory, run_id, node_state)
                        await self._set_run_status(session_factory, run_id, RunStatus.paused_captcha)
                        return

            if final_state is not None:
                if final_state.get("error") and final_state.get("retry_count", 0) >= 3:
                    await self._set_run_status(
                        session_factory, run_id, RunStatus.failed, error_message=final_state.get("error")
                    )
                else:
                    await self._set_run_status(session_factory, run_id, RunStatus.completed)
        except Exception as exc:
            await self._set_run_status(session_factory, run_id, RunStatus.failed, error_message=str(exc))
        finally:
            if owns_toolkit:
                try:
                    await toolkit.stop()
                except Exception:
                    pass

    async def resume_from_checkpoint(self, checkpoint_id: str, session_factory, llm=None, toolkit=None) -> None:
        from sqlalchemy import select

        owns_toolkit = toolkit is None
        if toolkit is None:
            from packages.browser_tools.toolkit import BrowserToolkit

            toolkit = BrowserToolkit()
            await toolkit.start()

        try:
            async with session_factory() as session:
                checkpoint = await session.get(Checkpoint, uuid.UUID(str(checkpoint_id)))
                if checkpoint is None:
                    return
                run = await session.get(Run, checkpoint.run_id)

            run_id = str(checkpoint.run_id)
            plan = (run.plan if run else None) or []
            scratchpad = dict(checkpoint.scratchpad_memory or {})
            extracted_data = list(checkpoint.extracted_so_far or [])
            index = run.current_step_index if run else 0

            if checkpoint.storage_state and toolkit._context is not None:
                try:
                    await toolkit._context.add_cookies(checkpoint.storage_state.get("cookies", []))
                except Exception:
                    pass
            if checkpoint.page_url:
                try:
                    await toolkit.navigate(checkpoint.page_url)
                except Exception:
                    pass

            state: AgentState = {
                "task_goal": (run.plan or {}).get("task_goal", "") if run else "",
                "extraction_schema": None,
                "plan": plan,
                "current_subtask_index": index,
                "scratchpad": scratchpad,
                "last_action_result": None,
                "error": None,
                "retry_count": 0,
                "captcha_detected": False,
                "checkpoint_id": None,
                "extracted_data": extracted_data,
                "run_id": run_id,
            }

            await self._set_run_status(session_factory, run_id, RunStatus.running)

            step_index = 0
            while True:
                state = await worker_node(state, toolkit=toolkit)
                await self._record_step(session_factory, run_id, step_index, "worker", state, toolkit)
                step_index += 1
                await self._update_run_progress(session_factory, run_id, state)

                decision = route_after_worker(state)
                if decision == "captcha":
                    await self._create_checkpoint_from_state(session_factory, run_id, state)
                    await self._set_run_status(session_factory, run_id, RunStatus.paused_captcha)
                    return
                if decision == "error_exhausted":
                    await self._set_run_status(
                        session_factory, run_id, RunStatus.failed, error_message=state.get("error")
                    )
                    return
                if decision == "more_subtasks":
                    state = advance_subtask(state)
                    continue
                if decision == "done":
                    state = await reporter_node(state)
                    await self._set_run_status(session_factory, run_id, RunStatus.completed)
                    return
                # error_retry: without a replanner LLM call here we just bail to failed
                await self._set_run_status(
                    session_factory, run_id, RunStatus.failed, error_message=state.get("error")
                )
                return
        except Exception as exc:
            await self._set_run_status(session_factory, run_id, RunStatus.failed, error_message=str(exc))
        finally:
            if owns_toolkit:
                try:
                    await toolkit.stop()
                except Exception:
                    pass

    async def _record_step(self, session_factory, run_id, index, node_name, node_state, toolkit) -> None:
        try:
            dom_fingerprint = None
            if toolkit is not None:
                try:
                    dom_fingerprint = (await toolkit.dom_snapshot(max_len=200)) or None
                except Exception:
                    dom_fingerprint = None

            async with session_factory() as session:
                step = Step(
                    run_id=uuid.UUID(str(run_id)),
                    index=index,
                    type=node_name,
                    input={"subtask_index": node_state.get("current_subtask_index")},
                    output={
                        "last_action_result": node_state.get("last_action_result"),
                        "error": node_state.get("error"),
                    },
                    status=StepStatus.error if node_state.get("error") else StepStatus.ok,
                    dom_fingerprint=dom_fingerprint,
                )
                session.add(step)
                await session.commit()
        except Exception:
            pass

    async def _update_run_progress(self, session_factory, run_id, node_state) -> None:
        try:
            async with session_factory() as session:
                run = await session.get(Run, uuid.UUID(str(run_id)))
                if run is None:
                    return
                run.current_step_index = node_state.get("current_subtask_index", run.current_step_index)
                run.plan = {"subtasks": node_state.get("plan", []), "task_goal": node_state.get("task_goal")}
                run.error_message = node_state.get("error")
                await session.commit()
        except Exception:
            pass

    async def _set_run_status(self, session_factory, run_id, status: RunStatus, error_message: str | None = None) -> None:
        try:
            async with session_factory() as session:
                run = await session.get(Run, uuid.UUID(str(run_id)))
                if run is None:
                    return
                run.status = status
                if error_message is not None:
                    run.error_message = error_message
                await session.commit()
        except Exception:
            pass

    async def _create_checkpoint_from_state(self, session_factory, run_id, state) -> None:
        try:
            pending = (state.get("scratchpad") or {}).get("_pending_checkpoint", {})
            async with session_factory() as session:
                checkpoint = Checkpoint(
                    run_id=uuid.UUID(str(run_id)),
                    reason="captcha",
                    page_url=pending.get("page_url") or "",
                    storage_state=pending.get("storage_state"),
                    extracted_so_far=state.get("extracted_data"),
                    scratchpad_memory=state.get("scratchpad"),
                )
                session.add(checkpoint)
                await session.commit()
        except Exception:
            pass
