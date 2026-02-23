import sqlite3
from src.core.config import DB_PATH

def calculate_project_evm():
    """Calculates Earned Value Management metrics for the entire project."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, planned_value, actual_cost, percent_complete FROM tasks"
        )
        tasks = cursor.fetchall()

    if not tasks:
        return None

    bac = 0.0  # Budget at Completion
    pv = 0.0   # Planned Value
    ev = 0.0   # Earned Value
    ac = 0.0   # Actual Cost

    for status, planned_val, actual_cost, pct_complete in tasks:
        # Safely handle potential empty database fields
        p_val = planned_val or 0.0
        a_cost = actual_cost or 0.0

        bac += p_val
        ac += a_cost

        if status == 'Completed':
            ev += p_val
            pv += p_val
        elif status == 'In Progress':
            # Use per-task percent_complete; fall back to PMBOK 50% rule if NULL.
            pct = pct_complete if pct_complete is not None else 0.5
            ev += (p_val * pct)
            pv += p_val  # Assumes task was scheduled to be completed by current date
            
    # Calculate Performance Indices
    cpi = ev / ac if ac > 0 else 1.0
    spi = ev / pv if pv > 0 else 1.0
    
    # Calculate Estimate at Completion (EAC)
    eac = bac / cpi if cpi > 0 else bac
    
    # Calculate Variances
    cv = ev - ac  # Cost Variance
    sv = ev - pv  # Schedule Variance

    return {
        "BAC": round(bac, 2),
        "EV": round(ev, 2),
        "PV": round(pv, 2),
        "AC": round(ac, 2),
        "CPI": round(cpi, 2),
        "SPI": round(spi, 2),
        "EAC": round(eac, 2),
        "CV": round(cv, 2),
        "SV": round(sv, 2)
    }