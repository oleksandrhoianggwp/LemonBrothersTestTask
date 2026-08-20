import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.product import Product
from app.models.sales_boost import SalesBoostProduct
from app.services.scoring.boost import HistoricalProduct, calculate_sales_boost
from app.services.scoring.engine import ScoringEngine
from app.services.scoring.types import ScoringInput
from app.services.trends.keywords import extract_keyword
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.scoring.rescore_all_products")
def rescore_all_products(product_ids: list[int] | None = None) -> dict[str, int]:
    logger.info("product_scoring_started")
    settings = get_settings()
    engine = ScoringEngine(settings)
    with SessionLocal() as db:
        historical_rows = list(db.scalars(select(SalesBoostProduct)).all())
        history = [
            HistoricalProduct(
                title=row.title,
                category=row.category,
                keywords=tuple(row.keywords or []),
            )
            for row in historical_rows
        ]
        if product_ids is None:
            target_product_ids = list(db.scalars(select(Product.id)).all())
        else:
            requested_ids = list(dict.fromkeys(product_ids))
            target_product_ids = list(
                db.scalars(select(Product.id).where(Product.id.in_(requested_ids))).all()
            )
    scored = 0
    for product_id in target_product_ids:
        with SessionLocal.begin() as db:
            product = db.get(Product, product_id)
            if product is None:
                continue
            keyword = product.keyword or extract_keyword(product.title)
            boost = calculate_sales_boost(product.title, product.category, keyword, history)
            result = engine.score(
                ScoringInput(
                    title=product.title,
                    category=product.category,
                    price=float(product.price) if product.price is not None else None,
                    rating=product.rating,
                    reviews_count=product.reviews_count,
                    trend_score=product.trend_score,
                    trend_change_percent=product.trend_change_percent,
                    boost_score=boost,
                )
            )
            product.keyword = keyword
            product.boost_score = boost
            product.score = result.score
            product.reasoning = result.reasoning
            product.score_source = result.source
            product.scoring_provider = result.provider
            product.last_scored_at = datetime.now(UTC)
            scored += 1
    logger.info("product_scoring_completed count=%s", scored)
    return {"scored": scored}
