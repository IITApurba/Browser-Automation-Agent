import pytest


@pytest.mark.asyncio
async def test_extract_listing_items(toolkit, fixture_path):
    await toolkit.navigate(fixture_path("listing.html"))

    schema = {
        "title": {"selector": ".item .item-title", "attr": "text", "multiple": True},
        "price": {"selector": ".item .item-price", "attr": "text", "multiple": True},
    }
    data = await toolkit.extract(schema)

    assert len(data["title"]) == 5
    assert len(data["price"]) == 5
    assert data["title"][0] == "Wireless Mouse"
    assert data["price"][0] == "$19.99"


@pytest.mark.asyncio
async def test_login_flow_sets_welcome_and_storage(toolkit, fixture_path):
    await toolkit.navigate(fixture_path("login.html"))

    await toolkit.type_text("#username", "alice")
    await toolkit.type_text("#password", "secret")
    await toolkit.click("#submit")

    is_visible = await toolkit.page.is_visible("#welcome")
    assert is_visible

    logged_in = await toolkit.page.evaluate("localStorage.getItem('logged_in')")
    assert logged_in == "true"
