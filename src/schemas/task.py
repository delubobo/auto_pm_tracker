from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TaskStatus(str, Enum):
    completed = "Completed"
    in_progress = "In Progress"
    pending = "Pending"


class TaskBase(BaseModel):
    task_name: str
    status: TaskStatus
    duration_days: int
    dependency_id: Optional[int] = None
    planned_value: float = 0.0
    actual_cost: float = 0.0


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    task_name: Optional[str] = None
    status: Optional[TaskStatus] = None
    duration_days: Optional[int] = None
    dependency_id: Optional[int] = None
    planned_value: Optional[float] = None
    actual_cost: Optional[float] = None


class TaskResponse(TaskBase):
    id: int

    model_config = {"from_attributes": True}
