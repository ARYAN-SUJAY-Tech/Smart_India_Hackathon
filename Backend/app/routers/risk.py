from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone
import json

from app.db.session import get_db
from app.models.tables import Village, SensorReading, AlertLog
from app.models.schemas import RiskOut
from app.services.risk_model import predict_risk, explain_risk
from app.services.alerting import get_alert_level

router = APIRouter(prefix="/risk", tags=["risk"])


def _latest_features(db: Session, village: Village) -> dict:
    """
    Assemble the feature dict for one village from its latest sensor
    reading + static terrain fields.

    Keys are LOCKED to match ML_pipeline.ipynb exactly:
    "elevation", "slope", "soil_moisture" -- bare names, no unit
    suffixes, since that's what predict_risk() (and eventually the
    real Random Forest) expects. DB columns keep unit-suffixed names
    (elevation_m, slope_deg) for clarity in storage; this function is
    the single place that translates DB naming -> model naming, so if
    his feature names ever change, this is the only line to touch.

    rainfall_mm is deliberately NOT included here -- his model doesn't
    consume it yet (see risk_model.py). It's still logged on every
    SensorReading and available for a separate alerting escalation
    rule if we want to use it before it's a model feature.
    """
    latest = (
        db.query(SensorReading)
        .filter(SensorReading.village_id == village.id)
        .order_by(desc(SensorReading.timestamp))
        .first()
    )
    return {
        "elevation": village.elevation_m or 0.0,
        "slope": village.slope_deg or 0.0,
        "soil_moisture": latest.soil_moisture if latest else 0.0,
    }


def _log_alert_if_changed(
    db: Session, village: Village, score: float, level: str, factors: dict
) -> None:
    """
    Log a row to alert_log only on a state transition (or the village's
    first-ever computation), not on every risk check.

    Without this guard, GET /risk/{id} logged an identical row on every
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
