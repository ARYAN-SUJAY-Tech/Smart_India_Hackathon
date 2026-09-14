# Flash Flood & Landslide Early Warning — Backend Prototype

SIH PS 26192. Independent backend build — no ML model or frontend
required to run and test everything below.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # fill in NASA Earthdata creds when ready
```

## Run

```bash
python seed_data.py           # creates flashflood.db + 3 sample villages
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive Swagger UI — test every
endpoint from the browser, no frontend needed.

## What's wired up today

- `GET /health` — liveness check
- `GET /villages` / `GET /villages/{id}` — village metadata + static terrain features
- `POST /sensor/ingest` — the IoT-ready hook; accepts any reading (SMAP, IMD, simulated, or real IoT later)
- `GET /risk/{village_id}` — computed risk score + alert level for one village (uses stub model)
- `GET /risk/` — risk for all villages, feeds the map view later
- `GET /alerts/` — recent alert history log

## What's a placeholder, on purpose

- `app/services/risk_model.py` — `predict_risk()` is a heuristic stub.
  Swap the function body with the trained Random Forest. Nothing else
  in the backend needs to change — routers only ever call this function.
- `app/models/schemas.py` — `RiskOut` field names are placeholders.
  Lock these with the ML teammate today, then update here.
- `app/services/smap_client.py` — real AppEEARS task flow not yet
  implemented (it's async: submit → poll → download). Use
  `simulate_soil_moisture()` for end-to-end testing until then.

## Try it end-to-end right now

```bash
# simulate a sensor/SMAP reading for village 1
curl -X POST http://127.0.0.1:8000/sensor/ingest \
  -H "Content-Type: application/json" \
  -d '{"village_id": 1, "soil_moisture": 0.55, "rainfall_mm": 120, "source": "simulated"}'

# get computed risk for that village
curl http://127.0.0.1:8000/risk/1

# see it logged in the alert history
curl http://127.0.0.1:8000/alerts/
```

## Next steps (once ML/frontend contracts are locked)

1. Replace `predict_risk()` with the trained model call
2. Finalize `RiskOut` / feature-dict field names in `schemas.py` and `risk_model.py`
3. Run `dem_processing.py` against your real hilly-region DEM tile to populate real `elevation_m`/`slope_deg` per village (replace `seed_data.py` values)
4. Implement the real AppEEARS flow in `smap_client.py`, on an APScheduler job pushing into `/sensor/ingest`
5. Point CORS + DB at whatever the frontend/deployment needs
