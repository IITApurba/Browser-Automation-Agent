import pytest

from packages.browser_tools.selector_strategy import resolve_and_act


@pytest.mark.asyncio
async def test_explicit_selector_works(toolkit, fixture_path):
    await toolkit.navigate(fixture_path("form.html"))

    ok = await resolve_and_act(
        toolkit.page,
        action="click",
        description="Submit",
        explicit_selector="#submit",
    )
    assert ok is True


@pytest.mark.asyncio
async def test_fallback_to_role_when_explicit_selector_broken(toolkit, fixture_path):
    await toolkit.navigate(fixture_path("form.html"))

    ok = await resolve_and_act(
        toolkit.page,
        action="click",
        description="Submit",
        explicit_selector="#does-not-exist",
        role="button",
        retries=0,
    )
    assert ok is True

    result_text = await toolkit.page.text_content("#result")
    assert "Submitted" in result_text
