from celery.exceptions import CeleryError
from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser
from app.schemas.task import TaskAccepted
from app.tasks.scraping import run_amazon_collection

router = APIRouter(prefix="/scraping", tags=["scraping"])


@router.post("/amazon", response_model=TaskAccepted, status_code=status.HTTP_202_ACCEPTED)
def enqueue_amazon_collection(_user: CurrentUser) -> TaskAccepted:
    try:
        task = run_amazon_collection.delay()
    except CeleryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task queue is temporarily unavailable",
        ) from exc
    return TaskAccepted(task_id=task.id)
