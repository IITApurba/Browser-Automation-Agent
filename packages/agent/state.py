from typing import TypedDict


class AgentState(TypedDict):
    task_goal: str
    extraction_schema: dict | None
    plan: list[dict]
    current_subtask_index: int
    scratchpad: dict
    last_action_result: dict | None
    error: str | None
    retry_count: int
    captcha_detected: bool
    checkpoint_id: str | None
    extracted_data: list[dict]
    run_id: str | None
