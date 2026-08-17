from packages.agent.state import AgentState


async def reporter_node(state: AgentState, report_generator=None, run=None) -> AgentState:
    extracted_data = state.get("extracted_data", [])
    plan = state.get("plan", [])

    summary = {
        "task_goal": state.get("task_goal"),
        "total_subtasks": len(plan),
        "completed_subtasks": state.get("current_subtask_index", 0) + 1,
        "extracted_record_count": len(extracted_data),
        "extracted_data": extracted_data,
        "had_error": bool(state.get("error")),
        "error": state.get("error"),
    }

    scratchpad = dict(state.get("scratchpad") or {})
    scratchpad["report_summary"] = summary

    if report_generator is not None and run is not None:
        try:
            markdown = report_generator.generate(run, plan, extracted_data)
            scratchpad["report_markdown"] = markdown
        except Exception as exc:
            scratchpad["report_generation_error"] = str(exc)

    state["scratchpad"] = scratchpad

    return state
