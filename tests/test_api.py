"""Smoke tests for the auto_pm_tracker API.

These tests use FastAPI's synchronous TestClient (no live server needed).
DATABASE_URL and DB_PATH must point to an Alembic-migrated SQLite DB.
DEMO_MODE=true must be set to allow the seed-demo endpoint.
"""
import pytest
from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_tasks_empty():
    """Before seeding, /api/tasks may return an empty list or existing tasks."""
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_task():
    payload = {
        "task_name": "Test Task",
        "status": "Pending",
        "duration_days": 5,
        "planned_value": 1000.0,
        "actual_cost": 0.0,
    }
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["task_name"] == "Test Task"
    assert data["status"] == "Pending"
    assert "id" in data

    # Clean up
    task_id = data["id"]
    client.delete(f"/api/tasks/{task_id}")


def test_get_task_not_found():
    response = client.get("/api/tasks/999999")
    assert response.status_code == 404


def test_seed_and_schedule():
    """Seed the demo project, then verify CPM returns a valid response."""
    seed = client.post("/api/admin/seed-demo")
    assert seed.status_code == 200

    response = client.get("/api/schedule/critical-path")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert "project_duration" in data
    assert "critical_path_tasks" in data
    assert len(data["tasks"]) > 0
    assert data["project_duration"] > 0
    assert len(data["critical_path_tasks"]) > 0


def test_evm_after_seed():
    """EVM metrics should be available after seeding."""
    response = client.get("/api/financials/evm")
    assert response.status_code == 200
    data = response.json()
    for key in ("BAC", "PV", "EV", "AC", "SPI", "CPI", "EAC", "CV", "SV"):
        assert key in data
    assert data["BAC"] > 0
    assert data["health_status"] in ("GREEN", "YELLOW", "RED")
