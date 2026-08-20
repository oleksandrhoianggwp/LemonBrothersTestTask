from datetime import datetime

from sqlalchemy import DateTime, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SalesBoostProduct(Base):
    __tablename__ = "sales_boost_products"
    __table_args__ = (UniqueConstraint("title_normalized", "category_normalized"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(255))
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    title_normalized: Mapped[str] = mapped_column(String(500), index=True)
    category_normalized: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
