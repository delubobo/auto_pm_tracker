"""
1_Dashboard.py — KPI summary cards, health banner, and critical path overview.

Data sources:
  GET /api/financials/evm         → EVMResponse
  GET /api/schedule/critical-path → CriticalPathResponse
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

import api_client

st.set_page_config(
    page_title="Dashboard | PM Tracker",
    page_icon=":material/dashboard:",
    layout="wide",
)
st.title(":material/dashboard: Project Dashboard")


@st.cache_data(ttl=30)
def load_data():
    evm = api_client.get_evm()
    cpm = api_client.get_critical_path()
    return evm, cpm


try:
    evm, cpm = load_data()
except Exception as e:
    st.error(f"Failed to load data from API: {e}")
    st.info("Ensure the FastAPI backend is running: `uvicorn src.api.app:app --reload --port 8001`")
    st.stop()

# --- Health Banner ---
health = evm["health_status"]
narrative = evm["narrative"]

if health == "GREEN":
    st.success(f"**{health}** — {narrative}")
elif health == "YELLOW":
    st.warning(f"**{health}** — {narrative}")
else:
    st.error(f"**{health}** — {narrative}")

st.divider()

# --- Financial KPIs: Row 1 ---
st.subheader(":material/payments: Financial Metrics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Budget at Completion (BAC)", f"${evm['BAC']:,.0f}")
col2.metric("Earned Value (EV)", f"${evm['EV']:,.0f}")
col3.metric("Planned Value (PV)", f"${evm['PV']:,.0f}")
col4.metric("Actual Cost (AC)", f"${evm['AC']:,.0f}")

# --- Financial KPIs: Row 2 ---
col5, col6, col7, col8 = st.columns(4)
col5.metric(
    "CPI (Cost Perf. Index)",
    f"{evm['CPI']:.3f}",
    delta=f"{evm['CPI'] - 1.0:+.3f} vs 1.0",
    delta_color="normal",
)
col6.metric(
    "SPI (Schedule Perf. Index)",
    f"{evm['SPI']:.3f}",
    delta=f"{evm['SPI'] - 1.0:+.3f} vs 1.0",
    delta_color="normal",
)
col7.metric(
    "Cost Variance (CV)",
    f"${evm['CV']:,.0f}",
    delta=f"${evm['CV']:+,.0f}",
    delta_color="normal",
)
col8.metric(
    "Schedule Variance (SV)",
    f"${evm['SV']:,.0f}",
    delta=f"${evm['SV']:+,.0f}",
    delta_color="normal",
)

st.divider()

# --- EAC vs BAC + Critical Path count side-by-side ---
col_a, col_b = st.columns(2)
with col_a:
    eac_delta = evm["EAC"] - evm["BAC"]
    col_a.metric(
        "Estimate at Completion (EAC)",
        f"${evm['EAC']:,.0f}",
        delta=f"${eac_delta:+,.0f} vs BAC",
        delta_color="inverse",
    )

with col_b:
    critical_count = len(cpm["critical_path_tasks"])
    total_count = len(cpm["tasks"])
    col_b.metric(
        "Critical Path Tasks",
        f"{critical_count} / {total_count}",
        delta=f"Project: {cpm['project_duration']} days",
        delta_color="off",
    )

st.divider()

# --- Critical Path Summary ---
st.subheader(":material/route: Critical Path")
if cpm["critical_path_tasks"]:
    st.markdown("**Tasks with zero float — any delay extends the project end date:**")
    st.markdown(" → ".join([f"`{t}`" for t in cpm["critical_path_tasks"]]))
else:
    st.info("No critical path data available. Run `pm-tracker init` first.")

# --- Float Detail Table ---
with st.expander("View all task floats"):
    import pandas as pd
    float_df = pd.DataFrame(
        [
            {
                "Task": t["name"],
                "Float (days)": t["float"],
                "Duration": t["duration"],
                "ES": t["es"],
                "EF": t["ef"],
                "Critical": "Yes" if t["is_critical"] else "No",
            }
            for t in cpm["tasks"]
        ]
    )
    st.dataframe(float_df, use_container_width=True, hide_index=True)
