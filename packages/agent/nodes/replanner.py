import json
import re
from pathlib import Path
from string import Template

from packages.agent.state import AgentState

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "replanner.md"


def _strip_code_fences(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text


def _parse_plan(raw: str) -> list[dict]:
    cleaned = _strip_code_fences(raw).strip()
    data = json.loads(cleaned)
    return data.get("subtasks", [])


async def replanner_node(state: AgentState, llm=None, toolkit=None, memory_store=None, session=None) -> AgentState:
    if llm is None:
        from packages.agent.llm import get_chat_model

        llm = get_chat_model()

    dom_snapshot = ""
    if toolkit is not None:
        try:
            dom_snapshot = await toolkit.dom_snapshot()
        except Exception:
            dom_snapshot = ""

    index = state["current_subtask_index"]
    remaining_plan = state["plan"][index:]

    prompt = Template(PROMPT_PATH.read_text(encoding="utf-8")).safe_substitute(
        task_goal=state["task_goal"],
        extraction_schema=json.dumps(state.get("extraction_schema") or {}),
        error=state.get("error") or "",
        scratchpad=json.dumps(state.get("scratchpad") or {}),
        remaining_plan=json.dumps(remaining_plan),
        dom_snapshot=dom_snapshot,
    )

    response = await llm.ainvoke(prompt) if hasattr(llm, "ainvoke") else llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)

    try:
        new_subtasks = _parse_plan(content)
        state["plan"] = state["plan"][:index] + new_subtasks
    except (json.JSONDecodeError, AttributeError):
        pass

    state["retry_count"] = state.get("retry_count", 0) + 1
    state["error"] = None

    if memory_store is not None and session is not None and state.get("run_id"):
        await memory_store.save(session, state["run_id"], "last_replan", state["plan"])

    return state
