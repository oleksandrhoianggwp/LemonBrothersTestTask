from decimal import Decimal
from pathlib import Path

from app.services.amazon.parser import (
    parse_amazon_html,
    parse_rating,
    parse_review_count,
)


def test_parse_amazon_fixture_normalizes_required_fields() -> None:
    html = (Path(__file__).parent / "fixtures" / "amazon_bestsellers.html").read_text(
        encoding="utf-8"
    )
    products = parse_amazon_html(html, "https://www.amazon.com/Best-Sellers/zgbs")
    assert len(products) == 2
    first = products[0]
    assert first.title == "Portable Rechargeable Neck Fan"
    assert first.category == "Best Sellers in Home & Kitchen"
    assert first.price == Decimal("29.99")
    assert first.rating == 4.6
    assert first.reviews_count == 12_345
    assert first.product_url == "https://www.amazon.com/dp/B0ABC12345"
    assert first.image_url == "https://images.example/fan.jpg"
    assert first.asin == "B0ABC12345"


def test_missing_optional_values_are_preserved_without_fabrication() -> None:
    html = (Path(__file__).parent / "fixtures" / "amazon_bestsellers.html").read_text(
        encoding="utf-8"
    )
    second = parse_amazon_html(html, "https://www.amazon.com")[1]
    assert second.price == Decimal("1249.50")
    assert second.rating is None
    assert second.reviews_count == 0
    assert second.image_url == "https://www.amazon.com/images/lamp.jpg"


def test_review_and_rating_normalization() -> None:
    assert parse_review_count("2.5K ratings") == 2500
    assert parse_review_count("1 234") == 1234
    assert parse_rating("4,8 out of 5") == 4.8
