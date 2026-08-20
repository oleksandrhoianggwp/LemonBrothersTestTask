import math

from app.services.scoring.types import ScoringInput, ScoringResult


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def score_with_fallback(data: ScoringInput) -> ScoringResult:
    trend_points = (
        _clamp(data.trend_score, 0, 100) / 100 * 40
        if data.trend_data_status != "unavailable"
        else 0.0
    )
    rating_points = _clamp(data.rating or 0, 0, 5) / 5 * 25
    normalized_reviews = math.log10(1 + max(0, data.reviews_count)) / math.log10(10_001)
    review_points = _clamp(normalized_reviews, 0, 1) * 15
    boost_points = _clamp(data.boost_score, 0, 20)
    score = round(_clamp(trend_points + rating_points + review_points + boost_points, 0, 100))

    if data.trend_data_status == "fresh":
        trend_reason = f"fresh search trend contributes {trend_points:.1f}/40"
    elif data.trend_data_status == "stale":
        trend_reason = f"stale saved search trend contributes {trend_points:.1f}/40"
    else:
        trend_reason = "search trend is unavailable and contributes 0.0/40"
    reasoning = (
        f"Score {score}/100: {trend_reason}, "
        f"product rating contributes {rating_points:.1f}/25, review confidence "
        f"contributes {review_points:.1f}/15, and internal sales similarity "
        f"contributes {boost_points:.1f}/20."
    )
    return ScoringResult(
        score=score,
        reasoning=reasoning,
        source="fallback",
        provider="deterministic",
    )
