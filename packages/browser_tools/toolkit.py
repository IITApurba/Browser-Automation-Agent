import re

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright


class BrowserToolkit:
    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("BrowserToolkit not started; call start() first")
        return self._page

    async def start(self, headless: bool = True) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()

    async def stop(self) -> None:
        if self._context is not None:
            await self._context.close()
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    async def navigate(self, url: str) -> None:
        await self.page.goto(url)

    async def click(self, selector: str) -> None:
        await self.page.click(selector)

    async def type_text(self, selector: str, text: str) -> None:
        await self.page.fill(selector, text)

    async def extract(self, schema: dict) -> dict:
        result: dict = {}
        for field_name, spec in schema.items():
            selector = spec["selector"]
            attr = spec.get("attr", "text")
            multiple = spec.get("multiple", False)

            if multiple:
                elements = await self.page.query_selector_all(selector)
                result[field_name] = [await self._read_value(el, attr) for el in elements]
            else:
                element = await self.page.query_selector(selector)
                result[field_name] = await self._read_value(element, attr) if element else None
        return result

    async def _read_value(self, element, attr: str) -> str | None:
        if attr == "text":
            return (await element.text_content() or "").strip()
        return await element.get_attribute(attr)

    async def screenshot(self, path: str) -> None:
        await self.page.screenshot(path=path)

    async def wait_for_selector(self, selector: str, timeout: int = 5000) -> None:
        await self.page.wait_for_selector(selector, timeout=timeout)

    async def dom_snapshot(self, max_len: int = 4000) -> str:
        content = await self.page.content()
        content = re.sub(r"<script.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<style.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"\s+", " ", content).strip()
        return content[:max_len]

    async def solve_captcha_handoff(self) -> dict:
        return {"status": "awaiting_human"}
