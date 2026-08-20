from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.product import Product
from app.models.trend import TrendSnapshot
from app.services.trends.parser import TrendSignal
from app.services.trends.scraper import TrendsCollectionError, TrendsRateLimitError
from app.tasks.trends import run_trend_collection


def _product(db: Session, *, asin: str, keyword: str) -> Product:
    product = Product(
        asin=asin,
        title=f"Product {asin}",
        category="Home & Kitchen",
        price=19.99,
        rating=4.5,
        reviews_count=100,
        product_url=f"https://www.amazon.com/dp/{asin}",
        image_url=f"https://images.example/{asin}.jpg",
        keyword=keyword,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _task_session(db: Session) -> sessionmaker:
    return sessionmaker(bind=db.get_bind(), expire_on_commit=False)


def test_rate_limit_preserves_snapshot_marks_stale_and_does_not_rescore(
    db_session: Session,
) -> None:
    product = _product(db_session, asin="B0RATE0001", keyword="neck fan")
    previous = datetime.now(UTC) - timedelta(hours=2)
    product.trend_score = 71
    product.last_trend_collected_at = previous
    product.last_trend_attempted_at = previous
    db_session.add(
        TrendSnapshot(
            product_id=product.id,
            keyword=product.keyword,
            trend_score=71,
            change_percent=8,
            raw_summary={"source": "google_trends_browser"},
            collected_at=previous,
        )
    )
    db_session.commit()

    async def rate_limited(keywords: list[str]) -> dict[str, TrendsRateLimitError]:
        return {keyword: TrendsRateLimitError("HTTP 429") for keyword in keywords}

    with (
        patch("app.tasks.trends.SessionLocal", _task_session(db_session)),
        patch("app.tasks.trends.cooldown_remaining_seconds", return_value=0),
        patch("app.tasks.trends.activate_rate_limit_cooldown", return_value=900),
        patch("app.tasks.trends.collect_google_trends", new=rate_limited),
        patch("app.tasks.scoring.rescore_all_products.delay") as score_delay,
    ):
        result = run_trend_collection.run()

    db_session.expire_all()
    refreshed = db_session.get(Product, product.id)
    assert result == {
        "collected": 0,
        "failed": 1,
        "rate_limited": 1,
        "cooldown_active": True,
        "cooldown_seconds_remaining": 900,
        "scoring_task_id": None,
    }
    assert refreshed is not None
    assert refreshed.trend_score == 71
    assert refreshed.last_trend_collected_at is not None
    assert refreshed.last_trend_collected_at.replace(tzinfo=UTC) == previous
    assert refreshed.last_trend_attempted_at > refreshed.last_trend_collected_at
    assert db_session.scalar(select(func.count()).select_from(TrendSnapshot)) == 1
    score_delay.assert_not_called()


def test_active_cooldown_skips_browser_and_finishes_without_rescore(
    db_session: Session,
) -> None:
    product = _product(db_session, asin="B0COOL0001", keyword="desk fan")
    collect = AsyncMock()
    with (
        patch("app.tasks.trends.SessionLocal", _task_session(db_session)),
        patch("app.tasks.trends.cooldown_remaining_seconds", return_value=321),
        patch("app.tasks.trends.collect_google_trends", collect),
        patch("app.tasks.scoring.rescore_all_products.delay") as score_delay,
    ):
        result = run_trend_collection.run()

    db_session.expire_all()
    refreshed = db_session.get(Product, product.id)
    assert result["cooldown_active"] is True
    assert result["cooldown_seconds_remaining"] == 321
    assert result["rate_limited"] == 1
    assert refreshed is not None and refreshed.last_trend_attempted_at is not None
    collect.assert_not_called()
    score_delay.assert_not_called()


def test_partial_collection_persists_only_real_snapshot_and_rescores_fresh_product(
    db_session: Session,
) -> None:
    fresh = _product(db_session, asin="B0PART0001", keyword="mini blender")
    failed = _product(db_session, asin="B0PART0002", keyword="cooling fan")

    async def partial(keywords: list[str]) -> dict[str, TrendSignal | TrendsCollectionError]:
        assert keywords == ["mini blender", "cooling fan"]
        return {
            "mini blender": TrendSignal(
                trend_score=64,
                change_percent=12.5,
                raw_summary={"source": "google_trends_browser"},
            ),
            "cooling fan": TrendsCollectionError("timeline unavailable"),
        }

    with (
        patch("app.tasks.trends.SessionLocal", _task_session(db_session)),
        patch("app.tasks.trends.cooldown_remaining_seconds", return_value=0),
        patch("app.tasks.trends.collect_google_trends", new=partial),
        patch("app.tasks.scoring.rescore_all_products.delay") as score_delay,
    ):
        score_delay.return_value = SimpleNamespace(id="fresh-score-task")
        result = run_trend_collection.run()

    db_session.expire_all()
    fresh_row = db_session.get(Product, fresh.id)
    failed_row = db_session.get(Product, failed.id)
    assert result["collected"] == 1
    assert result["failed"] == 1
    assert result["rate_limited"] == 0
    assert result["scoring_task_id"] == "fresh-score-task"
    assert fresh_row is not None and fresh_row.last_trend_collected_at is not None
    assert fresh_row.last_trend_attempted_at == fresh_row.last_trend_collected_at
    assert failed_row is not None and failed_row.last_trend_collected_at is None
    assert failed_row.last_trend_attempted_at is not None
    assert db_session.scalar(select(func.count()).select_from(TrendSnapshot)) == 1
    score_delay.assert_called_once_with([fresh.id])
