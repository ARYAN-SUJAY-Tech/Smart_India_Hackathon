# Flash Flood & Landslide Early Warning — Backend

SIH PS 26192. FastAPI backend, real trained models wired in from the
ML repo (landslide RF + flood RF), live rainfall from Open-Meteo.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python seed_data.py           # creates flashflood.db + 3 placeholder villages
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for Swagger UI — every endpoint has a
"try it out" button, no curl needed.

## Endpoints

- `GET /health`
- `GET /villages` / `GET /villages/{id}` — village metadata + terrain (elevation, slope)
- `POST /sensor/ingest` — logs a soil-moisture/rainfall reading (simulated, SMAP pull, or real IoT later — same endpoint either way)
- `GET /risk/{village_id}` — runs both models + live rainfall, returns combined risk score + breakdown
- `GET /risk/` — same, for every village (map view)
- `GET /alerts/` — risk history log

## Try it

```bash
curl -X POST http://127.0.0.1:8000/sensor/ingest \
  -H "Content-Type: application/json" \
  -d '{"village_id": 1, "soil_moisture": 0.38, "source": "simulated"}'

curl http://127.0.0.1:8000/risk/1

curl http://127.0.0.1:8000/alerts/
```

`GET /risk/1` is the one worth watching — it pulls elevation/slope from
the DB, soil moisture from whatever was last ingested, and rainfall
live from Open-Meteo, then runs both models.

## How risk is computed

Two separate trained models from the ML repo, both loaded in
`app/services/risk_model.py`:

- `sikkim_landslide_rf_model.pkl` — elevation, slope, soil_moisture → landslide probability
- `sikkim_flood_model.pkl` — elevation, slope, rainfall (total/mean/max), soil_moisture (mean/max) → flood probability

`risk_score` = max of the two, since a village should get flagged if
either hazard is elevated. Both scores are still broken out separately
in `contributing_factors` so nothing's hidden.

Rainfall comes from `app/services/rainfall_client.py` (Open-Meteo,
no API key). If that call fails, it falls back to zero rainfall rather
than crashing the endpoint — logs a warning, doesn't 500.

## Seed data — what it's actually for

`seed_data.py` just inserts 3 placeholder villages with made-up
lat/lon/elevation/slope so there's *something* in the DB to hit
`/risk/{id}` against. It's not real Sikkim data. Once real village
boundaries + his `Sikkim.tif` are used to populate the villages table
properly (via `dem_processing.py`), this script becomes unnecessary —
delete it or repoint it at the real loader.

## Known gaps

- `soil_moisture` in `/sensor/ingest` is manual/simulated right now.
  The real SMAP AppEEARS pull (`app/services/smap_client.py`) isn't
  implemented yet — it's an async submit/poll/download flow, not a
  single request. Use `simulate_soil_moisture()` until that's built.
- Village terrain (`elevation_m`, `slope_deg`) needs to come from his
  exact `Sikkim.tif`, not an independently downloaded DEM — pixel
  values won't match otherwise.
- CORS is wide open (`allow_origins=["*"]`) — fine for the demo, tighten
  before this goes anywhere real.