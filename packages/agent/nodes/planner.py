import json
import re
from pathlib import Path
from string import Template

from packages.agent.state import AgentState

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "planner.md"


def _strip_code_fences(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text


def _parse_plan(raw: str) -> list[dict]:
    cleaned = _strip_code_fences(raw).strip()
    data = json.loads(cleaned)
    return data.get("subtasks", [])


async def planner_node(state: AgentState, llm=None, memory_store=None, session=None) -> AgentState:
    if llm is None:
        from packages.agent.llm import get_chat_model

        llm = get_chat_model()

    scratchpad = dict(state.get("scratchpad") or {})

    if memory_store is not None and session is not None and state.get("run_id"):
        entries = await memory_store.list_for_run(session, state["run_id"])
        for entry in entries:
            scratchpad[entry.key] = entry.value

    prompt = Template(PROMPT_PATH.read_text(encoding="utf-8")).safe_substitute(
        task_goal=state["task_goal"],
        extraction_schema=json.dumps(state.get("extraction_schema") or {}),
        scratchpad=json.dumps(scratchpad),
    )

    response = await llm.ainvoke(prompt) if hasattr(llm, "ainvoke") else llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)

    try:
        plan = _parse_plan(content)
    except (json.JSONDecodeError, AttributeError):
        plan = []
        state["error"] = f"planner: failed to parse LLM plan output: {content[:200]!r}"

    state["plan"] = plan
    state["current_subtask_index"] = 0
    state["scratchpad"] = scratchpad

    if memory_store is not None and session is not None and state.get("run_id"):
        await memory_store.save(session, state["run_id"], "last_plan", plan)

    return state
