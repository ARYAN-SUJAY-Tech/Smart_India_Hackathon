"""
Download CHIRPS v2.0 daily global rainfall tifs and crop them to the Sikkim
bbox, producing the same 'chirps_precipitation_YYYY/chirps-v2.0.*.tif' folder
structure your Bengaluru pipeline already expects.

CHIRPS v2 covers 50S-50N, which comfortably includes Sikkim (~27.5N), so no
data-availability issue there.

Install once: pip install rasterio requests --break-system-packages
"""

import gzip
import os
import shutil
from datetime import date, timedelta

import rasterio
import requests
from rasterio.windows import from_bounds

# ---------------------------------------------------------------------------
# Config -- adjust the date range to whatever period you want features for
# (e.g. the wet season / a specific historical event window).
# ---------------------------------------------------------------------------
START_DATE = date(2025, 6, 1)
END_DATE = date(2025, 9, 30)
OUT_DIR = "chirps_precipitation_sikkim"

# Sikkim bbox, matching sikkim_bbox.geojson
BBOX = {"west": 88.18, "south": 27.0, "east": 88.82, "north": 27.92}

BASE_URL = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/p05"

os.makedirs(OUT_DIR, exist_ok=True)

d = START_DATE
downloaded, skipped, failed = 0, 0, 0
while d <= END_DATE:
    yyyy_mm_dd = d.strftime("%Y.%m.%d")
    out_path = os.path.join(OUT_DIR, f"chirps-v2.0.{yyyy_mm_dd}.tif")

    if os.path.exists(out_path):
        skipped += 1
        d += timedelta(days=1)
        continue

    url = f"{BASE_URL}/{d.year}/chirps-v2.0.{yyyy_mm_dd}.tif.gz"
    gz_path = out_path + ".gz"

    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(gz_path, "wb") as f:
            f.write(r.content)

        # Decompress
        with gzip.open(gz_path, "rb") as f_in, open(out_path + ".full", "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(gz_path)

        # Crop to Sikkim bbox immediately -- global daily tifs are large,
        # no need to keep the whole-world raster on disk.
        with rasterio.open(out_path + ".full") as src:
            window = from_bounds(BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"], src.transform)
            data = src.read(1, window=window)
            transform = src.window_transform(window)
            profile = src.profile.copy()
            profile.update(height=data.shape[0], width=data.shape[1], transform=transform)

            with rasterio.open(out_path, "w", **profile) as dst:
                dst.write(data, 1)
        os.remove(out_path + ".full")

        downloaded += 1
        if downloaded % 10 == 0:
            print(f"  {downloaded} days downloaded...")

    except Exception as e:
        print(f"FAILED {yyyy_mm_dd}: {e}")
        failed += 1

    d += timedelta(days=1)

print(f"\nDone. Downloaded: {downloaded}, already had: {skipped}, failed: {failed}")
print(f"Files are in ./{OUT_DIR}/ -- point your training script's 'inputdir' at this folder.")
