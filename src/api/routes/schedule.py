from fastapi import APIRouter, HTTPException

from src.cpm import calculate_critical_path
from src.schemas.schedule import CriticalPathResponse, TaskCPMResult

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.get("/critical-path", response_model=CriticalPathResponse)
def critical_path():
    results = calculate_critical_path()
    if not results:
        raise HTTPException(status_code=404, detail="No schedule data found. Run init first.")

    tasks = [TaskCPMResult(**r) for r in results]
    project_duration = max(t.ef for t in tasks)
    critical_tasks = [t.name for t in tasks if t.is_critical]

    return CriticalPathResponse(
        tasks=tasks,
        project_duration=project_duration,
        critical_path_tasks=critical_tasks,
    )
