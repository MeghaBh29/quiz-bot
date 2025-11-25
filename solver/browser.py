# solver/browser.py
# Async Playwright helper to fetch a JS-rendered page's HTML and visible text.

from playwright.async_api import async_playwright

async def fetch_rendered_page(url: str, wait_ms: int = 1000, timeout_ms: int = 60000):
    """
    Launch headless chromium, visit the page, wait for network idle and optional extra time,
    then return a dict {'html': <page html>, 'text': <visible body text>}.
    """
    async with async_playwright() as p:
        # Launch with --no-sandbox on many container hosts; remove if not needed.
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page()
        # goto with networkidle so SPA content can load
        await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        # small extra wait to let animations / late JS finish
        await page.wait_for_timeout(wait_ms)
        html = await page.content()
        try:
            text = await page.inner_text("body")
        except Exception:
            text = html
        await browser.close()
        return {"html": html, "text": text}
