"""
api_client.py — httpx wrapper for all FastAPI endpoints.

Reads API_BASE_URL from environment (defaults to http://localhost:8001).
All functions raise httpx.HTTPStatusError on non-2xx responses.
"""
import os

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")


def _get(path: str):
    resp = httpx.get(f"{API_BASE_URL}{path}", timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, payload: dict | None = None):
    resp = httpx.post(f"{API_BASE_URL}{path}", json=payload, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def _patch(path: str, payload: dict):
    resp = httpx.patch(f"{API_BASE_URL}{path}", json=payload, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def _delete(path: str) -> None:
    resp = httpx.delete(f"{API_BASE_URL}{path}", timeout=10.0)
    resp.raise_for_status()


# --- Health ---

def get_health() -> dict:
    return _get("/health")


# --- Tasks ---

def get_tasks() -> list:
    return _get("/api/tasks")


def create_task(payload: dict) -> dict:
    return _post("/api/tasks", payload)


def update_task(task_id: int, payload: dict) -> dict:
    return _patch(f"/api/tasks/{task_id}", payload)


def delete_task(task_id: int) -> None:
    _delete(f"/api/tasks/{task_id}")


# --- Schedule ---

def get_critical_path() -> dict:
    """Returns CriticalPathResponse: {tasks, project_duration, critical_path_tasks}"""
    return _get("/api/schedule/critical-path")


# --- Financials ---

def get_evm() -> dict:
    """Returns EVMResponse: {BAC, EV, PV, AC, CPI, SPI, EAC, CV, SV, health_status, narrative}"""
    return _get("/api/financials/evm")


# --- Admin ---

def seed_demo() -> dict:
    """Requires DEMO_MODE=true on the server."""
    return _post("/api/admin/seed-demo")
