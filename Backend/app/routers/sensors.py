from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.tables import Village, SensorReading
from app.models.schemas import SensorIngestIn

router = APIRouter(prefix="/sensor", tags=["sensors"])


@router.post("/ingest")
def ingest_reading(payload: SensorIngestIn, db: Session = Depends(get_db)):
    """
    Single ingestion point for ANY reading — SMAP pull, IMD pull,
    a simulated script today, or a real IoT device tomorrow. This is
    what lets the architecture legitimately claim to be IoT-ready:
    a real sensor just needs to POST here, nothing else changes.
    """
    village = db.query(Village).filter(Village.id == payload.village_id).first()
    if not village:
        raise HTTPException(status_code=404, detail="Village not found")

    reading = SensorReading(
        village_id=payload.village_id,
        source=payload.source,
        soil_moisture=payload.soil_moisture,
        rainfall_mm=payload.rainfall_mm,
        water_level_m=payload.water_level_m,
        timestamp=payload.timestamp or None,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return {"status": "ok", "reading_id": reading.id}
