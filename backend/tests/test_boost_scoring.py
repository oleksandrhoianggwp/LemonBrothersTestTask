from app.services.scoring.boost import HistoricalProduct, calculate_sales_boost

HISTORY = [
    HistoricalProduct(
        title="Portable Neck Fan",
        category="Home & Kitchen",
        keywords=("cooling", "portable fan", "summer"),
    )
]


def test_exact_category_match_adds_ten_points() -> None:
    result = calculate_sales_boost("Unrelated", " home & KITCHEN ", "different", HISTORY)
    assert result == 10


def test_keyword_overlap_adds_up_to_ten_points() -> None:
    result = calculate_sales_boost("Portable Cooling Fan", "Electronics", "neck fan", HISTORY)
    assert 0 < result <= 10


def test_no_match_returns_zero() -> None:
    result = calculate_sales_boost("Ceramic Mug", "Dining", "coffee cup", HISTORY)
    assert result == 0


def test_combined_match_is_clamped_to_twenty() -> None:
    result = calculate_sales_boost(
        "Portable Neck Fan", "Home & Kitchen", "cooling summer", HISTORY
    )
    assert result == 20
