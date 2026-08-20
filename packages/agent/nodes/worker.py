from packages.agent.state import AgentState
from packages.browser_tools.captcha_detect import detect_captcha
from packages.browser_tools.policy import PolicyViolationError


async def _execute_subtask(toolkit, subtask: dict):
    subtask_type = subtask["type"]
    params = subtask.get("params", {})

    if subtask_type == "navigate":
        await toolkit.navigate(params["url"])
        return {"status": "ok"}
    if subtask_type == "click":
        await toolkit.click(params["selector"])
        return {"status": "ok"}
    if subtask_type == "type_text":
        await toolkit.type_text(params["selector"], params.get("text", ""))
        return {"status": "ok"}
    if subtask_type == "extract":
        data = await toolkit.extract(params.get("schema", {}))
        return {"status": "ok", "data": data}
    if subtask_type == "wait_for_selector":
        await toolkit.wait_for_selector(params["selector"], timeout=params.get("timeout", 5000))
        return {"status": "ok"}

    raise ValueError(f"Unknown subtask type: {subtask_type}")


async def worker_node(state: AgentState, toolkit=None) -> AgentState:
    if toolkit is None:
        from packages.browser_tools.toolkit import BrowserToolkit

        toolkit = BrowserToolkit()
        await toolkit.start()

    plan = state["plan"]
    index = state["current_subtask_index"]
    subtask = plan[index]

    state["error"] = None

    try:
        result = await _execute_subtask(toolkit, subtask)
        state["last_action_result"] = result
        if subtask["type"] == "extract" and "data" in result:
            state["extracted_data"] = [*state.get("extracted_data", []), result["data"]]
    except PolicyViolationError as exc:
        state["error"] = f"worker: subtask {index} ({subtask.get('type')}) blocked by policy: {exc}"
        state["last_action_result"] = {"status": "policy_violation", "message": str(exc)}
    except Exception as exc:
        state["error"] = f"worker: subtask {index} ({subtask.get('type')}) failed: {exc}"
        state["last_action_result"] = {"status": "error", "message": str(exc)}

    try:
        state["captcha_detected"] = await detect_captcha(toolkit.page)
    except Exception:
        state["captcha_detected"] = False

    return state
