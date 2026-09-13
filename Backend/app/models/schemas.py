"""
Pydantic schemas = the JSON contract between backend, ML, and frontend.
Placeholder shapes for today — swap field names once you and your
teammate finalize the exact feature list / response shape, but the
rest of the backend (routers, DB, alerting) does not need to change
when you do.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class VillageOut(BaseModel):
    id: int
    external_id: Optional[str]
    name: str
    district: Optional[str]
    state: Optional[str]
    latitude: float
    longitude: float
    elevation_m: Optional[float]
    slope_deg: Optional[float]

    class Config:
        from_attributes = True


class SensorIngestIn(BaseModel):
    """Payload shape for the IoT-ready ingestion endpoint."""
    village_id: int
    soil_moisture: Optional[float] = None
    rainfall_mm: Optional[float] = None
    water_level_m: Optional[float] = None
    source: str = "simulated"  # will become "iot" once real hardware exists
    timestamp: Optional[datetime] = None


class RiskOut(BaseModel):
    """
    Response shape is stable now. contributing_factors currently comes
    back as {"slope": ..., "soil_moisture": ...} to match the ML
    pipeline's actual feature set (elevation/slope/soil_moisture, no
    rainfall yet -- see risk_model.py). Update if he adds rainfall.
    """
    village_id: int
    village_name: str
    risk_score: float          # 0.0 - 1.0
    risk_level: str            # normal | watch | warning | severe
    contributing_factors: dict # e.g. {"slope": 0.3, "soil_moisture": 0.25}
    timestamp: datetime


class AlertOut(BaseModel):
    id: int
    village_id: int
    risk_score: float
    risk_level: str
    timestamp: datetime

    class Config:
        from_attributes = True
