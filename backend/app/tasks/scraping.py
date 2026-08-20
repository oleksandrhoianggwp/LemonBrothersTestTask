import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.product import Product
from app.services.amazon.scraper import scrape_amazon_bestsellers
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.scraping.run_amazon_collection")
def run_amazon_collection() -> dict[str, int]:
    settings = get_settings()
    logger.info("amazon_collection_started")
    scraped = asyncio.run(
        scrape_amazon_bestsellers(
            settings.amazon_bestsellers_url,
            max_products=settings.amazon_max_products,
        )
    )
    now = datetime.now(UTC)
    created = 0
    updated = 0
    with SessionLocal.begin() as db:
        for item in scraped:
            product = None
            if item.asin:
                product = db.scalar(select(Product).where(Product.asin == item.asin))
            if product is None:
                product = db.scalar(select(Product).where(Product.product_url == item.product_url))
            if product is None:
                product = Product(
                    asin=item.asin,
                    title=item.title,
                    category=item.category,
                    price=item.price,
                    rating=item.rating,
                    reviews_count=item.reviews_count,
                    product_url=item.product_url,
                    image_url=item.image_url,
                    last_scraped_at=now,
                )
                db.add(product)
                created += 1
            else:
                product.title = item.title
                product.category = item.category
                product.price = item.price
                product.rating = item.rating
                product.reviews_count = item.reviews_count
                product.image_url = item.image_url
                product.last_scraped_at = now
                updated += 1
    logger.info(
        "amazon_collection_completed scraped=%s created=%s updated=%s",
        len(scraped),
        created,
        updated,
    )
    return {"scraped": len(scraped), "created": created, "updated": updated}
