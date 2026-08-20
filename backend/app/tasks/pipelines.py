import logging

from celery import chain

from app.tasks.celery_app import celery_app
from app.tasks.scraping import run_amazon_collection
from app.tasks.trends import run_trend_collection

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.pipelines.run_full_collection_pipeline")
def run_full_collection_pipeline() -> dict[str, str]:
    workflow = chain(
        run_amazon_collection.si(),
        run_trend_collection.si(True),
    ).apply_async()
    logger.info("full_collection_pipeline_enqueued task_id=%s", workflow.id)
    return {"task_id": workflow.id}
