import asyncio
import functools
from pathlib import Path

from langgraph.graph import StateGraph, END

from packages.agent.nodes.captcha_handler import captcha_handler_node
from packages.agent.nodes.planner import planner_node
from packages.agent.nodes.replanner import replanner_node
from packages.agent.nodes.reporter import reporter_node
from packages.agent.nodes.worker import worker_node
from packages.agent.routing import advance_subtask, route_after_worker
from packages.agent.state import AgentState


def _advance_node(state: AgentState) -> AgentState:
    return advance_subtask(state)


def build_graph(llm=None, toolkit=None, memory_store=None, session=None):
    graph = StateGraph(AgentState)

    graph.add_node("planner", functools.partial(planner_node, llm=llm, memory_store=memory_store, session=session))
    graph.add_node("worker", functools.partial(worker_node, toolkit=toolkit))
    graph.add_node("advance", _advance_node)
    graph.add_node(
        "replanner",
        functools.partial(replanner_node, llm=llm, toolkit=toolkit, memory_store=memory_store, session=session),
    )
    graph.add_node("captcha_handler", functools.partial(captcha_handler_node, toolkit=toolkit))
    graph.add_node("reporter", reporter_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "worker")

    graph.add_conditional_edges(
        "worker",
        route_after_worker,
        {
            "captcha": "captcha_handler",
            "error_retry": "replanner",
            "error_exhausted": "reporter",
            "more_subtasks": "advance",
            "done": "reporter",
        },
    )

    graph.add_edge("advance", "worker")
    graph.add_edge("replanner", "worker")
    graph.add_edge("captcha_handler", END)
    graph.add_edge("reporter", END)

    return graph.compile()


async def _demo() -> None:
    from packages.agent.llm import get_chat_model
    from packages.browser_tools.toolkit import BrowserToolkit

    listing_path = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "site" / "listing.html"
    listing_url = listing_path.resolve().as_uri()

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
            "checkpoint_id": None,
            "extracted_data": [],
            "run_id": None,
        }
        result = await compiled.ainvoke(initial_state)
        print(result["scratchpad"].get("report_summary"))
    finally:
        await toolkit.stop()


if __name__ == "__main__":
    asyncio.run(_demo())
