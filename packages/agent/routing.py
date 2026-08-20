from packages.agent.state import AgentState

MAX_RETRIES = 3


def route_after_worker(state: AgentState) -> str:
    if state.get("captcha_detected"):
        return "captcha"

    if state.get("error"):
        if state.get("retry_count", 0) < MAX_RETRIES:
            return "error_retry"
        return "error_exhausted"

    return "critic"


def route_after_critic(state: AgentState) -> str:
    if state.get("captcha_detected"):
        return "captcha"

    if state.get("error"):
        if state.get("retry_count", 0) < MAX_RETRIES:
            return "error_retry"
        return "error_exhausted"

    if state["current_subtask_index"] + 1 < len(state["plan"]):
        return "more_subtasks"

    return "done"


def advance_subtask(state: AgentState) -> AgentState:
    state["current_subtask_index"] += 1
    return state
