"""
5_AI_Assistant.py — Automated project analysis tools.

Predefined analysis buttons backed by REST API data:
  1. Risk Analysis      — critical tasks + CPI/SPI flags as structured risk table
  2. Status Report      — executive summary narrative from CPM + EVM
  3. Delay Simulator    — what-if: task delay → project end impact via float calculation

Phase 4 MCP tools (get_project_risks, simulate_delay, generate_status_report, etc.)
are mounted at /mcp and back the same logic server-side.
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

import api_client

st.set_page_config(
    page_title="AI Assistant | PM Tracker",
    page_icon=":material/smart_toy:",
    layout="wide",
)
st.title(":material/smart_toy: AI Project Assistant")
st.caption(
    "Automated analysis powered by the CPM and EVM engine. "
    "Phase 4 MCP tools are mounted at `/mcp` for Claude AI integration."
)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 1. RISK ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
st.subheader(":material/warning: Risk Analysis")
st.markdown(
    "Identifies schedule and cost risks: critical-path tasks with zero float, "
    "and EVM performance indices below threshold."
)

if st.button("Run Risk Analysis", icon=":material/manage_search:", type="primary", key="btn_risk"):
    with st.spinner("Analyzing project risks..."):
        try:
            cpm = api_client.get_critical_path()
            evm = api_client.get_evm()
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            st.stop()

    risks: list[dict] = []

    # --- Schedule risks: critical path tasks ---
    for t in cpm["tasks"]:
        if t["is_critical"]:
            risks.append(
                {
                    "Severity": "HIGH",
                    "Category": "Schedule",
                    "Item": t["name"],
                    "Risk": "Zero float — any delay propagates directly to project completion.",
                    "Recommendation": "Prioritize resource allocation. Monitor daily.",
                }
            )

    # --- Cost risk: CPI ---
    cpi = evm["CPI"]
    if cpi < 0.9:
        risks.append(
            {
                "Severity": "HIGH",
                "Category": "Cost",
                "Item": "Entire Project",
                "Risk": (
                    f"CPI {cpi:.3f} — project is significantly over budget. "
                    f"EAC ${evm['EAC']:,.0f} vs BAC ${evm['BAC']:,.0f} "
                    f"(+${evm['EAC'] - evm['BAC']:,.0f})."
                ),
                "Recommendation": "Identify over-spending tasks. Reduce scope or increase budget.",
            }
        )
    elif cpi < 1.0:
        risks.append(
            {
                "Severity": "MEDIUM",
                "Category": "Cost",
                "Item": "Entire Project",
                "Risk": f"CPI {cpi:.3f} — project is slightly over budget.",
                "Recommendation": "Monitor cost performance. Consider cost-reduction measures.",
            }
        )

    # --- Schedule risk: SPI ---
    spi = evm["SPI"]
    if spi < 0.9:
        risks.append(
            {
                "Severity": "HIGH",
                "Category": "Schedule",
                "Item": "Entire Project",
                "Risk": f"SPI {spi:.3f} — project is significantly behind schedule.",
                "Recommendation": "Crash schedule or fast-track remaining critical tasks.",
            }
        )
    elif spi < 1.0:
        risks.append(
            {
                "Severity": "MEDIUM",
                "Category": "Schedule",
                "Item": "Entire Project",
                "Risk": f"SPI {spi:.3f} — project is slightly behind schedule.",
                "Recommendation": "Review schedule. Identify and address delay causes.",
            }
        )

    if not risks:
        st.success(
            f"No significant risks detected. "
            f"CPI={cpi:.3f}, SPI={spi:.3f} — project is performing on or above plan."
        )
    else:
        risk_df = pd.DataFrame(risks)

        def _color_severity(val: str) -> str:
            if val == "HIGH":
                return "background-color: #fee2e2; color: #991b1b; font-weight: bold"
            if val == "MEDIUM":
                return "background-color: #fef9c3; color: #92400e; font-weight: bold"
            return ""

        st.dataframe(
            risk_df.style.applymap(_color_severity, subset=["Severity"]),
            use_container_width=True,
            hide_index=True,
        )
        high_count = sum(1 for r in risks if r["Severity"] == "HIGH")
        medium_count = sum(1 for r in risks if r["Severity"] == "MEDIUM")
        st.caption(f"Found {high_count} HIGH and {medium_count} MEDIUM risk(s).")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 2. STATUS REPORT
# ─────────────────────────────────────────────────────────────────────────────
st.subheader(":material/article: Status Report")
st.markdown("Generates a structured executive summary combining CPM schedule and EVM financials.")

if st.button("Generate Status Report", icon=":material/summarize:", type="primary", key="btn_report"):
    with st.spinner("Generating report..."):
        try:
            cpm = api_client.get_critical_path()
            evm = api_client.get_evm()
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            st.stop()

    health_label = {"GREEN": "[GREEN]", "YELLOW": "[YELLOW]", "RED": "[RED]"}.get(
        evm["health_status"], evm["health_status"]
    )

    def _cpi_label(v: float) -> str:
        if v >= 1.0:
            return "Under budget"
        if v >= 0.9:
            return "Slightly over budget"
        return "Significantly over budget"

    def _spi_label(v: float) -> str:
        if v >= 1.0:
            return "Ahead of / on schedule"
        if v >= 0.9:
            return "Slightly behind schedule"
        return "Significantly behind schedule"

    report = f"""
## Executive Status Report

**Overall Health:** {health_label}

---

### Schedule Summary
- **Project Duration:** {cpm["project_duration"]} days total
- **Total Tasks:** {len(cpm["tasks"])}
- **Critical Path Tasks ({len(cpm["critical_path_tasks"])}):** {", ".join(cpm["critical_path_tasks"]) or "None identified"}

---

### Financial Summary

| Metric | Value |
|---|---|
| Budget at Completion (BAC) | ${evm["BAC"]:,.2f} |
| Planned Value (PV) | ${evm["PV"]:,.2f} |
| Earned Value (EV) | ${evm["EV"]:,.2f} |
| Actual Cost (AC) | ${evm["AC"]:,.2f} |
| Estimate at Completion (EAC) | ${evm["EAC"]:,.2f} |
| Cost Variance (CV) | ${evm["CV"]:+,.2f} |
| Schedule Variance (SV) | ${evm["SV"]:+,.2f} |

---

### Performance Indices

| Index | Value | Interpretation |
|---|---|---|
| CPI (Cost) | {evm["CPI"]:.3f} | {_cpi_label(evm["CPI"])} |
| SPI (Schedule) | {evm["SPI"]:.3f} | {_spi_label(evm["SPI"])} |

---

### Assessment

{evm["narrative"]}
"""

    st.markdown(report)

    st.download_button(
        label="Download Report (.md)",
        icon=":material/download:",
        data=report,
        file_name="project_status_report.md",
        mime="text/markdown",
    )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 3. DELAY SIMULATOR
# ─────────────────────────────────────────────────────────────────────────────
st.subheader(":material/timer: Delay Simulator")
st.markdown(
    "Simulates the impact of adding delay days to a specific task. "
    "Uses available float to determine if the delay propagates to the project end date."
)

try:
    cpm_data = api_client.get_critical_path()
    task_options = [t["name"] for t in cpm_data["tasks"]]
except Exception as e:
    st.error(f"Error loading schedule data: {e}")
    st.stop()

if not task_options:
    st.info("No tasks found. Initialize the database first.")
else:
    col_task, col_delay = st.columns([3, 1])
    with col_task:
        selected_task = st.selectbox("Select Task to Delay", task_options)
    with col_delay:
        delay_days = st.number_input("Delay (days)", min_value=1, max_value=365, value=5, step=1)

    if st.button("Simulate Delay", icon=":material/play_arrow:", type="primary", key="btn_delay"):
        task_data = next(
            (t for t in cpm_data["tasks"] if t["name"] == selected_task), None
        )

        if task_data is None:
            st.error(f"Task '{selected_task}' not found.")
        else:
            float_available = task_data["float"]
            is_critical = task_data["is_critical"]
            project_duration = cpm_data["project_duration"]

            delay_absorbed = float_available >= delay_days
            if delay_absorbed:
                new_project_duration = project_duration
                days_added = 0
            else:
                days_added = delay_days - float_available
                new_project_duration = project_duration + days_added

            col1, col2, col3 = st.columns(3)
            col1.metric("Float Available", f"{float_available} days")
            col2.metric("Original Duration", f"{project_duration} days")
            col3.metric(
                "New Project Duration",
                f"{new_project_duration} days",
                delta=f"+{days_added} days" if days_added > 0 else "No change",
                delta_color="inverse" if days_added > 0 else "off",
            )

            if delay_absorbed:
                st.success(
                    f"**{delay_days}-day delay on '{selected_task}' is fully absorbed.**  \n"
                    f"Task has {float_available} days of float — project end date unchanged."
                )
            else:
                st.error(
                    f"**{delay_days}-day delay on '{selected_task}' extends the project.**  \n"
                    f"Only {float_available} days of float available. "
                    f"Project extends by **{days_added} day(s)** to **{new_project_duration} total days**."
                )

            if is_critical:
                st.warning(
                    f"'{selected_task}' is on the **critical path** — "
                    "it has zero float and any delay has maximum project impact."
                )
            elif float_available > 0:
                st.info(
                    f"'{selected_task}' has {float_available} days of float. "
                    "It is not on the critical path."
                )
