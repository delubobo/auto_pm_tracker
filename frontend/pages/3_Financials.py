"""
3_Financials.py — EVM gauge charts, EAC vs. BAC comparison, and metrics table.

Data source:
  GET /api/financials/evm → EVMResponse
    {BAC, EV, PV, AC, CPI, SPI, EAC, CV, SV, health_status, narrative}
"""
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

import api_client

st.set_page_config(
    page_title="Financials | PM Tracker",
    page_icon=":material/attach_money:",
    layout="wide",
)
st.title(":material/attach_money: Financials — Earned Value Management")


@st.cache_data(ttl=30)
def load_evm():
    return api_client.get_evm()


try:
    evm = load_evm()
except Exception as e:
    st.error(f"Failed to load EVM data: {e}")
    st.info("Ensure the FastAPI backend is running: `uvicorn src.api.app:app --reload --port 8001`")
    st.stop()

# --- Health Banner ---
health = evm["health_status"]
if health == "GREEN":
    st.success(f"**{health}** — {evm['narrative']}")
elif health == "YELLOW":
    st.warning(f"**{health}** — {evm['narrative']}")
else:
    st.error(f"**{health}** — {evm['narrative']}")

st.divider()


def _gauge(value: float, title: str, max_val: float = 2.0) -> go.Figure:
    """Render a Plotly gauge indicator for a performance index."""
    if value >= 1.0:
        bar_color = "#22c55e"
    elif value >= 0.9:
        bar_color = "#f59e0b"
    else:
        bar_color = "#ef4444"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=value,
            delta={"reference": 1.0, "valueformat": ".3f"},
            title={"text": title, "font": {"size": 16}},
            number={"valueformat": ".3f"},
            gauge={
                "axis": {"range": [0, max_val], "tickwidth": 1, "tickformat": ".1f"},
                "bar": {"color": bar_color, "thickness": 0.6},
                "bgcolor": "white",
                "steps": [
                    {"range": [0, 0.9], "color": "#fee2e2"},
                    {"range": [0.9, 1.0], "color": "#fef9c3"},
                    {"range": [1.0, max_val], "color": "#dcfce7"},
                ],
                "threshold": {
                    "line": {"color": "#1e293b", "width": 3},
                    "thickness": 0.8,
                    "value": 1.0,
                },
            },
        )
    )
    fig.update_layout(height=300, margin={"t": 70, "b": 10, "l": 30, "r": 30})
    return fig


# --- Gauge Row: CPI and SPI side-by-side ---
st.subheader(":material/speed: Performance Indices")
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(_gauge(evm["CPI"], "Cost Performance Index (CPI)"), use_container_width=True)
    st.caption("CPI >= 1.0: Under budget  |  0.9–1.0: Watch  |  < 0.9: Over budget")

with col2:
    st.plotly_chart(_gauge(evm["SPI"], "Schedule Performance Index (SPI)"), use_container_width=True)
    st.caption("SPI >= 1.0: Ahead of schedule  |  0.9–1.0: Watch  |  < 0.9: Behind schedule")

st.divider()

# --- EAC vs BAC Grouped Bar ---
st.subheader(":material/bar_chart: Budget & Cost Comparison")

fig_bar = go.Figure(
    data=[
        go.Bar(
            name="BAC (Budget)",
            x=["Forecast"],
            y=[evm["BAC"]],
            marker_color="#3b82f6",
            text=[f"${evm['BAC']:,.0f}"],
            textposition="outside",
        ),
        go.Bar(
            name="EAC (Estimate at Completion)",
            x=["Forecast"],
            y=[evm["EAC"]],
            marker_color="#ef4444" if evm["EAC"] > evm["BAC"] else "#22c55e",
            text=[f"${evm['EAC']:,.0f}"],
            textposition="outside",
        ),
        go.Bar(
            name="PV (Planned Value)",
            x=["Actuals"],
            y=[evm["PV"]],
            marker_color="#06b6d4",
            text=[f"${evm['PV']:,.0f}"],
            textposition="outside",
        ),
        go.Bar(
            name="EV (Earned Value)",
            x=["Actuals"],
            y=[evm["EV"]],
            marker_color="#8b5cf6",
            text=[f"${evm['EV']:,.0f}"],
            textposition="outside",
        ),
        go.Bar(
            name="AC (Actual Cost)",
            x=["Actuals"],
            y=[evm["AC"]],
            marker_color="#f59e0b",
            text=[f"${evm['AC']:,.0f}"],
            textposition="outside",
        ),
    ]
)

fig_bar.update_layout(
    barmode="group",
    yaxis_title="USD ($)",
    xaxis_title="",
    height=400,
    uniformtext_minsize=10,
    uniformtext_mode="hide",
    legend={"orientation": "h", "yanchor": "bottom", "y": -0.35, "xanchor": "center", "x": 0.5},
    margin={"t": 30, "b": 80},
)

st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# --- Metrics Summary: 4-column grid ---
st.subheader(":material/table_chart: EVM Metrics Summary")
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("BAC", f"${evm['BAC']:,.2f}")
col_b.metric(
    "EAC",
    f"${evm['EAC']:,.2f}",
    delta=f"${evm['EAC'] - evm['BAC']:+,.2f} vs BAC",
    delta_color="inverse",
)
col_c.metric(
    "Cost Variance (CV)",
    f"${evm['CV']:,.2f}",
    delta=f"${evm['CV']:+,.2f}",
    delta_color="normal",
)
col_d.metric(
    "Schedule Variance (SV)",
    f"${evm['SV']:,.2f}",
    delta=f"${evm['SV']:+,.2f}",
    delta_color="normal",
)

with st.expander("EVM Formula Reference"):
    st.markdown(
        """
| Metric | Formula | Meaning |
|---|---|---|
| **CPI** | EV / AC | Cost efficiency: dollars of value per dollar spent |
| **SPI** | EV / PV | Schedule efficiency: work done vs. work planned |
| **CV** | EV − AC | Positive = under budget |
| **SV** | EV − PV | Positive = ahead of schedule |
| **EAC** | BAC / CPI | Revised forecast of total project cost |
        """
    )
