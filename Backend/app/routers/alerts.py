from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from app.db.session import get_db
from app.models.tables import AlertLog
from app.models.schemas import AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/", response_model=List[AlertOut])
def list_alerts(limit: int = 50, db: Session = Depends(get_db)):
    """Recent alert history — powers the demo timeline."""
    return (
        db.query(AlertLog)
        .order_by(desc(AlertLog.timestamp))
        .limit(limit)
        .all()
    )
