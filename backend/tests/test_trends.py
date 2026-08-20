import asyncio
from pathlib import Path
from types import SimpleNamespace

from app.services.trends.keywords import extract_keyword
from app.services.trends.parser import (
    TrendSignal,
    parse_timeline_response,
    parse_timeline_response_many,
    parse_trends_csv,
)
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.trends.scraper import (
    TrendsRateLimitError,
    _collect_batch,
    _collect_batches,
    _collect_exported_csv,
    _keyword_batches,
)


def test_keyword_extraction_is_deterministic() -> None:
    title = "Portable Rechargeable Neck Fan for Home and Office"
    assert extract_keyword(title) == "portable rechargeable neck fan"
    assert extract_keyword(title) == extract_keyword(title)


def test_trend_timeline_normalization() -> None:
    raw = (Path(__file__).parent / "fixtures" / "google_trends_timeline.json").read_text(
        encoding="utf-8"
    )
    signal = parse_timeline_response(raw)
    assert signal.trend_score == 75
    assert signal.change_percent == 114.29
    assert signal.raw_summary["points"] == 8
    assert signal.raw_summary["source"] == "google_trends_browser"


def test_multi_keyword_timeline_is_split_into_independent_signals() -> None:
    raw = ")]}'\n" + """{
      "default": {
        "timelineData": [
          {"value": [10, 80]},
          {"value": [20, 70]},
          {"value": [30, 60]},
          {"value": [40, 50]}
        ]
      }
    }"""
    signals = parse_timeline_response_many(raw, ["first", "second"])
    assert signals["first"].trend_score == 35
    assert signals["first"].change_percent == 133.33
    assert signals["second"].trend_score == 55
    assert signals["second"].change_percent == -26.67
    assert signals["first"].raw_summary["series_count"] == 2


def test_google_trends_csv_export_is_parsed_into_independent_signals() -> None:
    raw = """Category: All categories

Week,portable fan: (United States),mini blender: (United States)
2026-06-21,10,80
2026-06-28,20,70
2026-07-05,30,60
2026-07-12,40,50
2026-07-19,50,40
2026-07-26,60,30
2026-08-02,70,20
2026-08-09,80,10
"""
    signals = parse_trends_csv(raw, ["portable fan", "mini blender"])

    assert signals["portable fan"].trend_score == 65
    assert signals["portable fan"].change_percent == 160
    assert signals["mini blender"].trend_score == 25
    assert signals["mini blender"].change_percent == -61.54
    assert signals["portable fan"].raw_summary["source"] == "google_trends_csv_export"


@pytest.mark.asyncio
async def test_playwright_collection_prefers_csv_export() -> None:
    page = MagicMock()
    page.goto = AsyncMock(return_value=SimpleNamespace(status=200))
    exported = {
        "portable fan": TrendSignal(
            trend_score=64,
            change_percent=12.5,
            raw_summary={"source": "google_trends_csv_export"},
        )
    }
    with (
        patch(
            "app.services.trends.scraper._accept_consent_if_present",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.services.trends.scraper._collect_exported_csv",
            new=AsyncMock(return_value=exported),
        ) as export_csv,
        patch("app.services.trends.scraper.parse_timeline_response_many") as parse_network,
    ):
        result = await _collect_batch(page, ["portable fan"])

    assert result == exported
    export_csv.assert_awaited_once_with(page, ["portable fan"])
    parse_network.assert_not_called()


@pytest.mark.asyncio
async def test_playwright_download_is_read_and_parsed(tmp_path: Path) -> None:
    csv_path = tmp_path / "multiTimeline.csv"
    csv_path.write_text(
        "Week,portable fan: (United States)\n"
        "2026-07-19,20\n"
        "2026-07-26,40\n"
        "2026-08-02,60\n"
        "2026-08-09,80\n",
        encoding="utf-8",
    )
    page = MagicMock()
    button = MagicMock()
    button.click = AsyncMock()
    download = MagicMock(suggested_filename="multiTimeline.csv")
    download.path = AsyncMock(return_value=str(csv_path))
    download_value = asyncio.get_running_loop().create_future()
    download_value.set_result(download)
    download_context = MagicMock()
    download_context.__aenter__ = AsyncMock(
        return_value=SimpleNamespace(value=download_value)
    )
    download_context.__aexit__ = AsyncMock(return_value=False)
    page.expect_download.return_value = download_context

    with patch(
        "app.services.trends.scraper._download_button",
        new=AsyncMock(return_value=button),
    ):
        signals = await _collect_exported_csv(page, ["portable fan"])

    assert signals is not None
    assert signals["portable fan"].trend_score == 70
    assert signals["portable fan"].raw_summary["source"] == "google_trends_csv_export"
    page.expect_download.assert_called_once_with(timeout=15_000)
    button.click.assert_awaited_once_with(timeout=10_000)


@pytest.mark.asyncio
async def test_playwright_collection_uses_network_fallback_when_export_is_missing() -> None:
    raw = """{
      "default": {
        "timelineData": [
          {"value": [20]},
          {"value": [40]},
          {"value": [60]},
          {"value": [80]}
        ]
      }
    }"""
    page = MagicMock()
    captured_response = MagicMock(
        status=200,
        url="https://trends.google.com/trends/api/widgetdata/multiline",
    )
    captured_response.text = AsyncMock(return_value=raw)
    response_handler = None

    def remember_handler(event: str, handler: object) -> None:
        nonlocal response_handler
        assert event == "response"
        response_handler = handler

    async def navigate(*args: object, **kwargs: object) -> SimpleNamespace:
        assert response_handler is not None
        response_handler(captured_response)
        return SimpleNamespace(status=200)

    page.on.side_effect = remember_handler
    page.goto = AsyncMock(side_effect=navigate)
    with (
        patch(
            "app.services.trends.scraper._accept_consent_if_present",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.services.trends.scraper._collect_exported_csv",
            new=AsyncMock(return_value=None),
        ),
    ):
        signals = await _collect_batch(page, ["portable fan"])

    assert signals["portable fan"].trend_score == 70
    assert signals["portable fan"].raw_summary["source"] == "google_trends_browser"


@pytest.mark.asyncio
async def test_initial_document_429_does_not_try_csv_export() -> None:
    page = MagicMock()
    page.goto = AsyncMock(return_value=SimpleNamespace(status=429))
    with patch(
        "app.services.trends.scraper._collect_exported_csv",
        new=AsyncMock(),
    ) as export_csv:
        with pytest.raises(TrendsRateLimitError):
            await _collect_batch(page, ["portable fan"])

    export_csv.assert_not_awaited()


def test_keywords_are_batched_at_google_comparison_limit() -> None:
    keywords = [f"keyword-{index}" for index in range(12)]
    assert _keyword_batches(keywords, 5) == [keywords[:5], keywords[5:10], keywords[10:]]


@pytest.mark.asyncio
async def test_confirmed_429_stops_after_one_batch_attempt() -> None:
    keywords = [f"keyword-{index}" for index in range(12)]
    collect = AsyncMock(side_effect=TrendsRateLimitError("HTTP 429"))
    with patch("app.services.trends.scraper._collect_batch", collect):
        results = await _collect_batches(
            AsyncMock(),
            keywords,
            delay_seconds=0,
            batch_size=5,
        )

    assert collect.await_count == 1
    assert set(results) == set(keywords)
    assert all(isinstance(result, TrendsRateLimitError) for result in results.values())
