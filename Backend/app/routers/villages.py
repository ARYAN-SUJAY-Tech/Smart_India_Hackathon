from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.tables import Village
from app.models.schemas import VillageOut

router = APIRouter(prefix="/villages", tags=["villages"])


@router.get("/", response_model=List[VillageOut])
def list_villages(db: Session = Depends(get_db)):
    return db.query(Village).all()


@router.get("/{village_id}", response_model=VillageOut)
def get_village(village_id: int, db: Session = Depends(get_db)):
    village = db.query(Village).filter(Village.id == village_id).first()
    if not village:
        raise HTTPException(status_code=404, detail="Village not found")
    return village
