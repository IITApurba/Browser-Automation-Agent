import asyncio


async def resolve_and_act(
    page,
    action: str,
    description: str,
    explicit_selector: str | None,
    role: str | None = None,
    text: str | None = None,
    attribute_hints: list[str] | None = None,
    retries: int = 2,
) -> bool:
    attribute_hints = attribute_hints or ["data-testid", "aria-label"]

    async def try_locator(locator) -> bool:
        try:
            if action == "click":
                await locator.click(timeout=2000)
            elif action == "type":
                await locator.fill(text or "", timeout=2000)
            else:
                await locator.wait_for(timeout=2000)
            return True
        except Exception:
            return False

    attempt = 0
    while attempt <= retries:
        if explicit_selector and await try_locator(page.locator(explicit_selector)):
            return True

        if role and await try_locator(page.get_by_role(role, name=description)):
            return True

        if text and await try_locator(page.get_by_text(text)):
            return True

        for hint in attribute_hints:
            candidate = f"[{hint}*='{description}']"
            if await try_locator(page.locator(candidate)):
                return True

        attempt += 1
        if attempt <= retries:
            await asyncio.sleep(2**attempt * 0.5)

    return False


async def ai_assisted_repair(page, description: str, dom_snapshot: str) -> str | None:
    """Extension point: in the full system this delegates to
    packages.agent.llm to propose a CSS selector for `description` given a
    truncated `dom_snapshot`. Import is deferred to avoid a circular import
    between browser_tools and agent at module load time.
    """
    from packages.agent import llm  # noqa: F401

    return None
