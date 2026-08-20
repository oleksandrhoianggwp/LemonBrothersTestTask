from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Float, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    asin: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(255), default="Unknown")
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    rating: Mapped[float | None] = mapped_column(Float)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    product_url: Mapped[str] = mapped_column(Text, unique=True)
    image_url: Mapped[str] = mapped_column(Text)
    keyword: Mapped[str | None] = mapped_column(String(255), index=True)
    boost_score: Mapped[float] = mapped_column(Float, default=0)
    trend_score: Mapped[float] = mapped_column(Float, default=0)
    trend_change_percent: Mapped[float | None] = mapped_column(Float)
    score: Mapped[int | None] = mapped_column(Integer)
    reasoning: Mapped[str | None] = mapped_column(Text)
    score_source: Mapped[str | None] = mapped_column(String(32))
    scoring_provider: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_trend_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_trend_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    trend_snapshots: Mapped[list["TrendSnapshot"]] = relationship(  # noqa: F821
        back_populates="product", cascade="all, delete-orphan"
    )
