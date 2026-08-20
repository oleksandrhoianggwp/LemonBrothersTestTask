import csv
import io
import json
from dataclasses import dataclass


class TrendsParsingError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TrendSignal:
    trend_score: float
    change_percent: float | None
    raw_summary: dict[str, int | float | str | None]


def _timeline_body(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith(")]}'"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[4:]
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise TrendsParsingError("Google Trends returned an unreadable timeline") from exc


def _signal_from_values(
    values: list[float],
    series_count: int,
    *,
    source: str = "google_trends_browser",
) -> TrendSignal:
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
            "source": source,
            "series_count": series_count,
        },
    )


def _csv_value(raw: str) -> float | None:
    cleaned = raw.strip()
    if not cleaned or cleaned in {"—", "-"}:
        return None
    if cleaned.startswith("<"):
        try:
            upper_bound = float(cleaned[1:])
        except ValueError as exc:
            raise TrendsParsingError("Google Trends CSV contained an invalid value") from exc
        return upper_bound / 2
    try:
        return float(cleaned)
    except ValueError as exc:
        raise TrendsParsingError("Google Trends CSV contained an invalid value") from exc


def parse_trends_csv(raw: str, keywords: list[str]) -> dict[str, TrendSignal]:
    if not keywords:
        return {}
    rows = list(csv.reader(io.StringIO(raw.lstrip("\ufeff"))))
    header_index = next(
        (
            index
            for index, row in enumerate(rows)
            if len(row) > 1
            and row[0].strip().casefold() in {"day", "week", "month", "date", "time"}
        ),
        None,
    )
    if header_index is None:
        raise TrendsParsingError("Google Trends CSV contained no timeline header")

    header = rows[header_index]
    if len(header) - 1 < len(keywords):
        raise TrendsParsingError("Google Trends CSV contained fewer series than requested")

    signals: dict[str, TrendSignal] = {}
    for series_index, keyword in enumerate(keywords, start=1):
        values: list[float] = []
        for row in rows[header_index + 1 :]:
            if len(row) <= series_index:
                continue
            value = _csv_value(row[series_index])
            if value is not None:
                values.append(value)
        if values:
            signals[keyword] = _signal_from_values(
                values,
                len(keywords),
                source="google_trends_csv_export",
            )

    if not signals:
        raise TrendsParsingError("Google Trends CSV timeline contained no values")
    return signals


def parse_timeline_response_many(
    raw: str,
    keywords: list[str],
) -> dict[str, TrendSignal]:
    if not keywords:
        return {}
    try:
        timeline = _timeline_body(raw)["default"]["timelineData"]
        values_by_series: list[list[float]] = [[] for _ in keywords]
        for point in timeline:
            point_values = point.get("value") or []
            for index in range(min(len(point_values), len(keywords))):
                values_by_series[index].append(float(point_values[index]))
    except (KeyError, TypeError, ValueError) as exc:
        raise TrendsParsingError("Google Trends returned an unreadable timeline") from exc

    signals = {
        keyword: _signal_from_values(values, len(keywords))
        for keyword, values in zip(keywords, values_by_series, strict=True)
        if values
    }
    if not signals:
        raise TrendsParsingError("Google Trends timeline contained no values")
    return signals


def parse_timeline_response(raw: str) -> TrendSignal:
    return parse_timeline_response_many(raw, ["keyword"])["keyword"]
