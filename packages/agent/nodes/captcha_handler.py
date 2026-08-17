from packages.agent.state import AgentState


async def captcha_handler_node(state: AgentState, toolkit=None) -> AgentState:
    storage_state = None
    page_url = None

    if toolkit is not None:
        try:
            storage_state = await toolkit._context.storage_state()
        except Exception:
            storage_state = None
        try:
            page_url = toolkit.page.url
        except Exception:
            page_url = None

    scratchpad = dict(state.get("scratchpad") or {})
    scratchpad["_pending_checkpoint"] = {
        "reason": "captcha",
        "page_url": page_url,
        "storage_state": storage_state,
    }
    state["scratchpad"] = scratchpad

    return state
