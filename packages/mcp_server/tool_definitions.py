"""Thin MCP-facing wrappers over BrowserToolkit and the DB models. No logic is reimplemented here;
each function delegates directly to the packages.browser_tools / packages.db primitives.
"""

import uuid

from packages.browser_tools.auth import login as _auth_login
from packages.browser_tools.captcha_detect import detect_captcha
from packages.browser_tools.toolkit import BrowserToolkit
from packages.db.models import Run, RunStatus, Task
from packages.db.session import async_session_factory

_toolkit: BrowserToolkit | None = None


async def _get_toolkit() -> BrowserToolkit:
    global _toolkit
    if _toolkit is None:
        _toolkit = BrowserToolkit()
        await _toolkit.start()
    return _toolkit


async def browser_navigate(url: str) -> dict:
    toolkit = await _get_toolkit()
    await toolkit.navigate(url)
    return {"status": "ok", "url": url}


async def browser_click(selector: str) -> dict:
    toolkit = await _get_toolkit()
    await toolkit.click(selector)
    return {"status": "ok"}


async def browser_type(selector: str, text: str) -> dict:
    toolkit = await _get_toolkit()
    await toolkit.type_text(selector, text)
    return {"status": "ok"}


async def browser_extract(schema: dict) -> dict:
    toolkit = await _get_toolkit()
    return await toolkit.extract(schema)


async def browser_screenshot(path: str) -> dict:
    toolkit = await _get_toolkit()
    await toolkit.screenshot(path)
    return {"status": "ok", "path": path}


async def browser_wait_for_selector(selector: str, timeout: int = 5000) -> dict:
    toolkit = await _get_toolkit()
    await toolkit.wait_for_selector(selector, timeout=timeout)
    return {"status": "ok"}


async def browser_get_dom_snapshot(max_len: int = 4000) -> dict:
    toolkit = await _get_toolkit()
    snapshot = await toolkit.dom_snapshot(max_len=max_len)
    return {"snapshot": snapshot}


async def browser_login(
    url: str,
    username_selector: str,
    password_selector: str,
    submit_selector: str,
    username: str,
    password: str,
) -> dict:
    toolkit = await _get_toolkit()
    storage_state = await _auth_login(
        toolkit, url, username_selector, password_selector, submit_selector, username, password
    )
    return {"status": "ok", "storage_state": storage_state}


async def browser_captcha_status() -> dict:
    toolkit = await _get_toolkit()
    detected = await detect_captcha(toolkit.page)
    return {"captcha_detected": detected}


async def task_create_run(task_id: str) -> dict:
    async with async_session_factory() as session:
        task = await session.get(Task, uuid.UUID(str(task_id)))
        if task is None:
            return {"status": "error", "message": "task not found"}
        run = Run(task_id=task.id, status=RunStatus.pending)
        session.add(run)
        await session.commit()
        await session.refresh(run)
        return {"status": "ok", "run_id": str(run.id)}


async def task_get_run_status(run_id: str) -> dict:
    async with async_session_factory() as session:
        run = await session.get(Run, uuid.UUID(str(run_id)))
        if run is None:
            return {"status": "error", "message": "run not found"}
        return {
            "status": getattr(run.status, "value", run.status),
            "current_step_index": run.current_step_index,
            "error_message": run.error_message,
        }
