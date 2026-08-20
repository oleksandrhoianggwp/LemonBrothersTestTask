from pathlib import Path

from app.services.trends.keywords import extract_keyword
from app.services.trends.parser import parse_timeline_response


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
