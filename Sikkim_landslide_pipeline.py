import os
import re
import glob
import netrc
import random
import requests
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import reproject, Resampling
from scipy import ndimage
import earthaccess


def authenticate_nasa():
    """Authenticate with NASA Earthdata with offline fallback."""
    try:
        auth = earthaccess.login(strategy="netrc")
        print("Authenticated with NASA Earthdata:", auth.authenticated)
        return auth
    except Exception as e:
        print(f"Warning: NASA login timeout ({e}). Proceeding with local rasters.")
        return None


def process_dem(dem_path="Sikkim.tif"):
    """Load DEM raster and calculate terrain slope in degrees."""
    with rasterio.open(dem_path) as dem:
        dem_array = dem.read(1).astype(np.float32)
        dem_transform = dem.transform
        dem_crs = dem.crs
        dem_bounds = dem.bounds
        dem_nodata = dem.nodata

    dem_array = np.where(dem_array == dem_nodata, np.nan, dem_array)

    pixel_size_x = dem_transform[0] * 111320 * np.cos(np.radians(27.5))
    pixel_size_y = abs(dem_transform[4]) * 111320

    dzdx = ndimage.sobel(dem_array, axis=1) / (8 * pixel_size_x)
    dzdy = ndimage.sobel(dem_array, axis=0) / (8 * pixel_size_y)

    slope_rad = np.arctan(np.sqrt(dzdx**2 + dzdy**2))
    slope_deg = np.degrees(slope_rad)

    return dem_array, slope_deg, dem_transform, dem_crs, dem_bounds


def resample_soil_moisture(filepath, dem_array, dem_transform, dem_crs):
    """Resample SMAP raster to match DEM spatial extent and CRS."""
    with rasterio.open(filepath) as sm_src:
        sm_array = sm_src.read(1)
        sm_transform = sm_src.transform
        sm_crs = sm_src.crs
        sm_nodata = sm_src.nodata

    sm_array = np.where(sm_array == sm_nodata, np.nan, sm_array)
    sm_resampled = np.empty(dem_array.shape, dtype=np.float32)

    reproject(
        source=sm_array,
        destination=sm_resampled,
        src_transform=sm_transform,
        src_crs=sm_crs,
        dst_transform=dem_transform,
        dst_crs=dem_crs,
        resampling=Resampling.bilinear
    )
    return sm_resampled


def compute_smap_mean_streaming(local_files, dem_array, dem_transform, dem_crs):
    """Memory-optimized accumulation of multi-year mean soil moisture."""
    running_sum = np.zeros(dem_array.shape, dtype=np.float64)
    running_count = np.zeros(dem_array.shape, dtype=np.int32)
    smap_file_map = {}

    for local_path in local_files:
        filename = os.path.basename(local_path)
        date_match = re.search(r"(\d{8})T000000", filename)
        if not date_match:
            continue
        date_str = date_match.group(1)
        smap_file_map[date_str] = local_path

        sm_arr = resample_soil_moisture(local_path, dem_array, dem_transform, dem_crs)
        valid_mask = ~np.isnan(sm_arr)
        running_sum[valid_mask] += sm_arr[valid_mask]
        running_count[valid_mask] += 1

    smap_mean_map = np.where(running_count > 0, running_sum / running_count, np.nan).astype(np.float32)
    return smap_mean_map, smap_file_map


def load_landslide_inventory(dem_bounds):
    """Load known landslide locations in Sikkim combined with NASA GLC records."""
    manual_landslides = pd.DataFrame([
        {"latitude": 27.6022, "longitude": 88.6463, "date": "20231004", "location": "Chungthang Dam", "label": 1},
        {"latitude": 27.4975, "longitude": 88.5348, "date": "20231004", "location": "Mangan", "label": 1},
        {"latitude": 27.4005, "longitude": 88.5135, "date": "20231004", "location": "Dikchu", "label": 1},
        {"latitude": 27.2341, "longitude": 88.4977, "date": "20231004", "location": "Singtam", "label": 1},
        {"latitude": 27.1751, "longitude": 88.5333, "date": "20231004", "location": "Rangpo", "label": 1},
    ])

    glc_url = "https://data.nasa.gov/docs/legacy/Global_Landslide_Catalog_Export/Global_Landslide_Catalog_Export_rows.csv"
    try:
        df_glc = pd.read_csv(glc_url)
        sikkim_glc = df_glc[
            (df_glc["latitude"] >= dem_bounds.bottom) & (df_glc["latitude"] <= dem_bounds.top) &
            (df_glc["longitude"] >= dem_bounds.left) & (df_glc["longitude"] <= dem_bounds.right)
        ].copy()

        if not sikkim_glc.empty:
            sikkim_glc["date"] = pd.to_datetime(sikkim_glc["event_date"]).dt.strftime("%Y%m%d")
            sikkim_glc["location"] = sikkim_glc["location_description"].fillna("NASA_GLC")
            sikkim_glc["label"] = 1
            sikkim_glc = sikkim_glc[["latitude", "longitude", "date", "location", "label"]]
            return pd.concat([manual_landslides, sikkim_glc], ignore_index=True)
    except Exception as e:
        print(f"GLC catalog load skipped ({e}).")

    return manual_landslides


def extract_features(df_points, dem_array, slope_array, dem_transform, smap_mean_map, smap_file_map, dem_crs):
    """Extract spatial features and sample negative baseline locations."""
    dataset = []

    for _, row in df_points.iterrows():
        lat, lon, event_date = row["latitude"], row["longitude"], str(row["date"])
        col, r = ~dem_transform * (lon, lat)
        row_idx, col_idx = int(r), int(col)

        if 0 <= row_idx < dem_array.shape[0] and 0 <= col_idx < dem_array.shape[1]:
            elevation = dem_array[row_idx, col_idx]
            slope = slope_array[row_idx, col_idx]

            if event_date in smap_file_map and os.path.exists(smap_file_map[event_date]):
                sm_arr = resample_soil_moisture(smap_file_map[event_date], dem_array, dem_transform, dem_crs)
                sm_val = sm_arr[row_idx, col_idx] if not np.isnan(sm_arr[row_idx, col_idx]) else smap_mean_map[row_idx, col_idx]
            else:
                sm_val = smap_mean_map[row_idx, col_idx]

            dataset.append({
                "latitude": lat, "longitude": lon, "elevation": elevation,
                "slope": slope, "soil_moisture": sm_val, "label": 1
            })

    pos_df = pd.DataFrame(dataset).dropna().reset_index(drop=True)

    valid_rows, valid_cols = np.where(~np.isnan(dem_array) & ~np.isnan(smap_mean_map))
    pos_coords = [(int((~dem_transform * (r["longitude"], r["latitude"]))[1]), 
                   int((~dem_transform * (r["longitude"], r["latitude"]))[0])) for _, r in pos_df.iterrows()]

    neg_data = []
    attempts, max_attempts = 0, len(pos_df) * 50

    while len(neg_data) < len(pos_df) and attempts < max_attempts:
        attempts += 1
        idx = random.randint(0, len(valid_rows) - 1)
        r_idx, c_idx = valid_rows[idx], valid_cols[idx]

        if any(abs(r_idx - pr) <= 5 and abs(c_idx - pc) <= 5 for pr, pc in pos_coords):
            continue

        lon, lat = dem_transform * (c_idx, r_idx)
        neg_data.append({
            "latitude": lat, "longitude": lon,
            "elevation": dem_array[r_idx, c_idx],
            "slope": slope_array[r_idx, c_idx],
            "soil_moisture": smap_mean_map[r_idx, c_idx],
            "label": 0
        })

    neg_df = pd.DataFrame(neg_data)
    return pd.concat([pos_df, neg_df], ignore_index=True)


if __name__ == "__main__":
    print("--- Starting Sikkim Landslide Feature Extraction Pipeline ---")
    authenticate_nasa()
    dem_arr, slope_arr, transform, crs, bounds = process_dem()

    local_files = sorted(glob.glob("smap_data/*soil_moisture*.tif"))
    print(f"Found {len(local_files)} local SMAP files.")

    mean_sm_map, file_map = compute_smap_mean_streaming(local_files, dem_arr, transform, crs)
    landslide_points = load_landslide_inventory(bounds)

    df_final = extract_features(landslide_points, dem_arr, slope_arr, transform, mean_sm_map, file_map, crs)

    output_path = "sikkim_landslide_dataset.csv"
    df_final.to_csv(output_path, index=False)
    print(f"\nSuccessfully generated feature dataset: {output_path}")
    print(df_final.head())