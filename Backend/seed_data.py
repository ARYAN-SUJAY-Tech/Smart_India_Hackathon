"""
Seed a handful of sample villages so every endpoint is testable today,
before real boundary/DEM data is wired in.

Run: python seed_data.py
"""
from app.db.session import SessionLocal, Base, engine
from app.models.tables import Village

Base.metadata.create_all(bind=engine)

SAMPLE_VILLAGES = [
    {"external_id": "V001", "name": "Sample Village A", "district": "Sample District",
     "state": "Sample State", "latitude": 30.32, "longitude": 78.03,
     "elevation_m": 1200.0, "slope_deg": 22.5, "aspect_deg": 180.0, "curvature": 0.02},
    {"external_id": "V002", "name": "Sample Village B", "district": "Sample District",
     "state": "Sample State", "latitude": 30.35, "longitude": 78.10,
     "elevation_m": 950.0, "slope_deg": 35.0, "aspect_deg": 90.0, "curvature": -0.01},
    {"external_id": "V003", "name": "Sample Village C", "district": "Sample District",
     "state": "Sample State", "latitude": 30.28, "longitude": 78.07,
     "elevation_m": 1500.0, "slope_deg": 15.0, "aspect_deg": 270.0, "curvature": 0.00},
]


def seed():
    db = SessionLocal()
    try:
        if db.query(Village).count() > 0:
            print("Villages already seeded, skipping.")
            return
        for v in SAMPLE_VILLAGES:
            db.add(Village(**v))
        db.commit()
        print(f"Seeded {len(SAMPLE_VILLAGES)} villages.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
