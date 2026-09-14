"""
Restructured from your Bengaluru flood_model_spatial_cv notebook for Sikkim.

Changes from the original:
  1. Single Sikkim.tif DEM instead of merging bng_north/bng_south tiles.
  2. Added a SMAP soil-moisture raster as a feature (reprojected/resampled
     onto the DEM grid, same pattern the original used for CHIRPS).
  3. Rainfall still comes from a folder of daily CHIRPS tifs -- point
     'inputdir' at wherever download_chirps_sikkim.py wrote its output.
  4. Event labels now come from sikkim_landslide_dataset.csv (lat/lon/label
     columns) instead of a KML of flood points -- same rasterize-to-grid-
     index logic, just reading a CSV instead of iterating KML geometries.
  5. Spatial CV zone boundaries recalculated for Sikkim's bbox (was
     hardcoded for Bengaluru's lat/lon in the original).

Install once: pip install rasterio geopandas scikit-learn joblib --break-system-packages
"""

import glob
import os

import joblib
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import reproject, Resampling
from scipy.ndimage import sobel
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import LeaveOneGroupOut

# ---------------------------------------------------------------------------
# 1. DEM + slope (single tile, no merge needed)
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
xmax = xmin + (target_width * x_pixel_size)
ymax = dem_transform[5]
y_pixel_size = dem_transform[4]
ymin = ymax + (target_height * y_pixel_size)

slope_x = sobel(elevation_grid, axis=1)
slope_y = sobel(elevation_grid, axis=0)
slope = np.hypot(slope_x, slope_y)

print(f"Terrain loaded: {target_height}x{target_width}")


def reproject_to_dem_grid(src_path, resampling=Resampling.bilinear):
    """Reproject/resample any raster onto the DEM's exact grid (same pattern
    the original script used inline for each CHIRPS day -- pulled out here
    since we now reuse it for SMAP too)."""
    dst = np.empty((target_height, target_width), dtype=np.float32)
    with rasterio.open(src_path) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dem_transform,
            dst_crs=dem_crs,
            resampling=resampling,
        )
    return dst


# ---------------------------------------------------------------------------
# 2. SMAP soil moisture -- a folder of daily tifs, same structure as CHIRPS,
#    so it's aggregated the same way (mean + max over the period) rather
#    than treated as one static file.
#    NOTE: SMAP's native resolution is ~9-36km vs. this DEM's ~30m, so after
#    resampling you'll see large blocky patches of near-identical soil
#    moisture value across many DEM pixels. That's expected, not a bug --
#    it reflects SMAP's real coarseness, not an error in the reprojection.
# ---------------------------------------------------------------------------
SMAP_DIR = "smap_soil_moisture_sikkim"  # <-- point this at your actual SMAP folder
smap_filepaths = sorted(glob.glob(os.path.join(SMAP_DIR, "*.tif"))) if os.path.isdir(SMAP_DIR) else []

if smap_filepaths:
    sm_sum = np.zeros((target_height, target_width), dtype=np.float32)
    sm_max = np.zeros((target_height, target_width), dtype=np.float32)
    for path in smap_filepaths:
        day_grid = reproject_to_dem_grid(path)
        sm_sum += np.nan_to_num(day_grid)
        sm_max = np.maximum(sm_max, np.nan_to_num(day_grid))
    mean_soil_moisture_grid = sm_sum / len(smap_filepaths)
    max_soil_moisture_grid = sm_max
    print(f"SMAP soil moisture aggregated from {len(smap_filepaths)} daily tifs.")
else:
    mean_soil_moisture_grid = None
    max_soil_moisture_grid = None
    print(f"WARNING: no tifs found in '{SMAP_DIR}' -- soil moisture will be excluded. "
          f"Update SMAP_DIR to your actual folder name.")

# ---------------------------------------------------------------------------
# 3. CHIRPS rainfall -- same accumulation logic as the original, reading
#    from whatever folder download_chirps_sikkim.py produced.
# ---------------------------------------------------------------------------
inputdir = "chirps_precipitation_sikkim"
filepaths = sorted(glob.glob(os.path.join(inputdir, "chirps-v2.0.*.tif")))

if not filepaths:
    raise FileNotFoundError(
        f"No CHIRPS tifs found in '{inputdir}'. Run download_chirps_sikkim.py "
        f"first (adjust its START_DATE/END_DATE to your period of interest)."
    )

max_rain = np.zeros((target_height, target_width), dtype=np.float32)
total_rain = np.zeros((target_height, target_width), dtype=np.float32)

for path in filepaths:
    day_grid = reproject_to_dem_grid(path)
    max_rain = np.maximum(max_rain, day_grid)
    total_rain += day_grid

mean_rain = total_rain / len(filepaths)
print(f"Rainfall accumulated from {len(filepaths)} daily tifs.")

# ---------------------------------------------------------------------------
# 4. Assemble the full-grid feature table
# ---------------------------------------------------------------------------
feature_dict = {
    "elevation": elevation_grid.flatten(),
    "max_rainfall": max_rain.flatten(),
    "mean_rainfall": mean_rain.flatten(),
    "total_rainfall": total_rain.flatten(),
    "slope": slope.flatten(),
}
if mean_soil_moisture_grid is not None:
    feature_dict["mean_soil_moisture"] = mean_soil_moisture_grid.flatten()
    feature_dict["max_soil_moisture"] = max_soil_moisture_grid.flatten()

X_full_grid = pd.DataFrame(feature_dict)
feature_cols = list(feature_dict.keys())
print(f"Active features ({len(feature_cols)}): {feature_cols}")

# ---------------------------------------------------------------------------
# 5. Event labels -- from your point CSV instead of a KML.
#    NOTE: this dataset is landslide points, not flash-flood points. If NDRF
#    wants flash floods specifically, source a flood-specific inventory if
#    one exists; otherwise be explicit in your pitch that you're treating
#    rainfall-triggered landslides and flash floods as related hazards
#    sharing the same terrain+rainfall+soil-moisture drivers.
# ---------------------------------------------------------------------------
points_df = pd.read_csv("sikkim_landslide_dataset.csv")

y_full_grid = np.zeros(elevation_grid.size, dtype=np.uint8)
event_indices = []
for lon, lat, label in zip(points_df["longitude"], points_df["latitude"], points_df["label"]):
    if label != 1:
        continue
    col, row = ~dem_transform * (lon, lat)
    row, col = int(np.round(row)), int(np.round(col))
    if 0 <= row < target_height and 0 <= col < target_width:
        event_indices.append((row * target_width) + col)

if not event_indices:
    raise ValueError("No valid event points found -- check CSV coordinates against DEM bounds.")

y_full_grid[event_indices] = 1

event_indices = np.where(y_full_grid == 1)[0]
non_event_indices = np.where(y_full_grid == 0)[0]

np.random.seed(50)
sampled_non_event_indices = np.random.choice(
    non_event_indices, size=len(event_indices) * 3, replace=False
)

final_indices = np.concatenate([event_indices, sampled_non_event_indices])

# Drop any rows with NaN in an active feature (e.g. DEM edge/nodata cells) --
# same explicit-handling principle as the landslide train.py, applied here.
X_candidate = X_full_grid.iloc[final_indices]
valid_mask = ~X_candidate[feature_cols].isna().any(axis=1)
n_dropped = (~valid_mask).sum()
if n_dropped:
    print(f"Dropping {n_dropped} sampled point(s) with NaN in an active feature.")
final_indices = final_indices[valid_mask.values]

X_balanced = X_full_grid.iloc[final_indices][feature_cols]
y_balanced = y_full_grid[final_indices]

print(f"Balanced dataset: {len(y_balanced)} points "
      f"({sum(y_balanced==1)} event, {sum(y_balanced==0)} non-event)")

# ---------------------------------------------------------------------------
# 6. Spatial zones -- quadrant thresholds recalculated for Sikkim's bbox
#    (was hardcoded for Bengaluru's lat 13.0/lon 77.55 split in the original)
# ---------------------------------------------------------------------------
rows_idx = final_indices // target_width
cols_idx = final_indices % target_width
lons_pts = xmin + cols_idx * x_pixel_size
lats_pts = ymax + rows_idx * y_pixel_size

LAT_MID = (27.0 + 27.92) / 2   # Sikkim bbox midline
LON_MID = (88.18 + 88.82) / 2


def assign_zone(lat, lon):
    if lat > LAT_MID and lon < LON_MID:
        return 0  # NW
    elif lat > LAT_MID and lon >= LON_MID:
        return 1  # NE
    elif lat <= LAT_MID and lon < LON_MID:
        return 2  # SW
    else:
        return 3  # SE


groups = np.array([assign_zone(lat, lon) for lat, lon in zip(lats_pts, lons_pts)])
print("Points per zone:", np.bincount(groups))

# Class composition check per zone -- same degenerate-fold risk flagged in
# the landslide pipeline applies here too, worth checking before trusting
# any single fold's accuracy.
zone_class_counts = pd.crosstab(groups, y_balanced)
print("Class counts per zone (rows=zone, cols=label):")
print(zone_class_counts)
degenerate_zones = zone_class_counts.index[(zone_class_counts == 0).any(axis=1)].tolist()
if degenerate_zones:
    print(f"WARNING: zone(s) {degenerate_zones} contain only one class -- "
          f"accuracy on that fold won't be meaningful.")

# ---------------------------------------------------------------------------
# 7. Spatial CV + final model (unchanged from the original approach)
# ---------------------------------------------------------------------------
logo = LeaveOneGroupOut()
all_preds = np.zeros(len(y_balanced), dtype=np.uint8)
all_true = np.zeros(len(y_balanced), dtype=np.uint8)
fold_scores = []

for fold, (train_idx, test_idx) in enumerate(logo.split(X_balanced, y_balanced, groups)):
    X_tr, X_te = X_balanced.iloc[train_idx], X_balanced.iloc[test_idx]
    y_tr, y_te = y_balanced[train_idx], y_balanced[test_idx]

    rf = RandomForestClassifier(
        n_estimators=200, max_depth=10, min_samples_leaf=5,
        class_weight="balanced", random_state=50, n_jobs=-1
    )
    rf.fit(X_tr, y_tr)
    y_pred = rf.predict(X_te)

    score = accuracy_score(y_te, y_pred)
    fold_scores.append(score)
    all_preds[test_idx] = y_pred
    all_true[test_idx] = y_te
    print(f"Zone {fold} held out — Accuracy: {score * 100:.2f}%")

print(f"\n================ SPATIAL CV RESULTS ================")
print(f"Mean accuracy: {np.mean(fold_scores) * 100:.2f}%")
print(f"Std deviation: {np.std(fold_scores) * 100:.2f}%")
print(f"\nAggregated classification report:")
print(classification_report(all_true, all_preds))

final_model = RandomForestClassifier(
    n_estimators=200, max_depth=10, min_samples_leaf=5,
    class_weight="balanced", random_state=50, n_jobs=-1
)
final_model.fit(X_balanced, y_balanced)
joblib.dump(final_model, "sikkim_flood_model.pkl")
joblib.dump(feature_cols, "sikkim_flood_model_features.pkl")  # so predict script knows the exact order
print("\nFinal model saved to 'sikkim_flood_model.pkl'")
