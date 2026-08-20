"""Track trend collection attempts separately from successful snapshots."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0003"
down_revision: str | None = "20260820_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("last_trend_attempted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE products
        SET last_trend_attempted_at = last_trend_collected_at
        WHERE last_trend_collected_at IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("products", "last_trend_attempted_at")
