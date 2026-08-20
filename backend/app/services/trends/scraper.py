import asyncio
import logging
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator, Page, Response, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.services.trends.parser import (
    TrendSignal,
    TrendsParsingError,
    parse_trends_csv,
    parse_timeline_response_many,
)

logger = logging.getLogger(__name__)


class TrendsCollectionError(RuntimeError):
    pass


class TrendsRateLimitError(TrendsCollectionError):
    pass


_DOWNLOAD_SELECTORS = (
    'button[aria-label*="download" i]',
    '[role="button"][aria-label*="download" i]',
    'button[aria-label*="csv" i]',
    'button[title*="download" i]',
    ".widget-actions-item.export",
    'button:has-text("Download")',
    'button:has-text("file_download")',
)


def _keyword_batches(keywords: list[str], batch_size: int) -> list[list[str]]:
    return [keywords[index : index + batch_size] for index in range(0, len(keywords), batch_size)]


async def _download_button(page: Page) -> Locator | None:
    heading = page.get_by_text("Interest over time", exact=True).first
    try:
        await heading.wait_for(state="visible", timeout=20_000)
    except PlaywrightTimeoutError:
        logger.info("trends_csv_export_unavailable reason=interest_widget_missing")
        return None

    scopes: list[Page | Locator] = []
    widget = heading.locator("xpath=ancestor::widget[1]")
    if await widget.count():
        scopes.append(widget)
    timeseries_widget = page.locator('widget[type="TIMESERIES"]').first
    if await timeseries_widget.count():
        scopes.append(timeseries_widget)
    scopes.append(page)

    for scope in scopes:
        for selector in _DOWNLOAD_SELECTORS:
            button = scope.locator(selector).first
            if await button.count() and await button.is_visible() and await button.is_enabled():
                return button
    logger.info("trends_csv_export_unavailable reason=download_control_missing")
    return None


async def _collect_exported_csv(
    page: Page,
    keywords: list[str],
) -> dict[str, TrendSignal] | None:
    button = await _download_button(page)
    if button is None:
        return None
    try:
        async with page.expect_download(timeout=15_000) as download_info:
            await button.click(timeout=10_000)
        download = await download_info.value
        download_path = await download.path()
        if download_path is None:
            raise TrendsCollectionError("Google Trends CSV download had no local path")
        raw = await asyncio.to_thread(Path(download_path).read_text, encoding="utf-8-sig")
        signals = parse_trends_csv(raw, keywords)
        logger.info(
            "trends_csv_export_collected series=%s filename=%s",
            len(signals),
            download.suggested_filename,
        )
        return signals
    except (OSError, PlaywrightError, TrendsParsingError, TrendsCollectionError) as exc:
        logger.info(
            "trends_csv_export_unavailable reason=%s",
            type(exc).__name__,
        )
        return None


async def _collect_batch(
    page: Page,
    keywords: list[str],
) -> dict[str, TrendSignal]:
    url = (
        "https://trends.google.com/trends/explore?"
        f"date=today%203-m&geo=US&q={quote(','.join(keywords), safe=',')}&hl=en-US"
    )
    loop = asyncio.get_running_loop()
    timeline_response: asyncio.Future[Response] = loop.create_future()

    def capture_response(response: Response) -> None:
        if (
            "/trends/api/widgetdata/multiline" in response.url
            and not timeline_response.done()
        ):
            timeline_response.set_result(response)

    page.on("response", capture_response)
    try:
        navigation = await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        if navigation is not None and navigation.status == 429:
            raise TrendsRateLimitError("Google Trends page failed with status 429")
        if navigation is not None and navigation.status >= 400:
            raise TrendsCollectionError(
                f"Google Trends page failed with status {navigation.status}"
            )
        await _accept_consent_if_present(page)

        if timeline_response.done():
            captured = timeline_response.result()
            if captured.status == 429:
                raise TrendsRateLimitError(
                    "Google Trends browser request failed with status 429"
                )
            if captured.status >= 400:
                raise TrendsCollectionError(
                    f"Google Trends browser request failed with status {captured.status}"
                )

        exported = await _collect_exported_csv(page, keywords)
        if exported is not None:
            return exported

        response = await asyncio.wait_for(timeline_response, timeout=45)
        if response.status == 429:
            raise TrendsRateLimitError("Google Trends browser request failed with status 429")
        if response.status >= 400:
            raise TrendsCollectionError(f"Google Trends browser request failed with status {response.status}")
        return parse_timeline_response_many(await response.text(), keywords)
    except (TimeoutError, PlaywrightTimeoutError, TrendsParsingError) as exc:
        raise TrendsCollectionError("Google Trends browser timeline was unavailable") from exc
    finally:
        page.remove_listener("response", capture_response)


async def _accept_consent_if_present(page: Page) -> bool:
    selectors = (
        'button:has-text("Accept all")',
        'button:has-text("I agree")',
        'button:has-text("Agree")',
    )
    for selector in selectors:
        button = page.locator(selector).first
        if await button.count() and await button.is_visible():
            await button.click(timeout=5_000)
            await page.wait_for_load_state("domcontentloaded", timeout=15_000)
            logger.info("trends_consent_accepted")
            return True
    return False


async def _collect_batches(
    page: Page,
    keywords: list[str],
    delay_seconds: float,
    batch_size: int,
) -> dict[str, TrendSignal | TrendsCollectionError]:
    results: dict[str, TrendSignal | TrendsCollectionError] = {}
    batches = _keyword_batches(keywords, max(1, min(5, batch_size)))
    for batch_index, batch in enumerate(batches):
        try:
            batch_signals = await _collect_batch(page, batch)
            results.update(batch_signals)
            for keyword in batch:
                if keyword not in batch_signals:
                    results[keyword] = TrendsCollectionError(
                        "Google Trends returned no timeline for this keyword"
                    )
        except TrendsRateLimitError as exc:
            for affected_batch in batches[batch_index:]:
                for keyword in affected_batch:
                    results[keyword] = exc
            logger.warning(
                "trend_collection_stopped_after_rate_limit affected_keywords=%s reason=%s",
                sum(len(item) for item in batches[batch_index:]),
                str(exc),
            )
            break
        except TrendsCollectionError as exc:
            for keyword in batch:
                results[keyword] = exc
            logger.warning(
                "trend_batch_failed batch_size=%s failure=%s reason=%s",
                len(batch),
                type(exc).__name__,
                str(exc),
            )
        if delay_seconds and batch_index < len(batches) - 1:
            await asyncio.sleep(delay_seconds)
    return results


async def collect_google_trends(
    keywords: list[str],
    delay_seconds: float = 2.0,
    batch_size: int = 5,
) -> dict[str, TrendSignal | TrendsCollectionError]:
    unique_keywords = list(
        dict.fromkeys(keyword.strip() for keyword in keywords if keyword.strip())
    )
    if not unique_keywords:
        return {}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="en-US",
            timezone_id="America/New_York",
        )
        page = await context.new_page()
        page.set_default_timeout(15_000)
        try:
            return await _collect_batches(
                page,
                unique_keywords,
                delay_seconds=delay_seconds,
                batch_size=batch_size,
            )
        finally:
            await page.close()
            await context.close()
            await browser.close()
