"""
18-task residential construction demo project.

BAC: $280,000
Parallel paths: roofing + mechanicals run concurrently after framing.
Non-trivial critical path: Site Prep → Excavation → Footings → Foundation
  Walls → Waterproofing → Framing → Roof Sheathing → Roofing → Rough
  Inspections → Insulation → Drywall → Interior Finishes → Punch List →
  Final Inspection (64 days total).
EVM story: foundation phase ran ~11% over budget due to rock and
  material cost increases; project is currently in the parallel trade phase.
"""
import json
import sqlite3

from src.core.config import DB_PATH

# (task_name, status, duration_days, planned_value, actual_cost,
#  predecessor_ids JSON, start_date ISO-8601, percent_complete, task_type)
_TASKS = [
    # ── Phase 1: Site & Foundation ──────────────────────────────────────
    # Foundation ran over budget — the "one phase over budget" EVM story.
    ("Site Preparation",          "Completed",   5, 8_000,  8_500,  "[]",           "2026-01-05", 1.0, "Task"),
    ("Excavation",                "Completed",   3, 12_000, 13_500, "[1]",          "2026-01-10", 1.0, "Task"),
    ("Foundation Footings",       "Completed",   4, 18_000, 20_200, "[2]",          "2026-01-13", 1.0, "Task"),
    ("Foundation Walls",          "Completed",   6, 25_000, 28_000, "[3]",          "2026-01-17", 1.0, "Task"),
    ("Foundation Waterproofing",  "Completed",   2, 7_000,  7_800,  "[4]",          "2026-01-23", 1.0, "Task"),
    # ── Phase 2: Structural Framing ─────────────────────────────────────
    ("Structural Framing",        "Completed",  14, 52_000, 51_000, "[5]",          "2026-01-25", 1.0, "Task"),
    # ── Phase 3A: Roofing (parallel with 3B) ────────────────────────────
    ("Roof Sheathing",            "In Progress", 4, 9_000,  4_000,  "[6]",          "2026-02-08", 0.5, "Task"),
    ("Roofing & Shingles",        "Pending",     5, 16_000, 0,      "[7]",          "2026-02-12", 0.0, "Task"),
    # ── Phase 3B: Rough Mechanicals (parallel with 3A) ──────────────────
    ("Rough Plumbing",            "In Progress", 6, 24_000, 11_000, "[6]",          "2026-02-08", 0.5, "Task"),
    ("Rough HVAC",                "Pending",     5, 20_000, 0,      "[6]",          "2026-02-08", 0.0, "Task"),
    ("Rough Electrical",          "In Progress", 7, 22_000, 10_500, "[6]",          "2026-02-08", 0.5, "Task"),
    # ── Phase 4: Inspections & Interior ─────────────────────────────────
    # Task 12 has 4 predecessors — the key multi-predecessor convergence point.
    ("Rough Inspections",         "Pending",     2, 3_500,  0,      "[8,9,10,11]",  "2026-02-17", 0.0, "Task"),
    ("Insulation",                "Pending",     3, 13_500, 0,      "[12]",         "2026-02-19", 0.0, "Task"),
    ("Drywall",                   "Pending",     8, 21_000, 0,      "[13]",         "2026-02-22", 0.0, "Task"),
    ("Interior Finishes",         "Pending",     5, 15_000, 0,      "[14]",         "2026-03-02", 0.0, "Task"),
    ("Exterior Finishes",         "Pending",     4, 8_000,  0,      "[14]",         "2026-03-02", 0.0, "Task"),
    # Task 17 converges interior + exterior paths.
    ("Punch List",                "Pending",     2, 3_000,  0,      "[15,16]",      "2026-03-07", 0.0, "Task"),
    ("Final Inspection & Handoff","Pending",     1, 3_000,  0,      "[17]",         "2026-03-09", 0.0, "Milestone"),
]


def seed_demo_data() -> None:
    """Replace all tasks with the 18-task residential construction demo."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks")
        cursor.executemany(
            """
            INSERT INTO tasks
                (task_name, status, duration_days, planned_value, actual_cost,
                 predecessor_ids, start_date, percent_complete, task_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _TASKS,
        )
        conn.commit()

    bac = sum(t[3] for t in _TASKS)
    print(f"[OK] Demo project seeded: {len(_TASKS)} tasks, BAC=${bac:,.0f}")
