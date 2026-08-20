from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TrendSnapshot(Base):
    __tablename__ = "trend_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    keyword: Mapped[str] = mapped_column(String(255), index=True)
    trend_score: Mapped[float] = mapped_column(Float)
    change_percent: Mapped[float | None] = mapped_column(Float)
    raw_summary: Mapped[dict | None] = mapped_column(JSON)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    product: Mapped["Product"] = relationship(back_populates="trend_snapshots")  # noqa: F821
