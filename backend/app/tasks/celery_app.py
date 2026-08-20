from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "lemonbrothers",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.scraping",
        "app.tasks.trends",
        "app.tasks.scoring",
        "app.tasks.pipelines",
    ],
)
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "full-collection-every-six-hours": {
            "task": "app.tasks.pipelines.run_full_collection_pipeline",
            "schedule": crontab(minute=0, hour="*/6"),
        }
    },
)
