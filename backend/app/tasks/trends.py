import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.product import Product
from app.models.trend import TrendSnapshot
from app.services.trends.keywords import extract_keyword
from app.services.trends.parser import TrendSignal
from app.services.trends.scraper import TrendsRateLimitError, collect_google_trends
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.trends.run_trend_collection")
def run_trend_collection(rescore: bool = True) -> dict[str, int | str | None]:
    logger.info("trend_collection_started")
    with SessionLocal() as db:
        products = list(db.scalars(select(Product).order_by(Product.id)).all())
        product_keywords = {
            product.id: product.keyword or extract_keyword(product.title) for product in products
        }
    unique_keywords = list(dict.fromkeys(product_keywords.values()))
    signals = asyncio.run(collect_google_trends(unique_keywords)) if unique_keywords else {}
    collected = 0
    failed = 0
    rate_limited = 0
    collected_at = datetime.now(UTC)
    with SessionLocal.begin() as db:
        for product_id, keyword in product_keywords.items():
            signal = signals.get(keyword)
            product = db.get(Product, product_id)
            if product is None:
                continue
            product.keyword = keyword
            if not isinstance(signal, TrendSignal):
                failed += 1
                if isinstance(signal, TrendsRateLimitError):
                    rate_limited += 1
                continue
            product.trend_score = signal.trend_score
            product.trend_change_percent = signal.change_percent
            product.last_trend_collected_at = collected_at
            db.add(
                TrendSnapshot(
                    product_id=product.id,
                    keyword=keyword,
                    trend_score=signal.trend_score,
                    change_percent=signal.change_percent,
                    raw_summary=signal.raw_summary,
                    collected_at=collected_at,
                )
            )
            collected += 1
    scoring_task_id = None
    if rescore:
        from app.tasks.scoring import rescore_all_products

        scoring_task_id = rescore_all_products.delay().id
    logger.info(
        "trend_collection_completed collected=%s failed=%s rate_limited=%s",
        collected,
        failed,
        rate_limited,
    )
    return {
        "collected": collected,
        "failed": failed,
        "rate_limited": rate_limited,
        "scoring_task_id": scoring_task_id,
    }
