from pydantic import BaseModel


class EVMResponse(BaseModel):
    BAC: float
    EV: float
    PV: float
    AC: float
    CPI: float
    SPI: float
    EAC: float
    CV: float
    SV: float
    health_status: str
    narrative: str
