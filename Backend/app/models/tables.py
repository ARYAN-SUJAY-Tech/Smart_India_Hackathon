"""
Core tables for the prototype.

village          -- ward/village metadata + static terrain features
sensor_reading   -- any real-time input: real IoT later, simulated now,
                    also used to log each SMAP/IMD pull per village
alert_log        -- every risk score + alert level computed, timestamped
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.db.session import Base


class Village(Base):
    __tablename__ = "villages"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True)  # e.g. census/LGD code
    name = Column(String, nullable=False)
    district = Column(String)
    state = Column(String)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # static terrain features, computed once from DEM.
    # IMPORTANT: must be computed from the SAME Sikkim.tif the ML
    # teammate trained on (get his exact file, don't re-source SRTM
    # independently) so values match what the model expects at
    # inference time. Column names carry units for DB clarity; when
    # assembling the feature dict for predict_risk(), map these to
    # the model's bare keys "elevation" / "slope" (see routers/risk.py).
    elevation_m = Column(Float, nullable=True)
    slope_deg = Column(Float, nullable=True)
    aspect_deg = Column(Float, nullable=True)   # not used by ML pipeline yet, kept for later
    curvature = Column(Float, nullable=True)    # not used by ML pipeline yet, kept for later

    sensor_readings = relationship("SensorReading", back_populates="village")
    alerts = relationship("AlertLog", back_populates="village")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    village_id = Column(Integer, ForeignKey("villages.id"), nullable=False)
    source = Column(String, default="simulated")  # "smap" | "imd" | "cwc" | "iot" | "simulated"
    soil_moisture = Column(Float, nullable=True)      # fraction 0-1, SPL3SMP_E resampled onto DEM grid -- matches ML pipeline's "soil_moisture" feature
    rainfall_mm = Column(Float, nullable=True)         # accumulated, from IMD or sensor.
    # NOT currently consumed by the ML model (see risk_model.py note) --
    # kept here so it's ready the moment rainfall is added as a feature,
    # and usable today as an independent alerting escalation rule.
    water_level_m = Column(Float, nullable=True)       # from CWC or sensor, optional
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    village = relationship("Village", back_populates="sensor_readings")


class AlertLog(Base):
    __tablename__ = "alert_log"

    id = Column(Integer, primary_key=True, index=True)
    village_id = Column(Integer, ForeignKey("villages.id"), nullable=False)
    risk_score = Column(Float, nullable=False)      # 0.0 - 1.0
    risk_level = Column(String, nullable=False)      # "normal" | "watch" | "warning" | "severe"
    contributing_factors = Column(String, nullable=True)  # JSON-encoded string for prototype
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    village = relationship("Village", back_populates="alerts")
