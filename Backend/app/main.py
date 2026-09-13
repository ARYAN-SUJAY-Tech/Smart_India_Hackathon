from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import Base, engine
from app.routers import villages, risk, sensors, alerts

# create tables on startup (fine for SQLite prototype;
# switch to Alembic migrations before any production claim)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hilly Region Flash Flood & Landslide Early Warning API",
    description="Prototype backend — SIH PS 26192",
    version="0.1.0",
)

# open CORS for prototype so the frontend (React/Streamlit) can hit
# this from any origin during the hackathon; restrict before deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(villages.router)
app.include_router(risk.router)
app.include_router(sensors.router)
app.include_router(alerts.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
