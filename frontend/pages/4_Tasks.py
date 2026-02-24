"""
4_Tasks.py — Interactive task CRUD via st.data_editor.

Data source:
  GET    /api/tasks            → list[TaskResponse]
  POST   /api/tasks            → TaskResponse (create)
  PATCH  /api/tasks/{id}       → TaskResponse (update)
  DELETE /api/tasks/{id}       → 204 (delete)

Workflow:
  1. Load tasks from API into a DataFrame.
  2. Render as st.data_editor.
  3. On "Save Changes": diff original vs. edited → PATCH changed rows,
     POST new rows (no ID), DELETE removed rows.
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

import api_client

st.set_page_config(page_title="Tasks | PM Tracker", page_icon="✅", layout="wide")
st.title("✅ Task Management")
st.caption(
    "Edit tasks inline below. Click **Save Changes** to persist edits to the database, "
    "or **Refresh** to reload current data."
)


def _load_tasks() -> pd.DataFrame:
    tasks = api_client.get_tasks()
    if not tasks:
        return pd.DataFrame(
            columns=["id", "task_name", "status", "duration_days", "dependency_id",
                     "planned_value", "actual_cost"]
        )
    return pd.DataFrame(tasks)


# --- Session state init ---
if "tasks_df" not in st.session_state:
    try:
        st.session_state["tasks_df"] = _load_tasks()
    except Exception as e:
        st.error(f"Failed to load tasks: {e}")
        st.stop()

# --- Toolbar ---
col_refresh, col_seed, _ = st.columns([1, 1, 6])
with col_refresh:
    if st.button("🔄 Refresh"):
        try:
            st.session_state["tasks_df"] = _load_tasks()
            st.rerun()
        except Exception as e:
            st.error(f"Refresh failed: {e}")

with col_seed:
    if st.button("🌱 Seed Demo"):
        try:
            result = api_client.seed_demo()
            st.success(result.get("message", "Demo data seeded."))
            st.session_state["tasks_df"] = _load_tasks()
            st.rerun()
        except Exception as e:
            st.error(f"Seed failed: {e}  \nEnsure `DEMO_MODE=true` is set on the server.")

df_original = st.session_state["tasks_df"].copy()

# --- Data Editor ---
edited_df = st.data_editor(
    df_original,
    column_config={
        "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
        "task_name": st.column_config.TextColumn("Task Name", width="large"),
        "status": st.column_config.SelectboxColumn(
            "Status",
            options=["Completed", "In Progress", "Pending"],
            width="medium",
        ),
        "duration_days": st.column_config.NumberColumn(
            "Duration (days)", min_value=1, step=1, width="small"
        ),
        "dependency_id": st.column_config.NumberColumn(
            "Dependency ID", min_value=1, step=1, width="small"
        ),
        "planned_value": st.column_config.NumberColumn(
            "Planned Value ($)", format="$%.2f", min_value=0.0
        ),
        "actual_cost": st.column_config.NumberColumn(
            "Actual Cost ($)", format="$%.2f", min_value=0.0
        ),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="task_editor",
)

st.divider()

# --- Save Changes ---
if st.button("💾 Save Changes", type="primary"):
    errors: list[str] = []
    saved = 0

    original_ids = set(
        df_original["id"].dropna().astype(int).tolist()
        if "id" in df_original.columns else []
    )
    edited_ids = set(
        edited_df["id"].dropna().astype(int).tolist()
        if "id" in edited_df.columns else []
    )

    # --- Deletes: rows present in original but absent in edited ---
    for deleted_id in original_ids - edited_ids:
        try:
            api_client.delete_task(int(deleted_id))
            saved += 1
        except Exception as e:
            errors.append(f"Delete task {deleted_id}: {e}")

    # --- Creates & Updates ---
    for _, row in edited_df.iterrows():
        row_dict = row.to_dict()
        raw_id = row_dict.get("id")

        def _safe_int(v):
            return None if (v is None or (isinstance(v, float) and pd.isna(v))) else int(v)

        def _safe_float(v):
            return 0.0 if (v is None or (isinstance(v, float) and pd.isna(v))) else float(v)

        task_id = _safe_int(raw_id)

        if task_id is None:
            # New row — create
            payload = {
                "task_name": row_dict.get("task_name") or "New Task",
                "status": row_dict.get("status") or "Pending",
                "duration_days": _safe_int(row_dict.get("duration_days")) or 1,
                "dependency_id": _safe_int(row_dict.get("dependency_id")),
                "planned_value": _safe_float(row_dict.get("planned_value")),
                "actual_cost": _safe_float(row_dict.get("actual_cost")),
            }
            try:
                api_client.create_task(payload)
                saved += 1
            except Exception as e:
                errors.append(f"Create task '{payload['task_name']}': {e}")

        elif task_id in original_ids:
            # Existing row — patch only changed fields
            orig_row = df_original[df_original["id"] == task_id].iloc[0]
            changes: dict = {}

            for col in ["task_name", "status"]:
                new_val = row_dict.get(col)
                old_val = orig_row.get(col)
                if new_val != old_val and new_val is not None:
                    changes[col] = new_val

            for col in ["duration_days"]:
                new_val = _safe_int(row_dict.get(col))
                old_val = _safe_int(orig_row.get(col))
                if new_val != old_val and new_val is not None:
                    changes[col] = new_val

            for col in ["planned_value", "actual_cost"]:
                new_val = _safe_float(row_dict.get(col))
                old_val = _safe_float(orig_row.get(col))
                if abs(new_val - old_val) > 0.001:
                    changes[col] = new_val

            new_dep = _safe_int(row_dict.get("dependency_id"))
            old_dep = _safe_int(orig_row.get("dependency_id"))
            if new_dep != old_dep:
                changes["dependency_id"] = new_dep

            if changes:
                try:
                    api_client.update_task(task_id, changes)
                    saved += 1
                except Exception as e:
                    errors.append(f"Update task {task_id}: {e}")

    # --- Report results ---
    if errors:
        for err in errors:
            st.error(err)
    else:
        if saved:
            st.success(f"✅ Saved {saved} change(s) successfully.")
        else:
            st.info("No changes detected.")

    # Reload fresh data
    try:
        st.session_state["tasks_df"] = _load_tasks()
        st.rerun()
    except Exception as e:
        st.warning(f"Could not reload tasks after save: {e}")
