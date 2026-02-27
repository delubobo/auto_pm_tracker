import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from src.api.routes import financials, schedule, tasks
from src.core.config import DEMO_MODE
from src.core.db import Base, engine
from src.mcp_server import mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Auto-seed demo data on startup when AUTO_SEED=true and DB is empty.
    Designed for cloud deployments with ephemeral storage (no persistent volume needed).
    """
    if os.getenv("AUTO_SEED", "false").lower() == "true":
        from src.core.db import SessionLocal
        from src.models.task import Task
        db = SessionLocal()
        try:
            if db.query(Task).count() == 0:
                from src.demo_data import seed_demo_data
                seed_demo_data()
        finally:
            db.close()
    yield


app = FastAPI(
    title="auto_pm_tracker API",
    description=(
        "REST API for construction project management. "
        "Exposes CPM schedule analysis and EVM financial metrics. "
        "MCP server mounted at /mcp for AI assistant integration."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# --- Routers ---
app.include_router(tasks.router)
app.include_router(schedule.router)
app.include_router(financials.router)


# --- Health ---
@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": "1.0.0"}


# --- Admin ---
@app.post("/api/admin/seed-demo", tags=["admin"])
def seed_demo():
    """Seed the database with demo construction project data.
    Only available when DEMO_MODE=true environment variable is set.
    """
    if not DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Seed endpoint is disabled. Set DEMO_MODE=true to enable.",
        )
    from src.demo_data import seed_demo_data

    seed_demo_data()
    return JSONResponse({"message": "Demo project seeded successfully."}, status_code=200)


# --- MCP server (FastMCP / Starlette ASGI) mounted at /mcp ---
app.mount("/mcp", mcp.streamable_http_app())
