"""Create application tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asin", sa.String(20)),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("category", sa.String(255), nullable=False),
        sa.Column("price", sa.Numeric(12, 2)),
        sa.Column("rating", sa.Float()),
        sa.Column("reviews_count", sa.Integer(), nullable=False),
        sa.Column("product_url", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("keyword", sa.String(255)),
        sa.Column("boost_score", sa.Float(), nullable=False),
        sa.Column("trend_score", sa.Float(), nullable=False),
        sa.Column("trend_change_percent", sa.Float()),
        sa.Column("score", sa.Integer()),
        sa.Column("reasoning", sa.Text()),
        sa.Column("score_source", sa.String(32)),
        sa.Column("scoring_provider", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True)),
        sa.Column("last_scored_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("asin"),
        sa.UniqueConstraint("product_url"),
    )
    op.create_index("ix_products_asin", "products", ["asin"])
    op.create_index("ix_products_keyword", "products", ["keyword"])
    op.create_table(
        "sales_boost_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("category", sa.String(255), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("title_normalized", sa.String(500), nullable=False),
        sa.Column("category_normalized", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("title_normalized", "category_normalized"),
    )
    op.create_index("ix_sales_boost_products_title_normalized", "sales_boost_products", ["title_normalized"])
    op.create_index("ix_sales_boost_products_category_normalized", "sales_boost_products", ["category_normalized"])
    op.create_table(
        "trend_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("keyword", sa.String(255), nullable=False),
        sa.Column("trend_score", sa.Float(), nullable=False),
        sa.Column("change_percent", sa.Float()),
        sa.Column("raw_summary", sa.JSON()),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trend_snapshots_product_id", "trend_snapshots", ["product_id"])
    op.create_index("ix_trend_snapshots_keyword", "trend_snapshots", ["keyword"])
    op.create_index("ix_trend_snapshots_collected_at", "trend_snapshots", ["collected_at"])


def downgrade() -> None:
    op.drop_table("trend_snapshots")
    op.drop_table("sales_boost_products")
    op.drop_table("products")
    op.drop_table("users")
