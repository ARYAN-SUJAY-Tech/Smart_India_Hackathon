# Flood Watch — Flash Flood & Landslide Early Warning System

**Smart India Hackathon — Problem Statement 26192**
*Flash Flood Prediction System for Hilly Regions using Multi-Source Data*
Organization: Ministry of Home Affairs · Department: NDRF, DM Division · Theme: Disaster Management

## The problem

Hilly states in India are highly vulnerable to landslides and flash
floods that often strike with very short warning times, and current
early warning mechanisms aren't hyper-local or fast enough for timely
evacuation. The ask: integrate rainfall, soil moisture, slope
stability, historical landslide inventories, and real-time IoT inputs
into a system that forecasts risk at the **village/ward level**, with
enough lead time to actually act on it.

## Our solution, and how it maps to that ask

| Expected Solution asks for... | What we built |
|---|---|
| Slope stability / terrain modelling | DEM-derived `elevation`, `slope`, `aspect`, `curvature` per village ([`ML/`](ML/README.md), [`Backend/app/services/dem_processing.py`](Backend/app/services/dem_processing.py)) |
| Historical landslide inventories | 210-point labeled Sikkim dataset feeding a Random Forest classifier ([`ML/sikkim_landslide_dataset.csv`](ML/sikkim_landslide_dataset.csv)) |
| Soil moisture | NASA SMAP retrievals (2022–2024, `ML/smap_data/`) for training; a single ingestion endpoint for live readings in production |
| Real-time IoT inputs | `POST /sensor/ingest` — one endpoint any sensor, SMAP puller, or IMD feed can push to ([`Backend/README.md`](Backend/README.md)) |
| Hyper-local, village/ward-level forecasts | Every village gets its own `risk_score` (0–1) and `risk_level`, not a regional/state-level number |
| Actionable lead time / early warning | Risk levels use IMD's own colour-coded scheme (Normal → Be Aware → Be Prepared → Take Action), with an alert history log, surfaced on a live map dashboard ([`frontend/README.md`](frontend/README.md)) |
| Rainfall data | **Gap, not yet closed** — collected on every sensor reading but not yet a model input; see [`ML/README.md`](ML/README.md#known-limitations-on-purpose) |

## Architecture

```
ML/                        Backend/                         frontend/
─────────────────────      ─────────────────────────        ──────────────────────
Sikkim.tif (DEM)      ──►  dem_processing.py           
smap_data/ (SMAP)     ──►  (elevation/slope/soil_moisture)
sikkim_landslide_          per village, stored in SQLite
  dataset.csv (labels)                │
       │                              ▼
       ▼                   risk_model.py  ◄── loads sikkim_landslide_rf_model.pkl
train.py                        │
  │ trains, spatially           ▼
  │ cross-validates,      risk.py routers
  ▼ exports .pkl           GET /risk/, /risk/{id}     ──►  DataContext polls every 5s
sikkim_landslide_          GET /villages/, /alerts/    ──►  MapWidget, VillageList,
  rf_model.pkl             POST /sensor/ingest         ◄──  AlertTimeline, Sensor
                            (real IoT hook today,            simulate tool, detail
                             simulated for the demo)         drawer w/ contributing_factors
```

The three folders are independent, connected only by the two contracts
each README documents: the model's `["elevation", "slope",
"soil_moisture"]` feature order (ML ↔ Backend), and the JSON shapes in
`Backend/app/models/schemas.py` (Backend ↔ frontend).

## Repo layout

- **[`ML/`](ML/README.md)** — training data (DEM, SMAP rasters, labeled
  landslide inventory) and the script that trains/exports the Random
  Forest risk model.
- **[`Backend/`](Backend/README.md)** — FastAPI service: village/terrain
  data, sensor ingestion, risk computation via the trained model, and
  alert history logging.
- **[`frontend/`](frontend/README.md)** — Next.js dashboard: live map of
  village risk, an at-a-glance severity summary, alert history, and a
  village detail view with the model's contributing factors.

## Running it end-to-end

```bash
# 1. Backend
cd Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python seed_data.py
uvicorn app.main:app --reload          # http://127.0.0.1:8000

# 2. Frontend (separate terminal)
cd frontend
npm install
npm run dev                            # http://localhost:3000
```

Open the frontend, use its "Simulate Sensor Reading" tool (clearly
marked as a demo stand-in for a real IoT/SMAP feed), and watch the
corresponding village's marker color, risk score, and alert history
update live. Full details, including how to retrain the model, are in
each folder's own README linked above.

## Honest scope

This is a hackathon prototype, not a production deployment:

- **Real:** the DEM/SMAP/historical-inventory-trained Random Forest
  model, the village-level API contract, the live map/alerting UI, and
  the IoT-ready `/sensor/ingest` hook (any real sensor can start
  POSTing to it with no architecture change).
- **Simulated for the demo:** actual hardware sensors (the ingestion
  endpoint accepts simulated readings), the NASA AppEEARS automation
  for pulling live SMAP data (`Backend/app/services/smap_client.py`
  isn't wired to a live feed yet), and the three seeded villages'
  coordinates (placeholder, not real village records).
- **No auth, tests, or CI** — out of scope for the hackathon build; see
  each sub-README's own "next steps" section for what a production
  path would need.
