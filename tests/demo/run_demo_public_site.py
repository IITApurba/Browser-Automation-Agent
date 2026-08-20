"""Manual demo script — NOT run by the test suite.

Requires:
  - network access
  - a real LLM provider API key (e.g. OPENAI_API_KEY or ANTHROPIC_API_KEY) set in the environment
  - `playwright install chromium` already run

Usage:
    python tests/demo/run_demo_public_site.py

This points the agent at a real public URL instead of the offline fixture site, using a real
LLM (not the "fake" provider) to plan and adapt to the live page. Intended for manual smoke
testing / demos, never for CI.
"""

import asyncio
import os

from packages.agent.graph import build_graph
from packages.agent.llm import get_chat_model
from packages.agent.state import AgentState
from packages.browser_tools.toolkit import BrowserToolkit

DEMO_URL = "https://example.com"


async def main() -> None:
    provider = os.environ.get("LLM_PROVIDER", "openai")
    llm = get_chat_model(provider)

    toolkit = BrowserToolkit()
    await toolkit.start(headless=False)

    try:
        compiled = build_graph(llm=llm, toolkit=toolkit)
        initial_state: AgentState = {
            "task_goal": f"Go to {DEMO_URL} and summarize the page heading and first paragraph",
            "extraction_schema": None,
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
        print(result["scratchpad"].get("report_summary"))
    finally:
        await toolkit.stop()


if __name__ == "__main__":
    asyncio.run(main())
