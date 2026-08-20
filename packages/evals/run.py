"""Eval harness: runs the fixed task suite through the real LangGraph graph
against offline fixtures, using the fake LLM provider (no network calls),
and reports pass rate, latency percentiles, retries, and LLM cache/cost
stats. Numbers in README.md's Results section come from an actual run of
this script — `make eval` or `python -m packages.evals.run`.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from pathlib import Path

from packages.agent.graph import build_graph
from packages.agent.llm import get_chat_model
from packages.agent.llm_cache import CachingChatModel, LLMCache
from packages.agent.state import AgentState
from packages.browser_tools.toolkit import BrowserToolkit
from packages.evals.tasks import TASKS

REPORT_DIR = Path(__file__).parent / "reports"

# Always-pass critic response, reused for every critic call so the fixed
# task suite doesn't need to hand-script one verdict per subtask.
CRITIC_PASS_RESPONSE = '{"passed": true, "reason": "worker result matches subtask intent", "should_replan": false}'


def _initial_state(task) -> AgentState:
    return {
        "task_goal": task.task_goal,
        "extraction_schema": task.extraction_schema,
        "plan": [],
        "current_subtask_index": 0,
        "scratchpad": {},
        "last_action_result": None,
        "error": None,
        "retry_count": 0,
        "captcha_detected": False,
        "agent_checkpoint_id": None,
        "extracted_data": [],
        "run_id": task.name,
        "critic_verdict": None,
    }


async def run_task(task, shared_cache: LLMCache) -> dict:
    planner_llm = CachingChatModel(
        get_chat_model("fake", overrides={"responses": task.plan_responses}),
        model_name="fake",
        cache=shared_cache,
    )
    critic_llm = CachingChatModel(
        get_chat_model("fake", overrides={"responses": [CRITIC_PASS_RESPONSE]}),
        model_name="fake",
        cache=shared_cache,
    )

    toolkit = BrowserToolkit()
    await toolkit.start()

    start = time.perf_counter()
    try:
        compiled = build_graph(llm=planner_llm, critic_llm=critic_llm, toolkit=toolkit)
        result = await compiled.ainvoke(_initial_state(task))
    finally:
        await toolkit.stop()
    duration_ms = (time.perf_counter() - start) * 1000

    passed = not result.get("error") and task.expected(result.get("extracted_data", []))

    return {
        "name": task.name,
        "passed": passed,
        "duration_ms": round(duration_ms, 2),
        "retry_count": result.get("retry_count", 0),
        "had_error": bool(result.get("error")),
        "error": result.get("error"),
        "extracted_record_count": len(result.get("extracted_data", [])),
        "planner_llm_stats": planner_llm.stats(),
        "critic_llm_stats": critic_llm.stats(),
    }


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((pct / 100) * (len(ordered) - 1))))
    return ordered[index]


async def run_suite(repeat: int = 1) -> dict:
    shared_cache = LLMCache(semantic=False)
    results = []
    for _ in range(repeat):
        for task in TASKS:
            results.append(await run_task(task, shared_cache))

    durations = [r["duration_ms"] for r in results]
    passed_count = sum(1 for r in results if r["passed"])
    total_tokens = sum(r["planner_llm_stats"]["total_tokens"] + r["critic_llm_stats"]["total_tokens"] for r in results)
    total_cost = sum(r["planner_llm_stats"]["total_cost_usd"] + r["critic_llm_stats"]["total_cost_usd"] for r in results)

    summary = {
        "task_count": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "pass_rate": round(passed_count / len(results), 4) if results else 0.0,
        "latency_ms": {
            "p50": round(_percentile(durations, 50), 2),
            "p95": round(_percentile(durations, 95), 2),
            "mean": round(statistics.mean(durations), 2) if durations else 0.0,
        },
        "avg_retry_count": round(statistics.mean([r["retry_count"] for r in results]), 3) if results else 0.0,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "llm_cache": shared_cache.stats.as_dict(),
    }

    return {"summary": summary, "results": results}


def _render_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        "# Eval Report",
        "",
        f"- Tasks run: {s['task_count']}",
        f"- Pass rate: {s['pass_rate'] * 100:.1f}% ({s['passed']}/{s['task_count']})",
        f"- Latency p50 / p95: {s['latency_ms']['p50']} ms / {s['latency_ms']['p95']} ms",
        f"- Avg retries per task: {s['avg_retry_count']}",
        f"- Total LLM tokens (est.): {s['total_tokens']}",
        f"- Total LLM cost (est., fake provider = $0): ${s['total_cost_usd']}",
        f"- LLM cache hit rate: {s['llm_cache']['hit_rate'] * 100:.1f}% ({s['llm_cache']['hits']}/{s['llm_cache']['total']})",
        "",
        "## Per-task results",
        "",
        "| Task | Passed | Duration (ms) | Retries | Records |",
        "|---|---|---|---|---|",
    ]
    for r in report["results"]:
        lines.append(f"| {r['name']} | {r['passed']} | {r['duration_ms']} | {r['retry_count']} | {r['extracted_record_count']} |")
    return "\n".join(lines) + "\n"


async def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = await run_suite(repeat=3)

    (REPORT_DIR / "latest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (REPORT_DIR / "latest.md").write_text(_render_markdown(report), encoding="utf-8")

    print(_render_markdown(report))


if __name__ == "__main__":
    asyncio.run(main())
