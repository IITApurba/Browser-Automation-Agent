import pytest

from packages.browser_tools.captcha_detect import detect_captcha


@pytest.mark.asyncio
async def test_captcha_detected_initially(toolkit, fixture_path):
    await toolkit.navigate(fixture_path("captcha_mock.html"))

    assert await detect_captcha(toolkit.page) is True


@pytest.mark.asyncio
async def test_captcha_cleared_after_human_check(toolkit, fixture_path):
    await toolkit.navigate(fixture_path("captcha_mock.html"))

    await toolkit.page.check("#human-check")
    await toolkit.page.evaluate(
        "document.getElementById('g-recaptcha') && document.getElementById('g-recaptcha').remove()"
    )

    assert await detect_captcha(toolkit.page) is False
