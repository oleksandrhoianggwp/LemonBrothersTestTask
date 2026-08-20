import json
from dataclasses import dataclass


class TrendsParsingError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TrendSignal:
    trend_score: float
    change_percent: float | None
    raw_summary: dict[str, int | float | str | None]


def parse_timeline_response(raw: str) -> TrendSignal:
    cleaned = raw.strip()
    if cleaned.startswith(")]}'"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[4:]
    try:
        body = json.loads(cleaned)
        timeline = body["default"]["timelineData"]
        values = [float(point["value"][0]) for point in timeline if point.get("value")]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise TrendsParsingError("Google Trends returned an unreadable timeline") from exc
    if not values:
        raise TrendsParsingError("Google Trends timeline contained no values")

    window = min(4, max(1, len(values) // 2))
    recent = sum(values[-window:]) / window
    previous_values = values[-2 * window : -window]
    previous = sum(previous_values) / len(previous_values) if previous_values else None
    if previous is None:
        change = None
    elif previous == 0:
        change = 100.0 if recent > 0 else 0.0
    else:
        change = ((recent - previous) / previous) * 100
    score = max(0.0, min(100.0, recent))
    return TrendSignal(
        trend_score=round(score, 2),
        change_percent=round(change, 2) if change is not None else None,
        raw_summary={
            "points": len(values),
            "first_value": values[0],
            "last_value": values[-1],
            "recent_average": round(recent, 2),
            "previous_average": round(previous, 2) if previous is not None else None,
            "source": "google_trends_browser",
        },
    )
