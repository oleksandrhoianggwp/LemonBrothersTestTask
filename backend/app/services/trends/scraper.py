import asyncio
import logging
from urllib.parse import quote

from playwright.async_api import BrowserContext, Response, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.services.trends.parser import TrendSignal, TrendsParsingError, parse_timeline_response

logger = logging.getLogger(__name__)


class TrendsCollectionError(RuntimeError):
    pass


async def _collect_one(context: BrowserContext, keyword: str) -> TrendSignal:
    page = await context.new_page()
    url = (
        "https://trends.google.com/trends/explore?"
        f"date=today%203-m&geo=US&q={quote(keyword)}&hl=en"
    )
    try:
        loop = asyncio.get_running_loop()
        timeline_response: asyncio.Future[Response] = loop.create_future()

        def capture_response(response: Response) -> None:
            response_url = response.url
            if (
                "/trends/api/widgetdata/multiline" in response_url
                and not timeline_response.done()
            ):
                timeline_response.set_result(response)

        page.on("response", capture_response)
        navigation = await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        if navigation is not None and navigation.status >= 400:
            raise TrendsCollectionError(
                f"Google Trends page failed with status {navigation.status}"
            )
        response = await asyncio.wait_for(timeline_response, timeout=45)
        if response.status >= 400:
            raise TrendsCollectionError(f"Google Trends browser request failed with status {response.status}")
        return parse_timeline_response(await response.text())
    except (TimeoutError, PlaywrightTimeoutError, TrendsParsingError) as exc:
        raise TrendsCollectionError("Google Trends browser timeline was unavailable") from exc
    finally:
        await page.close()


async def collect_google_trends(
    keywords: list[str],
    delay_seconds: float = 0.5,
) -> dict[str, TrendSignal | TrendsCollectionError]:
    results: dict[str, TrendSignal | TrendsCollectionError] = {}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"
            ),
        )
        try:
            for keyword in keywords:
                try:
                    results[keyword] = await _collect_one(context, keyword)
                except TrendsCollectionError as exc:
                    logger.warning(
                        "trend_collection_failed keyword_length=%s failure=%s",
                        len(keyword),
                        type(exc).__name__,
                    )
                    results[keyword] = exc
                if delay_seconds:
                    await asyncio.sleep(delay_seconds)
        finally:
            await context.close()
            await browser.close()
    return results
