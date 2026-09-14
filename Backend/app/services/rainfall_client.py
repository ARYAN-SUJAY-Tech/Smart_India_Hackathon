"""
Live rainfall forecast client via Open-Meteo (no API key needed).

Mirrors the ML teammate's sikkim_predict_pipeline.py exactly: he samples
a grid of points across Sikkim and interpolates for the training-time
raster prediction. For per-village serving we don't need a full grid --
each village already has a fixed lat/lon, so we just query that one
point directly. Same API, same fields, no interpolation needed at
serving time.
"""
import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def get_rainfall_forecast(latitude: float, longitude: float, forecast_days: int = 3) -> dict:
    """
    Returns {"total_rainfall": mm, "mean_rainfall": mm, "max_rainfall": mm}
    over the forecast window -- these three keys match the flood model's
    feature names exactly (see sikkim_flood_model_features.pkl).
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "precipitation_sum",
        "timezone": "Asia/Kolkata",
        "forecast_days": forecast_days,
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    daily_rain = data["daily"]["precipitation_sum"]
    # Open-Meteo can return None for a day it has no data for yet -- drop those
    daily_rain = [v for v in daily_rain if v is not None]

    if not daily_rain:
        # fail safe rather than fail loud -- a missing forecast shouldn't
        # crash the risk endpoint. Zero rainfall under-predicts risk,
        # which is the safer direction to fail in for a demo, but this
        # should be logged/monitored in a non-prototype deployment.
        return {"total_rainfall": 0.0, "mean_rainfall": 0.0, "max_rainfall": 0.0}

    return {
        "total_rainfall": round(sum(daily_rain), 2),
        "mean_rainfall": round(sum(daily_rain) / len(daily_rain), 2),
        "max_rainfall": round(max(daily_rain), 2),
    }
