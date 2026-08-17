from mcp.server.fastmcp import FastMCP

from packages.mcp_server import tool_definitions as td

mcp = FastMCP("browser-automation-agent")


@mcp.tool()
async def browser_navigate(url: str) -> dict:
    return await td.browser_navigate(url)


@mcp.tool()
async def browser_click(selector: str) -> dict:
    return await td.browser_click(selector)


@mcp.tool()
async def browser_type(selector: str, text: str) -> dict:
    return await td.browser_type(selector, text)


@mcp.tool()
async def browser_extract(schema: dict) -> dict:
    return await td.browser_extract(schema)


@mcp.tool()
async def browser_screenshot(path: str) -> dict:
    return await td.browser_screenshot(path)


@mcp.tool()
async def browser_wait_for_selector(selector: str, timeout: int = 5000) -> dict:
    return await td.browser_wait_for_selector(selector, timeout)


@mcp.tool()
async def browser_get_dom_snapshot(max_len: int = 4000) -> dict:
    return await td.browser_get_dom_snapshot(max_len)


@mcp.tool()
async def browser_login(
    url: str,
    username_selector: str,
    password_selector: str,
    submit_selector: str,
    username: str,
    password: str,
) -> dict:
    return await td.browser_login(url, username_selector, password_selector, submit_selector, username, password)


@mcp.tool()
async def browser_captcha_status() -> dict:
    return await td.browser_captcha_status()


@mcp.tool()
async def task_create_run(task_id: str) -> dict:
    return await td.task_create_run(task_id)


@mcp.tool()
async def task_get_run_status(run_id: str) -> dict:
    return await td.task_get_run_status(run_id)
