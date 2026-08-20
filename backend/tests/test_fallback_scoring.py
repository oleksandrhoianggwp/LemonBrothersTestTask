from app.services.scoring.fallback import score_with_fallback
from app.services.scoring.types import ScoringInput


def test_fallback_is_deterministic_and_explained() -> None:
    data = ScoringInput(
        title="Portable Neck Fan",
        category="Home & Kitchen",
        price=29.99,
        rating=4.7,
        reviews_count=2500,
        trend_score=72,
        trend_change_percent=18,
        boost_score=12,
    )
    first = score_with_fallback(data)
    second = score_with_fallback(data)
    assert first == second
    assert first.source == "fallback"
    assert 0 <= first.score <= 100
    assert "Score" in first.reasoning


def test_fallback_clamps_all_inputs() -> None:
    result = score_with_fallback(
        ScoringInput(
            title="Outlier",
            category="Test",
            rating=99,
            reviews_count=10**9,
            trend_score=999,
            boost_score=999,
        )
    )
    assert result.score == 100


def test_each_signal_increases_score() -> None:
    baseline = ScoringInput(title="Product", category="Category")
    baseline_score = score_with_fallback(baseline).score
    assert score_with_fallback(baseline.model_copy(update={"rating": 5})).score > baseline_score
    assert score_with_fallback(baseline.model_copy(update={"reviews_count": 10_000})).score > baseline_score
    assert score_with_fallback(baseline.model_copy(update={"trend_score": 100})).score > baseline_score
    assert score_with_fallback(baseline.model_copy(update={"boost_score": 20})).score > baseline_score
