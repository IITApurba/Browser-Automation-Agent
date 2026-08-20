"""Fixed eval tasks run against the offline fixture site through the real
LangGraph graph. Each task supplies scripted fake-LLM plan responses (so the
harness needs no network access) and an `expected` checker for extraction
correctness."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

FIXTURES = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "site"


def _uri(name: str) -> str:
    return (FIXTURES / name).resolve().as_uri()


@dataclass
class EvalTask:
    name: str
    task_goal: str
    extraction_schema: dict
    plan_responses: list[str]
    expected: Callable[[list[dict]], bool]


def _listing_ok(extracted: list[dict]) -> bool:
    if not extracted:
        return False
    titles = extracted[0].get("title", [])
    prices = extracted[0].get("price", [])
    return len(titles) == 5 and len(prices) == 5 and "Wireless Mouse" in titles


def _login_ok(extracted: list[dict]) -> bool:
    if not extracted:
        return False
    return extracted[0].get("welcome_text") == "Welcome back!"


TASKS: list[EvalTask] = [
    EvalTask(
        name="listing_extraction",
        task_goal="Extract all listing items with titles and prices",
        extraction_schema={"title": {}, "price": {}},
        plan_responses=[
            (
                '{"subtasks": ['
                f'{{"type": "navigate", "description": "Go to listing page", "params": {{"url": "{_uri("listing.html")}"}}}},'
                '{"type": "extract", "description": "Extract listing items", "params": {"schema": {'
                '"title": {"selector": ".item .item-title", "attr": "text", "multiple": true}, '
                '"price": {"selector": ".item .item-price", "attr": "text", "multiple": true}}}}'
                "]}"
            )
        ],
        expected=_listing_ok,
    ),
    EvalTask(
        name="login_flow",
        task_goal="Log in and confirm the welcome message appears",
        extraction_schema={"welcome_text": {}},
        plan_responses=[
            (
                '{"subtasks": ['
                f'{{"type": "navigate", "description": "Go to login page", "params": {{"url": "{_uri("login.html")}"}}}},'
                '{"type": "type_text", "description": "Enter username", "params": {"selector": "#username", "text": "demo"}},'
                '{"type": "type_text", "description": "Enter password", "params": {"selector": "#password", "text": "demo"}},'
                '{"type": "click", "description": "Submit login form", "params": {"selector": "#submit"}},'
                '{"type": "wait_for_selector", "description": "Wait for welcome banner", "params": {"selector": "#welcome", "timeout": 3000}},'
                '{"type": "extract", "description": "Read welcome text", "params": {"schema": {'
                '"welcome_text": {"selector": "#welcome", "attr": "text"}}}}'
                "]}"
            )
        ],
        expected=_login_ok,
    ),
]
