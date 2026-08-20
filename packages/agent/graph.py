import asyncio
import functools
from pathlib import Path

from langgraph.graph import StateGraph, END

from packages.agent.nodes.captcha_handler import captcha_handler_node
from packages.agent.nodes.critic import critic_node
from packages.agent.nodes.planner import planner_node
from packages.agent.nodes.replanner import replanner_node
from packages.agent.nodes.reporter import reporter_node
from packages.agent.nodes.worker import worker_node
from packages.agent.routing import advance_subtask, route_after_critic, route_after_worker
from packages.agent.state import AgentState
from packages.agent.tracing import wrap_node


def _advance_node(state: AgentState) -> AgentState:
    return advance_subtask(state)


def build_graph(llm=None, toolkit=None, memory_store=None, session=None, trace: bool = True, critic_llm=None):
    """Compiles the supervisor/worker/critic graph: planner supervises overall
    strategy, worker executes browser actions, critic independently judges
    whether each result actually satisfied its subtask's intent before the
    plan is allowed to advance (see docs/HLD.md for the multi-agent design)."""
    graph = StateGraph(AgentState)

    maybe_trace = wrap_node if trace else (lambda fn, name: fn)

    graph.add_node(
        "planner",
        maybe_trace(functools.partial(planner_node, llm=llm, memory_store=memory_store, session=session), "planner"),
    )
    graph.add_node("worker", maybe_trace(functools.partial(worker_node, toolkit=toolkit), "worker"))
    graph.add_node(
        "critic", maybe_trace(functools.partial(critic_node, llm=critic_llm or llm, toolkit=toolkit), "critic")
    )
    graph.add_node("advance", _advance_node)
    graph.add_node(
        "replanner",
        maybe_trace(
            functools.partial(replanner_node, llm=llm, toolkit=toolkit, memory_store=memory_store, session=session),
            "replanner",
        ),
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
            "critic": "critic",
        },
    )

    graph.add_conditional_edges(
        "critic",
        route_after_critic,
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
            "agent_checkpoint_id": None,
            "extracted_data": [],
            "run_id": None,
        }
        result = await compiled.ainvoke(initial_state)
        print(result["scratchpad"].get("report_summary"))
    finally:
        await toolkit.stop()


if __name__ == "__main__":
    asyncio.run(_demo())
