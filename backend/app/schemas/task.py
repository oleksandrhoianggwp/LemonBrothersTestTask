from typing import Any

from pydantic import BaseModel


class TaskAccepted(BaseModel):
    task_id: str
    status: str = "PENDING"


class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: Any | None = None
