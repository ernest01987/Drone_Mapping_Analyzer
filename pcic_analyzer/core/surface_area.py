# =============================================================================
# core/surface_area.py
# Steps 6–8 — Per-pixel surface area, farm mask, and total 3D surface area
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import rasterio
from rasterio.features import rasterize as rio_rasterize
from rasterio.transform import Affine
from shapely.geometry import mapping

from config import QC_MIN_COS_SLOPE


@dataclass
class SurfaceAreaResult:
    surface_area_pixel: np.ndarray   # 2-D, m² per pixel (NaN outside farm)
    farm_mask: np.ndarray            # 2-D bool: True = inside farm polygon

    surface_area_m2: float           # Total 3D surface area [m²]
    surface_area_ha: float           # Total 3D surface area [ha]

    dtm_count: int                   # Valid pixels used
    dtm_mean: float                  # Mean per-pixel contribution [m²]
    dtm_sum: float                   # = surface_area_m2


def compute_surface_area(
    elevation: np.ndarray,
    slope_radians: np.ndarray,
    pixel_width: float,
    pixel_height: float,
    farm_polygon,                    # shapely Polygon or GeoDataFrame row geometry
    transform: Affine,
    all_touched: bool = False,
) -> SurfaceAreaResult:
    """
    Calculate the 3D terrain surface area inside a farm polygon.

    Formula (per pixel):
        A_surface = (pixel_width × pixel_height) / cos(slope_radians)

    Only valid pixels inside the farm polygon, with finite slope and
    cos(slope) above the guard threshold, contribute to the total.

    Parameters
    ----------
    elevation : np.ndarray (2-D, float32)
        DTM elevation array (NaN = NoData).
    slope_radians : np.ndarray (2-D, float32)
        Slope in radians from ``core.slope.compute_slope``.
    pixel_width, pixel_height : float
        Pixel dimensions in metres.
    farm_polygon : shapely geometry
        Farm boundary polygon (must be in the same CRS as the DTM).
    transform : Affine
        Raster affine transform.
    all_touched : bool
        If True, include boundary-touching pixels (rasterio ``all_touched``).
        Default: pixel-center inclusion.

    Returns
    -------
    SurfaceAreaResult
    """
    height_px, width_px = elevation.shape
    pixel_area = pixel_width * pixel_height

    # ── Step 6: Per-pixel surface area ───────────────────────────────────────
    cos_slope = np.cos(slope_radians)
    # Guard: avoid divide-by-zero for near-vertical slopes (≈90°)
    cos_slope_safe = np.where(
        np.isfinite(cos_slope) & (cos_slope > QC_MIN_COS_SLOPE),
        cos_slope,
        np.nan,
    )
    surface_area_pixel = (pixel_area / cos_slope_safe).astype(np.float32)

    # ── Step 7: Farm mask (rasterize polygon) ─────────────────────────────────
    shapes = [(mapping(farm_polygon), 1)]
    farm_mask = rio_rasterize(
        shapes,
        out_shape=(height_px, width_px),
        transform=transform,
        fill=0,
        dtype=np.uint8,
        all_touched=all_touched,
    ).astype(bool)

    # ── Step 8: Valid pixel mask ──────────────────────────────────────────────
    nodata_mask = ~np.isfinite(elevation)
    invalid_surface = ~np.isfinite(surface_area_pixel)

    valid_mask = farm_mask & ~nodata_mask & ~invalid_surface

    # Apply mask to surface_area_pixel (NaN outside)
    sa_masked = np.where(valid_mask, surface_area_pixel, np.nan)

    # ── Totals ────────────────────────────────────────────────────────────────
    dtm_count = int(np.sum(valid_mask))
    dtm_sum   = float(np.nansum(sa_masked))
    dtm_mean  = dtm_sum / dtm_count if dtm_count > 0 else 0.0

    surface_area_m2 = dtm_sum
    surface_area_ha = surface_area_m2 / 10_000.0

    return SurfaceAreaResult(
        surface_area_pixel=sa_masked,
        farm_mask=farm_mask,
        surface_area_m2=surface_area_m2,
        surface_area_ha=surface_area_ha,
        dtm_count=dtm_count,
        dtm_mean=dtm_mean,
        dtm_sum=dtm_sum,
    )


def save_surface_area_raster(
    surface_area_pixel: np.ndarray,
    transform: Affine,
    crs,
    output_path: str,
    nodata: float = -9999.0,
) -> None:
    """Write the per-pixel surface-area array to a GeoTIFF."""
    arr = surface_area_pixel.copy()
    arr[~np.isfinite(arr)] = nodata

    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": arr.shape[1],
        "height": arr.shape[0],
        "count": 1,
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
        "compress": "lzw",
    }
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(arr[np.newaxis, :, :])
