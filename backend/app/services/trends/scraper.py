import asyncio
import logging
from urllib.parse import quote

from playwright.async_api import BrowserContext, Response, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.services.trends.parser import (
    TrendSignal,
    TrendsParsingError,
    parse_timeline_response_many,
)

logger = logging.getLogger(__name__)


class TrendsCollectionError(RuntimeError):
    pass


class TrendsRateLimitError(TrendsCollectionError):
    pass


def _keyword_batches(keywords: list[str], batch_size: int) -> list[list[str]]:
    return [keywords[index : index + batch_size] for index in range(0, len(keywords), batch_size)]


async def _collect_batch(
    context: BrowserContext,
    keywords: list[str],
) -> dict[str, TrendSignal]:
    page = await context.new_page()
    url = (
        "https://trends.google.com/trends/explore?"
        f"date=today%203-m&geo=US&q={quote(','.join(keywords), safe=',')}&hl=en"
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
        if navigation is not None and navigation.status == 429:
            raise TrendsRateLimitError("Google Trends page failed with status 429")
        if navigation is not None and navigation.status >= 400:
            raise TrendsCollectionError(
                f"Google Trends page failed with status {navigation.status}"
            )
        response = await asyncio.wait_for(timeline_response, timeout=45)
        if response.status == 429:
            raise TrendsRateLimitError("Google Trends browser request failed with status 429")
        if response.status >= 400:
            raise TrendsCollectionError(f"Google Trends browser request failed with status {response.status}")
        return parse_timeline_response_many(await response.text(), keywords)
    except (TimeoutError, PlaywrightTimeoutError, TrendsParsingError) as exc:
        raise TrendsCollectionError("Google Trends browser timeline was unavailable") from exc
    finally:
        await page.close()


async def collect_google_trends(
    keywords: list[str],
    delay_seconds: float = 2.0,
    batch_size: int = 5,
    attempts: int = 2,
    rate_limit_backoff_seconds: float = 8.0,
) -> dict[str, TrendSignal | TrendsCollectionError]:
    results: dict[str, TrendSignal | TrendsCollectionError] = {}
    if not keywords:
        return results
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
            batches = _keyword_batches(keywords, max(1, min(5, batch_size)))
            for batch_index, batch in enumerate(batches):
                batch_error: TrendsCollectionError | None = None
                for attempt in range(1, max(1, attempts) + 1):
                    try:
                        batch_signals = await _collect_batch(context, batch)
                        results.update(batch_signals)
                        for keyword in batch:
                            if keyword not in batch_signals:
                                results[keyword] = TrendsCollectionError(
                                    "Google Trends returned no timeline for this keyword"
                                )
                        batch_error = None
                        break
                    except TrendsRateLimitError as exc:
                        batch_error = exc
                        logger.warning(
                            "trend_batch_rate_limited batch_size=%s attempt=%s reason=%s",
                            len(batch),
                            attempt,
                            str(exc),
                        )
                        if attempt < max(1, attempts):
                            await asyncio.sleep(rate_limit_backoff_seconds * attempt)
                    except TrendsCollectionError as exc:
                        batch_error = exc
                        logger.warning(
                            "trend_batch_failed batch_size=%s failure=%s reason=%s",
                            len(batch),
                            type(exc).__name__,
                            str(exc),
                        )
                        break
                if batch_error is not None:
                    for keyword in batch:
                        results[keyword] = batch_error
                    if isinstance(batch_error, TrendsRateLimitError):
                        for remaining_batch in batches[batch_index + 1 :]:
                            for keyword in remaining_batch:
                                results[keyword] = batch_error
                        logger.warning(
                            "trend_collection_stopped_after_rate_limit remaining_keywords=%s",
                            sum(len(item) for item in batches[batch_index + 1 :]),
                        )
                        break
                if delay_seconds:
                    await asyncio.sleep(delay_seconds)
        finally:
            await context.close()
            await browser.close()
    return results
