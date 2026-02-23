from typing import List, Optional

from pydantic import BaseModel


class TaskCPMResult(BaseModel):
    id: int
    name: str
    duration: int
    dependency_id: Optional[int] = None
    es: int
    ef: int
    ls: int
    lf: int
    float: int
    is_critical: bool


class CriticalPathResponse(BaseModel):
    tasks: List[TaskCPMResult]
    project_duration: int
    critical_path_tasks: List[str]
