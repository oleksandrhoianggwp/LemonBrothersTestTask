"""Track the last successful trend collection per product."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0002"
down_revision: str | None = "20260820_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("last_trend_collected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE products AS product
        SET last_trend_collected_at = latest.collected_at
        FROM (
            SELECT product_id, MAX(collected_at) AS collected_at
            FROM trend_snapshots
            GROUP BY product_id
        ) AS latest
        WHERE latest.product_id = product.id
        """
    )


def downgrade() -> None:
    op.drop_column("products", "last_trend_collected_at")
