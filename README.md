# Flash Flood & Landslide Prediction System for Hilly Regions

**Smart India Hackathon — Problem Statement 26192**
*Ministry of Home Affairs · NDRF, DM Division · Theme: Disaster Management*

## The Problem
Hilly states in India are highly vulnerable to landslides and flash floods that strike with very short warning times. Current early warning mechanisms aren't hyper-local or fast enough for timely evacuation. We aim to integrate rainfall, soil moisture, slope stability, historical landslide inventories, and real-time IoT inputs into a system that forecasts risk at the **village/ward level**, with enough lead time to actually act on it.

## Our Solution
We built an end-to-end ML and IoT pipeline that delivers hyper-local risk scores directly to a live dashboard.

| The Ask | What we built |
|---|---|
| Slope stability & terrain | DEM-derived `elevation` and `slope` per village using CartoDEM/SRTM ([`ML/`](ML/README.md), [`Backend/app/services/dem_processing.py`](Backend/app/services/dem_processing.py)) |
| Historical inventories | 210-point labeled Sikkim dataset feeding a Random Forest classifier ([`ML/sikkim_landslide_dataset.csv`](ML/sikkim_landslide_dataset.csv)) |
| Soil moisture | NASA SMAP retrievals for training; simulated point ingestion for live readings in production |
| Rainfall data | Training on NASA CHIRPS daily precipitation; live forecasting via Open-Meteo API integration |
| Real-time IoT inputs | `POST /sensor/ingest` — a single endpoint any hardware sensor or API scraper can push to |
| Hyper-local forecasts | 27 real Sikkim villages seeded. Every village gets its own `risk_score` (0–1) and `risk_level` |
| Actionable early warning | IMD colour-coded scheme (Normal → Watch → Warning → Severe) surfaced on a live Next.js map dashboard ([`frontend/README.md`](frontend/README.md)) |

## Architecture

```text
ML/                        Backend/ (FastAPI)               frontend/ (Next.js)
─────────────────────      ─────────────────────────        ──────────────────────
Sikkim.tif (DEM)      ──►  dem_processing.py           
CHIRPS & SMAP         ──►  Terrain + Sensor data
sikkim_landslide_          saved in SQLite DB
  dataset.csv                         │
       │                              ▼
       ▼                   risk_model.py  ◄── loads sikkim_flood_model.pkl
train.py                        │             (7 features: rain, soil, terrain)
  │ trains &                    ▼
  │ cross-validates       risk.py routers
  ▼ exports .pkl          GET /risk/                 ──►  DataContext polls every 5s
sikkim_flood_             GET /villages/, /alerts/   ──►  Live Map, Village List,
  model.pkl               POST /sensor/ingest        ◄──  Alert Timeline, and Sensor
                          (IoT hook / simulator)          simulator UI
```

The three folders are independent but strictly connected by API contracts and the expected ML features (`elevation, max_rainfall, mean_rainfall, total_rainfall, slope, mean_soil_moisture, max_soil_moisture`).

## Repo Layout

- **[`ML/`](ML/README.md)** — Training data (DEM, SMAP, CHIRPS, labeled inventory) and scripts to train/export the Random Forest model.
- **[`Backend/`](Backend/README.md)** — FastAPI service handling village/terrain data, sensor ingestion, live risk computation via the `.pkl` model, and alert history logging.
- **[`frontend/`](frontend/README.md)** — Next.js dashboard featuring a live interactive map, village risk summaries, alert timelines, and the IoT simulator.

## Running It Locally

You need two terminals to run the backend and frontend simultaneously.

```bash
# 1. Backend (FastAPI + ML)
cd Backend
python -m venv venv
source venv/bin/activate      # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
python seed_sikkim.py         # Seeds DB with 27 real Sikkim villages
uvicorn app.main:app --reload # Runs on http://127.0.0.1:8000

# 2. Frontend (Next.js) - in a new terminal
cd frontend
npm install
npm run dev                   # Runs on http://localhost:3000
```

Open `http://localhost:3000`. Use the "Simulate Sensor Reading" tool to push dummy IoT data to the backend. Watch the map markers change color, risk scores recalculate, and the alert history log update instantly.

## Scope & Limitations

This is a functional prototype designed for SIH, not a production-ready enterprise deployment:

- **Current scope:** The ML model trained on real DEM/SMAP/CHIRPS data, the village-level API contract, the live dashboard UI, and the IoT-ready `/sensor/ingest` hook.
- **Simulated part:** Actual hardware sensors (we use a UI simulator to POST to the real endpoint) and live automated NASA AppEEARS scraping (stubbed out for the demo to avoid API rate limits/timeouts).
