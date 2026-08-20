from pathlib import Path

from app.services.trends.keywords import extract_keyword
from app.services.trends.parser import parse_timeline_response, parse_timeline_response_many
from unittest.mock import AsyncMock, patch

import pytest

from app.services.trends.scraper import (
    TrendsRateLimitError,
    _collect_batches,
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
