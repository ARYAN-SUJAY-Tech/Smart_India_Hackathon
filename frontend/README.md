# Flood Watch — Frontend

Frontend for the Flash Flood & Landslide Early Warning System — SIH PS26192.
Next.js (App Router) + TypeScript + Tailwind v4, talking to the FastAPI
backend in `../Backend`.

Hackathon POC scope: no auth, no tests, no CI. Goal is a working
end-to-end loop — map with live risk-colored village markers, a way to
simulate a sensor reading, and an alert history — not a production build.

## Setup

```bash
npm install
cp .env.example .env.local    # only needed if your backend isn't on the default port
```

The backend must be running separately (see `../Backend/README.md`) —
seed it first (`python seed_data.py`) so there are villages to show.

## Run

```bash
npm run dev
```

Open <http://localhost:3000>. By default the app talks to the backend at
`http://127.0.0.1:8000`; override with a `NEXT_PUBLIC_API_URL` env var
(e.g. in `.env.local`) if the backend runs elsewhere.

Other scripts: `npm run build`, `npm run start`, `npm run lint`.

## What's here

- **Map** (`src/components/map/MapWidget.tsx`) — villages plotted as
  color-coded markers (green/yellow/orange/red, matching IMD's own
  colour-coded warning scheme) keyed on `risk_level`.
- **Village list** (`src/components/village/VillageList.tsx`) — all
  villages sorted worst-risk-first, next to the map so triage doesn't
  require scanning map pins.
- **Risk summary bar** (`src/components/dashboard/RiskSummaryBar.tsx`) —
  at-a-glance counts per risk level; click a chip to filter the list/map.
- **Village detail panel** (`src/components/village/VillageDetailPanel.tsx`)
  — risk score, level, and `contributing_factors` breakdown for a
  selected village.
- **Alert history** (`src/components/map/AlertTimeline.tsx`) — recent
  entries from `GET /alerts/`.
- **Simulate Sensor Reading** (`src/components/sensor/SensorIngestForm.tsx`)
  — a clearly-marked demo tool (not a real sensor) that POSTs to
  `/sensor/ingest` so you can watch a village's risk score/color update.
- **`src/context/DataContext.tsx`** — fetches villages once, polls
  `/risk/` and `/alerts/` every 5s, merges into `VillageRisk[]`.
- **`src/lib/types.ts`** — mirrors `Backend/app/models/schemas.py`
  exactly; keep the two in sync if the backend contract changes.
- **`src/lib/riskLevels.ts`** — single source of truth for risk-level
  colors/labels used across the map, list, summary bar, and alerts.

## Notes

- react-leaflet touches `window` at import time, so `MapWidget` is loaded
  via `next/dynamic` with `ssr: false` in the dashboard page.
- `GET /risk/{id}` (used after a sensor submission) also logs to the
  backend's alert history; the bulk `GET /risk/` used for map polling
  does the same but only logs on an actual risk-level transition, not
  every poll — see `Backend/app/routers/risk.py`.
