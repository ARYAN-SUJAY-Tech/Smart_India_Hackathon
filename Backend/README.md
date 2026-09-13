# Flash Flood & Landslide Early Warning — Backend

SIH PS 26192.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

The trained model lives at `app/ml/sikkim_landslide_rf_model.pkl` and is
loaded by `app/services/risk_model.py` — it was pickled under
scikit-learn 1.9.1; if your installed version differs you'll get an
`InconsistentVersionWarning` from joblib (harmless for this model's
structure, but worth matching if you see prediction drift).

No `.env` file is required to run the API today — CORS is wide open and
nothing currently reads environment variables. `app/services/smap_client.py`
will need NASA Earthdata credentials once the real AppEEARS flow is
implemented (see "Next steps" below).

## Run

```bash
python seed_data.py           # creates flashflood.db + 3 sample villages
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/docs> for interactive Swagger UI — test every
endpoint from the browser, no frontend needed.

## What's wired up today

- `GET /health` — liveness check
- `GET /villages/` / `GET /villages/{id}` — village metadata + static terrain features
- `POST /sensor/ingest` — the IoT-ready hook; accepts any reading (SMAP, IMD, simulated, or real IoT later)
- `GET /risk/{village_id}` — computed risk score + alert level for one village, using the trained Random Forest (`app/services/risk_model.py`)
- `GET /risk/` — risk for every village in one call; feeds the map view
- `GET /alerts/` — recent alert history log

Both risk endpoints log to `alert_log`, but only on an actual risk-level
**transition** for that village (or its first-ever computation) — not on
every call. Without that guard, a frontend polling `GET /risk/` every few
seconds (or a judge refreshing Swagger UI) would flood the table with
duplicate "still normal" rows and make the alert timeline useless. See
`_log_alert_if_changed` in `app/routers/risk.py`.

## What's a placeholder, on purpose

- `app/services/smap_client.py` — real AppEEARS task flow not yet
  implemented (it's async: submit → poll → download). Use
  `simulate_soil_moisture()`, or just POST to `/sensor/ingest` directly,
  for end-to-end testing until then.
- `Village.aspect_deg` / `Village.curvature` — computed and stored, but
  not consumed by the model (only `elevation`, `slope`, `soil_moisture`
  are, per `risk_model.py`'s `feature_names_in_`). Kept in case a future
  model version uses them.
- `seed_data.py`'s three sample villages have placeholder terrain values.
  Real `elevation_m`/`slope_deg` should come from `dem_processing.py`
  run against the actual hilly-region DEM tile.

## Try it end-to-end right now

```bash
# simulate a sensor/SMAP reading for village 1
curl -X POST http://127.0.0.1:8000/sensor/ingest \
  -H "Content-Type: application/json" \
  -d '{"village_id": 1, "soil_moisture": 0.45, "rainfall_mm": 120, "source": "simulated"}'

# get computed risk for that village (also logs the transition, if any)
curl http://127.0.0.1:8000/risk/1

# see it logged in the alert history
curl http://127.0.0.1:8000/alerts/
```

Or run the frontend in `../frontend` and use its "Simulate Sensor
Reading" tool, which does the same thing through the UI.

## Next steps

1. Run `dem_processing.py` against the real hilly-region DEM tile to
   populate real `elevation_m`/`slope_deg`/`aspect_deg`/`curvature` per
   village, replacing `seed_data.py`'s placeholder values.
2. Implement the real AppEEARS flow in `smap_client.py`, ideally on an
   APScheduler job pushing into `/sensor/ingest` on a schedule.
3. Add `rainfall_mm` as a model feature if/when the ML side retrains
   with it — it's already collected on every `SensorReading` but not
   yet consumed by `predict_risk()`.
4. Point CORS + DB at whatever the real frontend/deployment needs before
   any production claim (SQLite + `allow_origins=["*"]` are fine for a
   hackathon demo only).
