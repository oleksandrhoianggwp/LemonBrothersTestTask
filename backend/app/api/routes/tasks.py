from celery.result import AsyncResult
from fastapi import APIRouter

from app.api.dependencies import CurrentUser
from app.schemas.task import TaskStatus
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskStatus)
def task_status(task_id: str, _user: CurrentUser) -> TaskStatus:
    task = AsyncResult(task_id, app=celery_app)
    result = task.result if task.successful() and isinstance(task.result, (dict, list, str, int)) else None
    return TaskStatus(task_id=task_id, status=task.status, result=result)
