import json
import sqlite3
from collections import deque
from typing import Dict, List

from src.core.config import DB_PATH


def calculate_critical_path() -> List[Dict]:
    """Calculates ES, EF, LS, LF, and Float to identify the critical path.

    Uses Kahn's algorithm for topological ordering so the forward pass is
    correct regardless of the order rows are returned from the database.
    Supports multiple predecessors per task via the predecessor_ids JSON column,
    with fallback to the legacy dependency_id integer for existing data.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Fetch both the legacy column and the new JSON column so this works
        # before and after the Phase 2 migration.
        cursor.execute(
            "SELECT id, task_name, duration_days, dependency_id, "
            "predecessor_ids FROM tasks ORDER BY id"
        )
        rows = cursor.fetchall()

    if not rows:
        return []

    # ------------------------------------------------------------------ #
    # Build task_map.  predecessor_ids column is a JSON array of ints;    #
    # fall back to [dependency_id] when the column is missing or empty.   #
    # ------------------------------------------------------------------ #
    task_map: Dict[int, Dict] = {}
    for t_id, name, duration, dep_id, pred_ids_raw in rows:
        try:
            predecessor_ids: List[int] = json.loads(pred_ids_raw or "[]")
        except (json.JSONDecodeError, TypeError):
            predecessor_ids = []

        # Legacy fallback: if JSON is empty but old FK is set, honour it.
        if not predecessor_ids and dep_id:
            predecessor_ids = [dep_id]

        task_map[t_id] = {
            "id": t_id,
            "name": name,
            "duration": duration or 0,
            "predecessor_ids": predecessor_ids,
            "successors": [],
            "es": 0,
            "ef": 0,
            "ls": 0,
            "lf": 0,
            "float": 0,
            "is_critical": False,
        }

    # Build successor lists (used in backward pass).
    for t_id, t_data in task_map.items():
        for pid in t_data["predecessor_ids"]:
            if pid in task_map:
                task_map[pid]["successors"].append(t_id)

    # ------------------------------------------------------------------ #
    # Kahn's algorithm — topological sort                                  #
    # Produces a linear order where every predecessor appears before its  #
    # successor, regardless of DB row insertion order.                     #
    # ------------------------------------------------------------------ #
    in_degree: Dict[int, int] = {t_id: 0 for t_id in task_map}
    for t_id, t_data in task_map.items():
        for pid in t_data["predecessor_ids"]:
            if pid in task_map:
                in_degree[t_id] += 1

    queue: deque = deque(t_id for t_id, deg in in_degree.items() if deg == 0)
    topo_order: List[int] = []

    while queue:
        t_id = queue.popleft()
        topo_order.append(t_id)
        for succ_id in task_map[t_id]["successors"]:
            in_degree[succ_id] -= 1
            if in_degree[succ_id] == 0:
                queue.append(succ_id)

    if len(topo_order) != len(task_map):
        raise ValueError(
            "Cycle detected in task graph — CPM requires a DAG."
        )

    # ------------------------------------------------------------------ #
    # Forward pass (Early Start / Early Finish)                            #
    # ES = max EF of all predecessors; root tasks have ES = 0.            #
    # ------------------------------------------------------------------ #
    for t_id in topo_order:
        t_data = task_map[t_id]
        predecessors = [
            pid for pid in t_data["predecessor_ids"] if pid in task_map
        ]
        if predecessors:
            t_data["es"] = max(task_map[pid]["ef"] for pid in predecessors)
        else:
            t_data["es"] = 0
        t_data["ef"] = t_data["es"] + t_data["duration"]

    project_duration = max(t["ef"] for t in task_map.values())

    # ------------------------------------------------------------------ #
    # Backward pass (Late Finish / Late Start / Total Float)              #
    # Iterate in reverse topological order so successors are resolved     #
    # before predecessors.                                                 #
    # ------------------------------------------------------------------ #
    for t_id in reversed(topo_order):
        t_data = task_map[t_id]
        if not t_data["successors"]:
            t_data["lf"] = project_duration
        else:
            t_data["lf"] = min(
                task_map[succ_id]["ls"] for succ_id in t_data["successors"]
            )
        t_data["ls"] = t_data["lf"] - t_data["duration"]
        t_data["float"] = t_data["ls"] - t_data["es"]
        t_data["is_critical"] = t_data["float"] == 0

    return list(task_map.values())
