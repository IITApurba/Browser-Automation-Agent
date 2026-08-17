IFRAME_PATTERNS = ["recaptcha", "hcaptcha", "turnstile"]
CAPTCHA_SELECTORS = [".g-recaptcha", "#g-recaptcha", ".h-captcha", ".cf-turnstile"]
CAPTCHA_PHRASES = ["verify you are human", "i'm not a robot", "im not a robot"]


async def detect_captcha(page) -> bool:
    for frame in page.frames:
        url = (frame.url or "").lower()
        if any(pattern in url for pattern in IFRAME_PATTERNS):
            return True

    for selector in CAPTCHA_SELECTORS:
        if await page.query_selector(selector) is not None:
            return True

    body_text = (await page.content()).lower()
    if any(phrase in body_text for phrase in CAPTCHA_PHRASES):
        return True

    return False
