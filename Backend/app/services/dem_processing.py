"""
DEM terrain feature extraction. Independent of ML and frontend —
run this once per target region to populate elevation/slope/aspect
for each village in the DB.

Usage (after placing a DEM GeoTIFF, e.g. from Bhoonidhi/Cartosat-1
or SRTM, under data/dem/):

    python -m app.services.dem_processing data/dem/region.tif

Requires: rasterio, numpy
"""
import sys
import numpy as np
import rasterio
from rasterio.transform import rowcol


def compute_slope_aspect(dem_path: str):
    """
    Returns (elevation, slope_deg, aspect_deg) arrays plus the raster's
    transform/crs, using a simple Sobel-based gradient (same technique
    as the reference repo's slope computation).
    """
    with rasterio.open(dem_path) as src:
        elevation = src.read(1).astype(float)
        transform = src.transform
        crs = src.crs
        # pixel size in the DEM's native units (assume projected CRS in meters;
        # reproject first if your DEM is in geographic/lat-lon degrees)
        px_size_x = transform.a
        px_size_y = -transform.e

    # Sobel kernels for gradient in x and y
    kernel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
    kernel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])

    dzdx = _convolve2d(elevation, kernel_x) / (8 * px_size_x)
    dzdy = _convolve2d(elevation, kernel_y) / (8 * px_size_y)

    slope_rad = np.arctan(np.sqrt(dzdx**2 + dzdy**2))
    slope_deg = np.degrees(slope_rad)

    aspect_rad = np.arctan2(dzdy, -dzdx)
    aspect_deg = (np.degrees(aspect_rad) + 360) % 360

    return elevation, slope_deg, aspect_deg, transform, crs


def _convolve2d(arr: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Minimal same-size 2D convolution without extra deps (scipy optional)."""
    try:
        from scipy.signal import convolve2d
        return convolve2d(arr, kernel, mode="same", boundary="symm")
    except ImportError:
        # fallback: pad + manual convolution (slower, fine for prototype-size tiles)
        pad = np.pad(arr, 1, mode="edge")
        out = np.zeros_like(arr)
        kh, kw = kernel.shape
        for i in range(arr.shape[0]):
            for j in range(arr.shape[1]):
                region = pad[i:i + kh, j:j + kw]
                out[i, j] = np.sum(region * kernel)
        return out


def sample_at_point(dem_path: str, lat: float, lon: float) -> dict:
    """
    Look up elevation/slope/aspect for one village's lat/lon.
    Call this once per village when populating the DB.
    """
    elevation, slope_deg, aspect_deg, transform, crs = compute_slope_aspect(dem_path)
    row, col = rowcol(transform, lon, lat)
    row, col = int(row), int(col)

    if 0 <= row < elevation.shape[0] and 0 <= col < elevation.shape[1]:
        return {
            "elevation_m": float(elevation[row, col]),
            "slope_deg": float(slope_deg[row, col]),
            "aspect_deg": float(aspect_deg[row, col]),
        }
    raise ValueError(f"Point ({lat}, {lon}) falls outside DEM extent")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.services.dem_processing <dem_path.tif>")
        sys.exit(1)
    dem_path = sys.argv[1]
    elevation, slope, aspect, _, _ = compute_slope_aspect(dem_path)
    print(f"Elevation range: {np.nanmin(elevation):.1f} - {np.nanmax(elevation):.1f} m")
    print(f"Slope range: {np.nanmin(slope):.1f} - {np.nanmax(slope):.1f} deg")
