from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asin: str | None
    title: str
    category: str
    price: Decimal | None
    rating: float | None
    reviews_count: int
    product_url: str
    image_url: str
    keyword: str | None
    boost_score: float
    trend_score: float
    trend_change_percent: float | None
    score: int | None
    reasoning: str | None
    score_source: str | None
    scoring_provider: str | None
    updated_at: datetime
    last_scraped_at: datetime | None
    last_trend_collected_at: datetime | None
    last_trend_attempted_at: datetime | None
    last_scored_at: datetime | None


class ProductList(BaseModel):
    items: list[ProductRead]
    total: int
