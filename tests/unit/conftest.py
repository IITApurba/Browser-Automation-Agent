from pathlib import Path

import pytest
import pytest_asyncio

from packages.browser_tools.toolkit import BrowserToolkit

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "site"


@pytest.fixture
def fixture_path():
    def _fixture_path(name: str) -> str:
        return (FIXTURES_DIR / name).resolve().as_uri()

    return _fixture_path


@pytest_asyncio.fixture
async def toolkit():
    kit = BrowserToolkit()
    await kit.start(headless=True)
    yield kit
    await kit.stop()
