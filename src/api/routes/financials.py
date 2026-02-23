from fastapi import APIRouter, HTTPException

from src.schemas.financials import EVMResponse
from src.services import calculate_project_evm

router = APIRouter(prefix="/api/financials", tags=["financials"])


def _build_narrative(metrics: dict) -> tuple[str, str]:
    """Derive a plain-English health status and narrative from EVM metrics."""
    cpi = metrics["CPI"]
    spi = metrics["SPI"]

    if cpi >= 1.0 and spi >= 1.0:
        health = "GREEN"
        narrative = (
            f"Project is on track. CPI of {cpi} means every $1 spent returns ${cpi:.2f} of value. "
            f"SPI of {spi} indicates the project is ahead of or on schedule."
        )
    elif cpi < 0.9 or spi < 0.9:
        health = "RED"
        issues = []
        if cpi < 0.9:
            issues.append(f"significantly over budget (CPI {cpi})")
        if spi < 0.9:
            issues.append(f"significantly behind schedule (SPI {spi})")
        narrative = f"Project is {' and '.join(issues)}. Immediate corrective action recommended. EAC of ${metrics['EAC']:,.2f} vs BAC of ${metrics['BAC']:,.2f}."
    else:
        health = "YELLOW"
        issues = []
        if cpi < 1.0:
            issues.append(f"slightly over budget (CPI {cpi})")
        if spi < 1.0:
            issues.append(f"slightly behind schedule (SPI {spi})")
        narrative = f"Project is {' and '.join(issues)}. Monitor closely. EAC of ${metrics['EAC']:,.2f} vs BAC of ${metrics['BAC']:,.2f}."

    return health, narrative


@router.get("/evm", response_model=EVMResponse)
def evm_metrics():
    metrics = calculate_project_evm()
    if not metrics:
        raise HTTPException(status_code=404, detail="No financial data found. Run init first.")

    health_status, narrative = _build_narrative(metrics)
    return EVMResponse(**metrics, health_status=health_status, narrative=narrative)
