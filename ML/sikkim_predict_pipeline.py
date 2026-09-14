"""
Restructured from your Bengaluru predict_pipeline notebook for Sikkim.

Key changes:
  1. Single Sikkim.tif DEM (no merge).
  2. Rainfall forecast now sampled at a grid of points across Sikkim and
     interpolated, instead of one scalar for the whole domain. In flat
     Bengaluru a single city-center forecast was a reasonable approximation;
     in mountainous Sikkim rainfall varies sharply with elevation and
     location, so broadcasting one number across the whole raster would
     hide exactly the hyper-local variation the problem statement asks for.
  3. Soil moisture included as a feature at predict time too (must match
     whatever features sikkim_flood_train.py was trained on).
  4. Village/ward-level reverse geocoding kept and repointed at Sikkim's
     bbox -- this directly produces the village/ward-level alert output the
     problem statement asks for.

Install once: pip install rasterio scipy geopy requests joblib --break-system-packages
"""

import glob
import os
import time

import joblib
import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.warp import reproject, Resampling
from scipy.interpolate import griddata
from scipy.ndimage import sobel
import matplotlib.pyplot as plt

SIKKIM_BBOX = {"west": 88.18, "south": 27.0, "east": 88.82, "north": 27.92}

# ---------------------------------------------------------------------------
# 1. DEM + slope
# ---------------------------------------------------------------------------
with rasterio.open("Sikkim.tif") as src:
    elevation_grid = src.read(1).astype(np.float32)
    dem_transform = src.transform
    dem_crs = src.crs
    target_height, target_width = elevation_grid.shape
    if src.nodata is not None:
        elevation_grid[elevation_grid == src.nodata] = np.nan

xmin = dem_transform[2]
x_pixel_size = dem_transform[0]
ymax = dem_transform[5]
y_pixel_size = dem_transform[4]

slope_x = sobel(elevation_grid, axis=1)
slope_y = sobel(elevation_grid, axis=0)
slope = np.hypot(slope_x, slope_y)
print(f"Terrain loaded: {target_height}x{target_width}")


def reproject_to_dem_grid(src_path, resampling=Resampling.bilinear):
    dst = np.empty((target_height, target_width), dtype=np.float32)
    with rasterio.open(src_path) as src:
        reproject(
            source=rasterio.band(src, 1), destination=dst,
            src_transform=src.transform, src_crs=src.crs,
            dst_transform=dem_transform, dst_crs=dem_crs,
            resampling=resampling,
        )
    return dst


# SMAP: use the most recent day in your folder as the "current" antecedent
# soil moisture snapshot. This is a simplification -- there's no way to
# forecast future soil moisture the way rainfall has a forecast API, so the
# best available proxy for "conditions right now" is the latest observed
# SMAP granule. In a real deployment this should be refreshed as new SMAP
# passes come in (roughly every 2-3 days), not a static file.
SMAP_DIR = "smap_soil_moisture_sikkim"
smap_filepaths = sorted(glob.glob(os.path.join(SMAP_DIR, "*.tif"))) if os.path.isdir(SMAP_DIR) else []
if smap_filepaths:
    latest_soil_moisture_grid = reproject_to_dem_grid(smap_filepaths[-1])
    print(f"Using most recent SMAP file as current soil moisture: {smap_filepaths[-1]}")
else:
    latest_soil_moisture_grid = None
    print(f"WARNING: no tifs found in '{SMAP_DIR}' -- omitting soil moisture "
          f"(must match what the model was trained with, or predict will fail).")

# ---------------------------------------------------------------------------
# 2. Model
# ---------------------------------------------------------------------------
rf_model = joblib.load("sikkim_flood_model.pkl")
feature_cols = joblib.load("sikkim_flood_model_features.pkl")
print(f"Model loaded. Expected features: {feature_cols}")

# ---------------------------------------------------------------------------
# 3. Multi-point rainfall forecast, interpolated across the full grid.
#    Open-Meteo supports batched requests via comma-separated lat/lon lists.
# ---------------------------------------------------------------------------
def get_sikkim_forecast_grid(n_per_side=4):
    lats = np.linspace(SIKKIM_BBOX["south"], SIKKIM_BBOX["north"], n_per_side)
    lons = np.linspace(SIKKIM_BBOX["west"], SIKKIM_BBOX["east"], n_per_side)
    sample_lats, sample_lons = np.meshgrid(lats, lons)
    sample_lats, sample_lons = sample_lats.flatten(), sample_lons.flatten()

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": ",".join(map(str, sample_lats)),
        "longitude": ",".join(map(str, sample_lons)),
        "daily": "precipitation_sum",
        "timezone": "Asia/Kolkata",
        "forecast_days": 3,
    }
    resp = requests.get(url, params=params, timeout=30).json()
    # Batched requests return a list of per-location dicts; a single-point
    # request returns one dict directly -- normalize to a list either way.
    locations = resp if isinstance(resp, list) else [resp]

    totals, maxes, means = [], [], []
    for loc in locations:
        daily_rain = loc["daily"]["precipitation_sum"]
        totals.append(sum(daily_rain))
        maxes.append(max(daily_rain))
        means.append(np.mean(daily_rain))

    print(f"===== SAMPLED FORECAST ({len(locations)} points across Sikkim) =====")
    print(f"Total 3-day rainfall range: {min(totals):.1f}-{max(totals):.1f}mm")

    # Interpolate each statistic from the sample points onto the full DEM grid
    col_idx, row_idx = np.meshgrid(np.arange(target_width), np.arange(target_height))
    grid_lons = xmin + col_idx * x_pixel_size
    grid_lats = ymax + row_idx * y_pixel_size

    points = np.column_stack([sample_lons, sample_lats])
    total_grid = griddata(points, totals, (grid_lons, grid_lats), method="linear", fill_value=np.mean(totals))
    max_grid = griddata(points, maxes, (grid_lons, grid_lats), method="linear", fill_value=np.mean(maxes))
    mean_grid = griddata(points, means, (grid_lons, grid_lats), method="linear", fill_value=np.mean(means))

    return total_grid.astype(np.float32), mean_grid.astype(np.float32), max_grid.astype(np.float32)


total_rain, mean_rain, max_rain = get_sikkim_forecast_grid()

# ---------------------------------------------------------------------------
# 4. Build feature grid matching training feature order exactly, predict
# ---------------------------------------------------------------------------
feature_arrays = {
    "elevation": elevation_grid.flatten(),
    "max_rainfall": max_rain.flatten(),
    "mean_rainfall": mean_rain.flatten(),
    "total_rainfall": total_rain.flatten(),
    "slope": slope.flatten(),
}
if latest_soil_moisture_grid is not None:
    # Same snapshot fills both slots -- we only have one "current" observation,
    # not a mean/max over a forecast window the way rainfall has.
    feature_arrays["mean_soil_moisture"] = latest_soil_moisture_grid.flatten()
    feature_arrays["max_soil_moisture"] = latest_soil_moisture_grid.flatten()

forecast_grid = pd.DataFrame({col: feature_arrays[col] for col in feature_cols})
flood_probability = rf_model.predict_proba(forecast_grid)[:, 1]
flood_risk_map = flood_probability.reshape(target_height, target_width)
print("Prediction complete")

plt.figure(figsize=(12, 10))
plt.imshow(flood_risk_map, cmap="RdYlGn_r")
plt.colorbar(label="Flood/landslide-trigger probability")
plt.title("Sikkim hazard risk map — live 3-day forecast")
plt.axis("off")
plt.tight_layout()
plt.savefig("sikkim_risk_forecast.png", dpi=150)
print("Saved sikkim_risk_forecast.png")

# ---------------------------------------------------------------------------
# 5. Village/ward-level output -- reverse geocode high-risk pixels.
#    This is the part that directly satisfies the problem statement's
#    "hyper-local forecasts at the village or ward level" requirement.
# ---------------------------------------------------------------------------
from geopy.geocoders import Nominatim

threshold = 0.20  # recall-biased for hazard warnings, same as original
high_risk_rows, high_risk_cols = np.where(flood_risk_map > threshold)
print(f"High risk pixels: {len(high_risk_rows)}")

high_risk_lons = xmin + high_risk_cols * x_pixel_size
high_risk_lats = ymax + high_risk_rows * y_pixel_size

step = max(1, len(high_risk_rows) // 80)
sampled_lats = high_risk_lats[::step]
sampled_lons = high_risk_lons[::step]

geolocator = Nominatim(user_agent="sikkim_flash_flood_risk")
locations = set()

print("Geocoding... (~2 minutes)")
for i, (lat, lon) in enumerate(zip(sampled_lats, sampled_lons)):
    try:
        loc = geolocator.reverse(f"{lat}, {lon}", language="en", timeout=10)
        if loc:
            addr = loc.raw.get("address", {})
            area = (addr.get("village") or addr.get("hamlet") or addr.get("town")
                    or addr.get("suburb") or addr.get("county", ""))
            if area and area.isascii():
                locations.add(area)
        time.sleep(1)
    except Exception:
        continue
    if i % 10 == 0:
        print(f"  {i}/{len(sampled_lats)} done...")

print(f"\n===== HIGH-RISK VILLAGES/AREAS (threshold={threshold}) =====")
for loc in sorted(locations):
    print(f"  - {loc}")
print(f"\nTotal unique areas: {len(locations)}")
