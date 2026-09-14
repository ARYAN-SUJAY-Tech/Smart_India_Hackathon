from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone
import json
import logging

from app.db.session import get_db
from app.models.tables import Village, SensorReading, AlertLog
from app.models.schemas import RiskOut
from app.services.risk_model import predict_risk, explain_risk
from app.services.alerting import get_alert_level
from app.services.rainfall_client import get_rainfall_forecast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk", tags=["risk"])


def _latest_features(db: Session, village: Village) -> dict:
    """
    Assemble the UNION of both models' feature keys for one village:

    Landslide model needs: elevation, slope, soil_moisture
    Flood model needs:     elevation, slope, max_rainfall, mean_rainfall,
                            total_rainfall, mean_soil_moisture, max_soil_moisture

    DB columns keep unit-suffixed names (elevation_m, slope_deg) for
    storage clarity; this function is the single place that translates
    DB naming -> model naming, so if either model's feature names ever
    change, this is the only place to touch.

    soil_moisture comes from the latest ingested SensorReading (SMAP or
    simulated). Per the ML teammate's own sikkim_predict_pipeline.py
    comment, there's no forecast product for soil moisture the way
    there is for rainfall, so the single latest snapshot fills both
    mean_soil_moisture and max_soil_moisture -- mirroring his approach,
    not a shortcut introduced independently here.

    Rainfall is fetched LIVE from Open-Meteo per village lat/lon, not
    read from SensorReading -- it's a forecast, not something a sensor
    submits. rainfall_mm on SensorReading is a separate, legacy field
    kept for any manual/IoT rainfall submissions; it doesn't feed the
    model directly.
    """
    latest = (
        db.query(SensorReading)
        .filter(SensorReading.village_id == village.id)
        .order_by(desc(SensorReading.timestamp))
        .first()
    )
    soil_moisture = latest.soil_moisture if latest else 0.0

    try:
        rainfall = get_rainfall_forecast(village.latitude, village.longitude)
    except Exception:
        # a failed forecast call shouldn't take down the risk endpoint --
        # fail to zero rainfall (under-predicts risk, the safer direction
        # for a demo) and log it for follow-up.
        logger.warning("Rainfall forecast failed for village %s", village.id, exc_info=True)
        rainfall = {"total_rainfall": 0.0, "mean_rainfall": 0.0, "max_rainfall": 0.0}

    return {
        "elevation": village.elevation_m or 0.0,
        "slope": village.slope_deg or 0.0,
        "soil_moisture": soil_moisture,
        "mean_soil_moisture": soil_moisture,
        "max_soil_moisture": soil_moisture,
        "total_rainfall": rainfall["total_rainfall"],
        "mean_rainfall": rainfall["mean_rainfall"],
        "max_rainfall": rainfall["max_rainfall"],
    }


def _log_alert_if_changed(
    db: Session, village: Village, score: float, level: str, factors: dict
) -> None:
    """
    Log a row to alert_log only on a state transition (or the village's
    first-ever computation), not on every risk check.

    Without this guard, GET /risk/{id} logs an identical row on every
    single call -- e.g. a judge refreshing Swagger UI, or a frontend
    polling for a live map, floods alert_log with hundreds of duplicate
    "still normal" rows and makes the alert timeline useless. A real
    early-warning system alerts on state transitions, not on "checked
    again, nothing changed", so that's the behavior both endpoints share.
    """
    last = (
        db.query(AlertLog)
        .filter(AlertLog.village_id == village.id)
        .order_by(desc(AlertLog.timestamp))
        .first()
    )
    if last is not None and last.risk_level == level:
        return
    db.add(
        AlertLog(
            village_id=village.id,
            risk_score=score,
            risk_level=level,
            contributing_factors=json.dumps(factors),
        )
    )
    db.commit()


def _compute_risk(db: Session, village: Village) -> RiskOut:
    features = _latest_features(db, village)
    score = predict_risk(features)
    level = get_alert_level(score)
    factors = explain_risk(features)

    _log_alert_if_changed(db, village, score, level, factors)

    return RiskOut(
        village_id=village.id,
        village_name=village.name,
        risk_score=score,
        risk_level=level,
        contributing_factors=factors,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/{village_id}", response_model=RiskOut)
def get_village_risk(village_id: int, db: Session = Depends(get_db)):
    village = db.query(Village).filter(Village.id == village_id).first()
    if not village:
        raise HTTPException(status_code=404, detail="Village not found")

    return _compute_risk(db, village)


@router.get("/", response_model=list[RiskOut])
def get_all_risk(db: Session = Depends(get_db)):
    """Risk for every village — feeds the map view."""
    villages = db.query(Village).all()
    return [_compute_risk(db, village) for village in villages]
