import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from src.api.routes import financials, schedule, tasks
from src.core.config import DEMO_MODE
from src.core.db import Base, engine
from src.mcp_server import mcp

# Create all ORM-managed tables (no-op if they already exist from database.py init)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="auto_pm_tracker API",
    description=(
        "REST API for construction project management. "
        "Exposes CPM schedule analysis and EVM financial metrics. "
        "MCP server mounted at /mcp for AI assistant integration."
    ),
    version="1.0.0",
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
    from src.database import initialize_db, seed_data

    initialize_db()
    seed_data()
    return JSONResponse({"message": "Demo project seeded successfully."}, status_code=200)


# --- MCP server (FastMCP / Starlette ASGI) mounted at /mcp ---
app.mount("/mcp", mcp.streamable_http_app())
