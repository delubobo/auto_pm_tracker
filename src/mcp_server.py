import json
import sqlite3

from mcp.server.fastmcp import FastMCP

from src.core.config import DB_PATH
from src.cpm import calculate_critical_path
from src.services import calculate_project_evm

mcp = FastMCP("PM_Tracker_Server")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 tools (original)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_critical_path() -> str:
    """
    Fetches the project schedule and identifies the critical path.
    Use this tool when asked about schedule bottlenecks, task floats, or project timelines.
    """
    results = calculate_critical_path()
    if not results:
        return "No schedule data found in the database."
    return json.dumps(results, indent=2)


@mcp.tool()
def get_financial_health() -> str:
    """
    Calculates the Earned Value Management (EVM) metrics for the project.
    Use this tool when asked about project budget, CPI, SPI, or financial health.
    """
    metrics = calculate_project_evm()
    if not metrics:
        return "No financial data available to calculate EVM."
    return json.dumps(metrics, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 tools
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_project_risks() -> str:
    """
    Analyzes the project for schedule and cost risks.
    Flags critical-path tasks (zero float) and EVM indices below threshold as structured
    risk objects with severity, category, task name, risk description, and recommendation.
    Use when asked about risks, concerns, problems, or project health issues.
    """
    results = calculate_critical_path()
    metrics = calculate_project_evm()

    if not results or not metrics:
        return "Insufficient data to analyze risks. Ensure the database is initialized."

    risks: list[dict] = []

    for t in results:
        if t["is_critical"]:
            risks.append({
                "severity": "HIGH",
                "category": "Schedule",
                "task": t["name"],
                "risk": "Zero float — any delay propagates directly to project completion.",
                "recommendation": "Prioritize resource allocation. Monitor daily.",
            })

    cpi = metrics["CPI"]
    if cpi < 0.9:
        risks.append({
            "severity": "HIGH",
            "category": "Cost",
            "task": "Entire Project",
            "risk": (
                f"CPI {cpi:.3f} — project is significantly over budget. "
                f"EAC ${metrics['EAC']:,.2f} vs BAC ${metrics['BAC']:,.2f}."
            ),
            "recommendation": "Identify over-spending tasks. Reduce scope or increase budget.",
        })
    elif cpi < 1.0:
        risks.append({
            "severity": "MEDIUM",
            "category": "Cost",
            "task": "Entire Project",
            "risk": f"CPI {cpi:.3f} — project is slightly over budget.",
            "recommendation": "Monitor cost performance. Consider cost-reduction measures.",
        })

    spi = metrics["SPI"]
    if spi < 0.9:
        risks.append({
            "severity": "HIGH",
            "category": "Schedule",
            "task": "Entire Project",
            "risk": f"SPI {spi:.3f} — project is significantly behind schedule.",
            "recommendation": "Crash schedule or fast-track remaining critical tasks.",
        })
    elif spi < 1.0:
        risks.append({
            "severity": "MEDIUM",
            "category": "Schedule",
            "task": "Entire Project",
            "risk": f"SPI {spi:.3f} — project is slightly behind schedule.",
            "recommendation": "Review schedule. Identify and address delay causes.",
        })

    if not risks:
        return json.dumps({
            "status": "No significant risks detected.",
            "cpi": cpi,
            "spi": spi,
        }, indent=2)

    return json.dumps(risks, indent=2)


@mcp.tool()
def simulate_delay(task_name: str, delay_days: int) -> str:
    """
    Simulates the impact of a delay on a specific task.
    Uses the task's total float to determine whether the delay is absorbed or propagates
    to the project end date. Returns original vs. new project duration.
    Use when asked about 'what if', 'delay', or schedule impact scenarios.

    Args:
        task_name: The exact name of the task to delay (case-insensitive match).
        delay_days: Number of additional days of delay to simulate.
    """
    results = calculate_critical_path()
    if not results:
        return "No schedule data found in the database."

    task = next((t for t in results if t["name"].lower() == task_name.lower()), None)
    if task is None:
        available_tasks = [t["name"] for t in results]
        return json.dumps({
            "error": f"Task '{task_name}' not found.",
            "available_tasks": available_tasks,
        }, indent=2)

    project_duration = max(t["ef"] for t in results)
    float_available = task["float"]

    if float_available >= delay_days:
        days_added = 0
        new_duration = project_duration
        impact = "absorbed"
        summary = (
            f"A {delay_days}-day delay on '{task['name']}' is fully absorbed by "
            f"{float_available} days of float. Project end date is unchanged."
        )
    else:
        days_added = delay_days - float_available
        new_duration = project_duration + days_added
        impact = "propagates"
        summary = (
            f"A {delay_days}-day delay on '{task['name']}' extends the project by "
            f"{days_added} day(s) to {new_duration} total days. "
            f"Only {float_available} days of float were available to absorb the delay."
        )

    return json.dumps({
        "task": task["name"],
        "is_critical": task["is_critical"],
        "delay_days": delay_days,
        "float_available": float_available,
        "original_project_duration": project_duration,
        "new_project_duration": new_duration,
        "days_added_to_project": days_added,
        "impact": impact,
        "summary": summary,
    }, indent=2)


@mcp.tool()
def query_tasks_by_status(status: str) -> str:
    """
    Queries tasks from the database filtered by their status.
    Use when asked 'what is pending', 'what finished', 'what is in progress', or similar.

    Args:
        status: One of 'Completed', 'In Progress', or 'Pending' (case-insensitive).
    """
    status_map = {
        "completed": "Completed",
        "in progress": "In Progress",
        "in-progress": "In Progress",
        "inprogress": "In Progress",
        "pending": "Pending",
    }
    normalized = status_map.get(status.strip().lower())
    if normalized is None:
        return json.dumps({
            "error": f"Invalid status '{status}'. Must be one of: Completed, In Progress, Pending.",
        })

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT id, task_name, status, duration_days, planned_value, actual_cost "
            "FROM tasks WHERE status = ?",
            (normalized,),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        return json.dumps({"error": f"Database error: {e}"})

    return json.dumps({
        "status_filter": normalized,
        "count": len(rows),
        "tasks": rows,
    }, indent=2)


@mcp.tool()
def get_cost_to_complete() -> str:
    """
    Calculates the Estimate to Complete (ETC): how much money is still needed to finish.
    Formula: ETC = EAC - AC.
    Also reports remaining work value (BAC - EV) and a plain-English narrative.
    Use when asked 'how much is left', 'ETC', 'cost to complete', or remaining budget.
    """
    metrics = calculate_project_evm()
    if not metrics:
        return "No financial data available. Ensure the database is initialized."

    eac = metrics["EAC"]
    ac = metrics["AC"]
    bac = metrics["BAC"]
    cpi = metrics["CPI"]
    ev = metrics["EV"]

    etc = eac - ac
    remaining_work_value = bac - ev

    if cpi >= 1.0:
        narrative = (
            f"The project needs ${etc:,.2f} more to complete. "
            f"With a CPI of {cpi:.3f}, cost efficiency is favorable — "
            f"the final cost (EAC ${eac:,.2f}) is expected to stay at or under "
            f"the original budget (BAC ${bac:,.2f})."
        )
    else:
        overrun = eac - bac
        narrative = (
            f"The project needs ${etc:,.2f} more to complete. "
            f"With a CPI of {cpi:.3f}, the project is currently tracking ${overrun:,.2f} "
            f"over the original budget on a forecast basis. "
            f"${remaining_work_value:,.2f} in planned work value remains to be earned."
        )

    return json.dumps({
        "AC": ac,
        "EAC": eac,
        "ETC": etc,
        "BAC": bac,
        "EV": ev,
        "CPI": cpi,
        "remaining_work_value": remaining_work_value,
        "narrative": narrative,
    }, indent=2)


@mcp.tool()
def generate_status_report() -> str:
    """
    Generates a comprehensive project status report combining CPM and EVM data.
    Returns a structured dict with health status, schedule summary, financial metrics,
    performance index interpretations, and a plain-English narrative.
    Use when asked for a 'status report', 'executive summary', or project overview.
    """
    cpm_results = calculate_critical_path()
    metrics = calculate_project_evm()

    if not cpm_results or not metrics:
        return "Insufficient data to generate a status report. Ensure the database is initialized."

    cpi = metrics["CPI"]
    spi = metrics["SPI"]

    if cpi >= 1.0 and spi >= 1.0:
        health = "GREEN"
    elif cpi < 0.9 or spi < 0.9:
        health = "RED"
    else:
        health = "YELLOW"

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

    critical_tasks = [t["name"] for t in cpm_results if t["is_critical"]]
    project_duration = max(t["ef"] for t in cpm_results)

    narrative = (
        f"Health status: {health}. "
        f"CPI {cpi:.3f} ({_cpi_label(cpi)}). "
        f"SPI {spi:.3f} ({_spi_label(spi)}). "
        f"EAC ${metrics['EAC']:,.2f} vs BAC ${metrics['BAC']:,.2f}. "
        f"Critical path: {', '.join(critical_tasks) if critical_tasks else 'not identified'}."
    )

    report = {
        "health_status": health,
        "schedule": {
            "project_duration_days": project_duration,
            "total_tasks": len(cpm_results),
            "critical_task_count": len(critical_tasks),
            "critical_path": critical_tasks,
        },
        "financials": {
            "BAC": metrics["BAC"],
            "PV": metrics["PV"],
            "EV": metrics["EV"],
            "AC": metrics["AC"],
            "EAC": metrics["EAC"],
            "ETC": metrics["EAC"] - metrics["AC"],
            "CPI": cpi,
            "SPI": spi,
            "CV": metrics["CV"],
            "SV": metrics["SV"],
        },
        "performance_summary": {
            "cost_performance": _cpi_label(cpi),
            "schedule_performance": _spi_label(spi),
        },
        "narrative": narrative,
    }

    return json.dumps(report, indent=2)


if __name__ == "__main__":
    mcp.run()
