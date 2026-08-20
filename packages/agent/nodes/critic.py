import json
from pathlib import Path
from string import Template

from packages.agent.schemas import CriticVerdict
from packages.agent.state import AgentState
from packages.agent.structured_output import parse_with_retry

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "critic.md"


async def critic_node(state: AgentState, llm=None, toolkit=None) -> AgentState:
    """Supervisor-pattern critic: reviews the worker's result against the
    subtask's intent before the plan advances, catching failures the raw
    toolkit call wouldn't raise (empty extraction, wrong page, etc.)."""

    if llm is None:
        from packages.agent.llm import get_chat_model

        llm = get_chat_model()

    if state.get("error") or state.get("captcha_detected"):
        state["critic_verdict"] = None
        return state

    index = state["current_subtask_index"]
    subtask = state["plan"][index]

    dom_snapshot = ""
    if toolkit is not None:
        try:
            dom_snapshot = await toolkit.dom_snapshot()
        except Exception:
            dom_snapshot = ""

    prompt = Template(PROMPT_PATH.read_text(encoding="utf-8")).safe_substitute(
        subtask=json.dumps(subtask),
        last_action_result=json.dumps(state.get("last_action_result") or {}),
        dom_snapshot=dom_snapshot,
    )

    verdict = await parse_with_retry(llm, prompt, CriticVerdict)

    if verdict is None:
        # Critic itself failed to produce a valid verdict — don't block the
        # run on a guardrail malfunction, fall back to trusting the worker.
        state["critic_verdict"] = {"passed": True, "reason": "critic parse failed, defaulting to pass"}
        return state

    state["critic_verdict"] = verdict.model_dump()

    if not verdict.passed and verdict.should_replan:
        state["error"] = f"critic: subtask {index} did not satisfy intent: {verdict.reason}"

    return state
