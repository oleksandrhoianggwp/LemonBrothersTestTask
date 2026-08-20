from celery.exceptions import CeleryError
from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser
from app.schemas.task import TaskAccepted
from app.tasks.trends import run_trend_collection

router = APIRouter(prefix="/trends", tags=["trends"])


@router.post("/collect", response_model=TaskAccepted, status_code=status.HTTP_202_ACCEPTED)
def enqueue_trend_collection(_user: CurrentUser) -> TaskAccepted:
    try:
        task = run_trend_collection.delay()
    except CeleryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task queue is temporarily unavailable",
        ) from exc
    return TaskAccepted(task_id=task.id)
