"""
app.py — Streamlit entry point / Home page.

Run from project root:
    streamlit run frontend/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

import api_client

st.set_page_config(
    page_title="PM Tracker",
    page_icon=":material/construction:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title(":material/construction: Construction Project Manager")
st.markdown(
    """
    Welcome to the **auto_pm_tracker** web dashboard — a full-stack project management tool
    for construction engineering teams.

    Use the sidebar to navigate:

    | Page | Description |
    |---|---|
    | **Dashboard** | KPI summary, health status, and critical path overview |
    | **Schedule** | Interactive Gantt chart with critical path highlighted in red |
    | **Financials** | EVM gauge charts for CPI/SPI with EAC vs. BAC comparison |
    | **Tasks** | Edit tasks directly in an interactive spreadsheet |
    | **AI Assistant** | Automated project analysis: risks, status report, delay simulation |
    """
)

st.divider()

col1, col2 = st.columns([1, 3])

with col1:
    st.subheader(":material/sensors: API Status")
    try:
        health = api_client.get_health()
        st.success(f"Connected — v{health.get('version', 'unknown')}")
    except Exception as e:
        st.error(f"API offline  \n`{e}`")
        st.info(
            "Start the backend:\n"
            "```bash\nuvicorn src.api.app:app --reload --port 8001\n```"
        )

with col2:
    st.subheader(":material/terminal: Quick Start")
    st.code(
        "# Terminal 1 — start API\n"
        "uvicorn src.api.app:app --reload --port 8001\n\n"
        "# Terminal 2 — start dashboard\n"
        "streamlit run frontend/app.py",
        language="bash",
    )
