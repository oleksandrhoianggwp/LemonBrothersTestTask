import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.product import Product
from app.models.trend import TrendSnapshot
from app.services.trends.cooldown import (
    activate_rate_limit_cooldown,
    cooldown_remaining_seconds,
)
from app.services.trends.keywords import extract_keyword
from app.services.trends.parser import TrendSignal
from app.services.trends.scraper import TrendsRateLimitError, collect_google_trends
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.trends.run_trend_collection")
def run_trend_collection(rescore: bool = True) -> dict[str, int | str | bool | None]:
    logger.info("trend_collection_started")
    settings = get_settings()
    with SessionLocal() as db:
        products = list(db.scalars(select(Product).order_by(Product.id)).all())
        product_keywords = {
            product.id: product.keyword or extract_keyword(product.title) for product in products
        }
    attempted_at = datetime.now(UTC)
    cooldown_remaining = cooldown_remaining_seconds(settings)
    if cooldown_remaining > 0:
        with SessionLocal.begin() as db:
            for product_id in product_keywords:
                product = db.get(Product, product_id)
                if product is not None:
                    product.last_trend_attempted_at = attempted_at
        affected = len(product_keywords)
        logger.warning(
            "trend_collection_skipped_cooldown affected=%s remaining_seconds=%s",
            affected,
            cooldown_remaining,
        )
        return {
            "collected": 0,
            "failed": affected,
            "rate_limited": affected,
            "cooldown_active": True,
            "cooldown_seconds_remaining": cooldown_remaining,
            "scoring_task_id": None,
        }

    unique_keywords = list(dict.fromkeys(product_keywords.values()))
    signals = asyncio.run(collect_google_trends(unique_keywords)) if unique_keywords else {}
    collected = 0
    failed = 0
    rate_limited = 0
    collected_product_ids: list[int] = []
    with SessionLocal.begin() as db:
        for product_id, keyword in product_keywords.items():
            signal = signals.get(keyword)
            product = db.get(Product, product_id)
            if product is None:
                continue
            product.keyword = keyword
            product.last_trend_attempted_at = attempted_at
            if not isinstance(signal, TrendSignal):
                failed += 1
                if isinstance(signal, TrendsRateLimitError):
                    rate_limited += 1
                continue
            product.trend_score = signal.trend_score
            product.trend_change_percent = signal.change_percent
            product.last_trend_collected_at = attempted_at
            db.add(
                TrendSnapshot(
                    product_id=product.id,
                    keyword=keyword,
                    trend_score=signal.trend_score,
                    change_percent=signal.change_percent,
                    raw_summary=signal.raw_summary,
                    collected_at=attempted_at,
                )
            )
            collected += 1
            collected_product_ids.append(product.id)
    if rate_limited:
        cooldown_remaining = activate_rate_limit_cooldown(settings)
    scoring_task_id = None
    if rescore and collected_product_ids:
        from app.tasks.scoring import rescore_all_products

        scoring_task_id = rescore_all_products.delay(collected_product_ids).id
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
        "cooldown_active": cooldown_remaining > 0,
        "cooldown_seconds_remaining": cooldown_remaining,
        "scoring_task_id": scoring_task_id,
    }
