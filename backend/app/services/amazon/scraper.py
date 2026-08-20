import asyncio
import logging

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.services.amazon.parser import ScrapedProduct, parse_amazon_html

logger = logging.getLogger(__name__)


class AmazonScrapingError(RuntimeError):
    pass


BLOCK_MARKERS = (
    "enter the characters you see below",
    "sorry, we just need to make sure you're not a robot",
    "automated access to amazon data",
)


async def scrape_amazon_bestsellers(
    url: str,
    max_products: int = 20,
    attempts: int = 2,
) -> list[ScrapedProduct]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context(
                    locale="en-US",
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                    await page.wait_for_timeout(2_000)
                    html = await page.content()
                finally:
                    await context.close()
                    await browser.close()
            lowered = html.lower()
            if any(marker in lowered for marker in BLOCK_MARKERS):
                raise AmazonScrapingError("Amazon blocked the automated browser run")
            products = parse_amazon_html(html, url)[:max_products]
            if not products:
                raise AmazonScrapingError("Amazon page contained no parseable product cards")
            return products
        except (PlaywrightTimeoutError, AmazonScrapingError) as exc:
            last_error = exc
            logger.warning("amazon_scrape_attempt_failed attempt=%s failure=%s", attempt, type(exc).__name__)
            if attempt < attempts:
                await asyncio.sleep(attempt)
    raise AmazonScrapingError(str(last_error) if last_error else "Amazon scraping failed")
