# =============================================================================
# core/slope.py
# Step 5 — Compute slope raster from DTM elevation
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import rasterio
from rasterio.transform import Affine

from config import QC_EXTREME_SLOPE_DEG


@dataclass
class SlopeResult:
    slope_radians: np.ndarray    # 2-D, float32
    slope_degrees: np.ndarray    # 2-D, float32
    slope_percent: np.ndarray    # 2-D, float32
    extreme_pixel_count: int     # pixels > QC_EXTREME_SLOPE_DEG
    extreme_pixel_fraction: float


def compute_slope(
    elevation: np.ndarray,
    pixel_width: float,
    pixel_height: float,
) -> SlopeResult:
    """
    Calculate terrain slope from a DTM elevation grid.

    Uses numpy.gradient with the actual pixel spacing so the result is
    correct regardless of raster resolution.

    Parameters
    ----------
    elevation : np.ndarray (float32, 2-D)
        DTM elevation array with NoData as np.nan.
    pixel_width : float
        Absolute pixel width in metres (``abs(transform.a)``).
    pixel_height : float
        Absolute pixel height in metres (``abs(transform.e)``).

    Returns
    -------
    SlopeResult
    """
    # Fill NaN with the local mean for gradient calculation, then re-mask
    elev_filled = _fill_nan(elevation)

    # numpy.gradient axes: [0] = rows (y), [1] = cols (x)
    dz_dy, dz_dx = np.gradient(elev_filled, pixel_height, pixel_width)

    slope_radians = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2)).astype(np.float32)
    slope_degrees = np.degrees(slope_radians).astype(np.float32)
    slope_percent = (np.tan(slope_radians) * 100).astype(np.float32)

    # Restore NaN mask from original elevation
    nan_mask = ~np.isfinite(elevation)
    slope_radians[nan_mask] = np.nan
    slope_degrees[nan_mask] = np.nan
    slope_percent[nan_mask] = np.nan

    # Flag extreme slopes
    valid_mask = np.isfinite(slope_degrees)
    extreme_mask = valid_mask & (slope_degrees > QC_EXTREME_SLOPE_DEG)
    extreme_count = int(np.sum(extreme_mask))
    total_valid = int(np.sum(valid_mask))
    extreme_frac = extreme_count / total_valid if total_valid > 0 else 0.0

    return SlopeResult(
        slope_radians=slope_radians,
        slope_degrees=slope_degrees,
        slope_percent=slope_percent,
        extreme_pixel_count=extreme_count,
        extreme_pixel_fraction=extreme_frac,
    )


def save_slope_raster(
    slope_degrees: np.ndarray,
    transform: Affine,
    crs,
    output_path: str,
    nodata: float = -9999.0,
) -> None:
    """Write the slope-in-degrees array to a GeoTIFF."""
    arr = slope_degrees.copy()
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fill_nan(arr: np.ndarray) -> np.ndarray:
    """Replace NaN with the array mean (simple fill for gradient)."""
    filled = arr.copy()
    nan_mask = ~np.isfinite(filled)
    if nan_mask.any():
        filled[nan_mask] = np.nanmean(filled)
    return filled
