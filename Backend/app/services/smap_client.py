"""
NASA SMAP soil moisture client.

Requires a free NASA Earthdata login: https://urs.earthdata.nasa.gov/
Set credentials as env vars (see .env.example) rather than hardcoding.

SMAP native resolution is ~9km (enhanced L3) or ~36km (L3 standard) —
this is exactly the "coarse satellite pixel" you downscale using DEM
slope in the feature pipeline (see dem_processing.py).

For the prototype, start with AppEEARS (point/area extraction API) —
it's simpler than pulling raw HDF5/NetCDF granules directly.
Docs: https://appeears.earthdatacloud.nasa.gov/api/
"""
import os
import requests

APPEEARS_BASE_URL = "https://appeears.earthdatacloud.nasa.gov/api"
EARTHDATA_USERNAME = os.getenv("EARTHDATA_USERNAME")
EARTHDATA_PASSWORD = os.getenv("EARTHDATA_PASSWORD")


def get_earthdata_token() -> str:
    """Authenticate against AppEEARS and return a bearer token."""
    if not EARTHDATA_USERNAME or not EARTHDATA_PASSWORD:
        raise RuntimeError(
            "Set EARTHDATA_USERNAME / EARTHDATA_PASSWORD env vars "
            "(see .env.example) before calling the SMAP client."
        )
    resp = requests.post(
        f"{APPEEARS_BASE_URL}/login",
        auth=(EARTHDATA_USERNAME, EARTHDATA_PASSWORD),
    )
    resp.raise_for_status()
    return resp.json()["token"]


def fetch_soil_moisture_point(lat: float, lon: float, token: str = None) -> float:
    """
    PLACEHOLDER — point extraction via AppEEARS is task-based (submit,
    poll, download), not a single synchronous call. For today's demo,
    stub this out and return a fixed/simulated value so the rest of
    the pipeline (feature assembly, risk_model, alerting) can be
    tested end-to-end without waiting on a full AppEEARS task cycle.

    TODO once contracts are locked: implement the submit-task /
    poll-status / download-result flow per AppEEARS docs, cache
    results locally (SMAP only updates every 2-3 days), and store
    into SensorReading rows with source="smap".
    """
    raise NotImplementedError(
        "Wire up AppEEARS task flow here. Use simulate_soil_moisture() "
        "for end-to-end testing in the meantime."
    )


def simulate_soil_moisture(lat: float, lon: float) -> float:
    """Demo-only stand-in until the real AppEEARS flow is implemented."""
    import random
    return round(random.uniform(0.1, 0.6), 3)
