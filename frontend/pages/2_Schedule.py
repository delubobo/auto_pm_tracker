"""
2_Schedule.py — Interactive Gantt chart with critical path highlighted in red.

Data source:
  GET /api/schedule/critical-path → CriticalPathResponse
    tasks[].{id, name, duration, es, ef, ls, lf, float, is_critical}
    project_duration: int
    critical_path_tasks: list[str]

ES/EF are integer day offsets from project start.
A date picker lets the user anchor the schedule to a real calendar date.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

import api_client

st.set_page_config(
    page_title="Schedule | PM Tracker",
    page_icon=":material/calendar_month:",
    layout="wide",
)
st.title(":material/calendar_month: Project Schedule — Gantt Chart")

# --- Project start date anchor ---
col_date, _ = st.columns([2, 6])
with col_date:
    project_start = st.date_input("Project Start Date", value=date.today())

# --- Fetch CPM data ---
@st.cache_data(ttl=30)
def load_schedule():
    return api_client.get_critical_path()


try:
    cpm = load_schedule()
except Exception as e:
    st.error(f"Failed to load schedule: {e}")
    st.info("Ensure the FastAPI backend is running: `uvicorn src.api.app:app --reload --port 8001`")
    st.stop()

tasks = cpm["tasks"]
if not tasks:
    st.info("No schedule data found. Run `pm-tracker init` or seed demo data.")
    st.stop()

# --- Build DataFrame ---
rows = []
for t in tasks:
    start_dt = project_start + timedelta(days=t["es"])
    end_dt = project_start + timedelta(days=t["ef"])
    rows.append(
        {
            "Task": t["name"],
            "Start": start_dt,
            "Finish": end_dt,
            "Duration (days)": t["duration"],
            "ES": t["es"],
            "EF": t["ef"],
            "LS": t["ls"],
            "LF": t["lf"],
            "Float": t["float"],
            "Critical": t["is_critical"],
            "Status": "Critical" if t["is_critical"] else "Non-Critical",
        }
    )

df = pd.DataFrame(rows)
df = df.sort_values(["ES", "Task"])

# --- Gantt Chart ---
fig = px.timeline(
    df,
    x_start="Start",
    x_end="Finish",
    y="Task",
    color="Status",
    color_discrete_map={"Critical": "#e74c3c", "Non-Critical": "#3498db"},
    hover_data={
        "ES": True,
        "EF": True,
        "Float": True,
        "Duration (days)": True,
        "Start": False,
        "Finish": False,
        "Status": False,
        "Critical": False,
    },
    title=f"Construction Project Schedule  (start: {project_start})",
    height=max(420, len(df) * 36 + 120),
)

fig.update_layout(
    xaxis_title="Date",
    yaxis_title=None,
    legend_title="Path",
    yaxis={"autorange": "reversed"},
    showlegend=True,
    margin={"l": 20, "r": 20, "t": 60, "b": 40},
)
fig.update_traces(marker_line_color="rgba(0,0,0,0.25)", marker_line_width=1)

st.plotly_chart(fig, use_container_width=True)

# --- Summary row ---
st.divider()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Tasks", len(df))
col2.metric("Critical Tasks", int(df["Critical"].sum()))
col3.metric("Non-Critical Tasks", int((~df["Critical"]).sum()))
col4.metric("Project Duration", f"{cpm['project_duration']} days")

# --- Detail Table ---
with st.expander("CPM Detail Table (ES / EF / LS / LF / Float)"):
    display_df = df[
        ["Task", "Start", "Finish", "Duration (days)", "ES", "EF", "LS", "LF", "Float", "Status"]
    ].copy()
    display_df["Start"] = display_df["Start"].astype(str)
    display_df["Finish"] = display_df["Finish"].astype(str)
    st.dataframe(display_df, use_container_width=True, hide_index=True)
