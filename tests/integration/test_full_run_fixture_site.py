from pathlib import Path

import pytest

from packages.agent.graph import build_graph
from packages.agent.llm import get_chat_model
from packages.agent.state import AgentState
from packages.browser_tools.toolkit import BrowserToolkit

LISTING_PATH = Path(__file__).parent.parent / "fixtures" / "site" / "listing.html"


@pytest.mark.asyncio
async def test_full_run_against_fixture_site():
    listing_url = LISTING_PATH.resolve().as_uri()

    responses = [
        (
            '{"subtasks": ['
            f'{{"type": "navigate", "description": "Go to listing page", "params": {{"url": "{listing_url}"}}}},'
            '{"type": "extract", "description": "Extract listing items", "params": {"schema": {'
            '"title": {"selector": ".item .item-title", "attr": "text", "multiple": true}, '
            '"price": {"selector": ".item .item-price", "attr": "text", "multiple": true}}}}'
            "]}"
        )
    ]

    llm = get_chat_model("fake", overrides={"responses": responses})
    toolkit = BrowserToolkit()
    await toolkit.start()

    try:
        compiled = build_graph(llm=llm, toolkit=toolkit)
        initial_state: AgentState = {
            "task_goal": "Extract all listing items with titles and prices",
            "extraction_schema": {"title": {}, "price": {}},
            "plan": [],
            "current_subtask_index": 0,
            "scratchpad": {},
            "last_action_result": None,
            "error": None,
            "retry_count": 0,
            "captcha_detected": False,
            "agent_checkpoint_id": None,
            "extracted_data": [],
            "run_id": None,
        }
        result = await compiled.ainvoke(initial_state)

        assert not result.get("error")
        assert result["extracted_data"], "expected at least one extracted record"
        assert result["scratchpad"].get("report_summary") is not None
    finally:
        await toolkit.stop()
