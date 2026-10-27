# =============================================================================
# core/statistics.py
# Steps 9–12 — Area difference, % increase, terrain statistics, slope classes
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from config import SLOPE_CLASSES


@dataclass
class SlopeClassStats:
    label: str
    plane_area_ha: float   # planimetric area (pixel_area × pixel count)
    surface_area_ha: float # 3D surface area (sum of surface_area_pixel)


@dataclass
class TerrainStatistics:
    # ── Slope ────────────────────────────────────────────────────────────────
    mean_slope_deg: float
    min_slope_deg: float
    max_slope_deg: float
    median_slope_deg: float
    mean_slope_pc: float

    # ── Elevation ─────────────────────────────────────────────────────────────
    mean_elevation_m: float
    min_elevation_m: float
    max_elevation_m: float

    # ── Areas ─────────────────────────────────────────────────────────────────
    plane_area_m2: float
    plane_area_ha: float
    surface_area_m2: float
    surface_area_ha: float
    area_difference_ha: float
    area_increase_pc: float

    # ── Pixel summary ─────────────────────────────────────────────────────────
    dtm_count: int
    dtm_mean: float
    dtm_sum: float

    # ── Slope classes ─────────────────────────────────────────────────────────
    slope_classes: list[SlopeClassStats] = field(default_factory=list)

    farm_id: str = ""


def compute_statistics(
    elevation: np.ndarray,
    slope_degrees: np.ndarray,
    slope_radians: np.ndarray,
    slope_percent: np.ndarray,
    surface_area_pixel: np.ndarray,
    farm_mask: np.ndarray,
    plane_area_m2: float,
    plane_area_ha: float,
    surface_area_m2: float,
    surface_area_ha: float,
    dtm_count: int,
    dtm_mean: float,
    dtm_sum: float,
    pixel_area: float,
    farm_id: str = "",
) -> TerrainStatistics:
    """
    Compute terrain statistics and derive area difference / percentage increase.

    Parameters
    ----------
    elevation, slope_degrees, slope_radians, slope_percent : np.ndarray (2-D)
        Raster arrays (NaN = NoData or outside farm).
    surface_area_pixel : np.ndarray (2-D)
        Per-pixel 3D surface area (NaN outside valid farm pixels).
    farm_mask : np.ndarray (2-D bool)
        True = inside farm boundary.
    plane_area_m2 / _ha : float
        Planimetric area from Step 4.
    surface_area_m2 / _ha : float
        Total 3D surface area from Step 8.
    dtm_count, dtm_mean, dtm_sum : int / float
        Pixel-level stats from Step 8.
    pixel_area : float
        pixel_width × pixel_height [m²].
    farm_id : str
        Label for this farm.

    Returns
    -------
    TerrainStatistics
    """
    # Only use pixels inside the farm with valid data
    valid = farm_mask & np.isfinite(slope_degrees)

    # ── Slope statistics ──────────────────────────────────────────────────────
    slope_vals = slope_degrees[valid]
    mean_slope_deg   = float(np.mean(slope_vals))   if slope_vals.size else 0.0
    min_slope_deg    = float(np.min(slope_vals))    if slope_vals.size else 0.0
    max_slope_deg    = float(np.max(slope_vals))    if slope_vals.size else 0.0
    median_slope_deg = float(np.median(slope_vals)) if slope_vals.size else 0.0
    mean_slope_pc    = float(np.mean(slope_percent[valid])) if slope_vals.size else 0.0

    # ── Elevation statistics ──────────────────────────────────────────────────
    elev_valid = farm_mask & np.isfinite(elevation)
    elev_vals = elevation[elev_valid]
    mean_elev = float(np.mean(elev_vals))   if elev_vals.size else 0.0
    min_elev  = float(np.min(elev_vals))    if elev_vals.size else 0.0
    max_elev  = float(np.max(elev_vals))    if elev_vals.size else 0.0

    # ── Steps 9 & 10: Area difference and percentage increase ─────────────────
    area_difference_ha = surface_area_ha - plane_area_ha
    if plane_area_ha > 0:
        area_increase_pc = (area_difference_ha / plane_area_ha) * 100.0
    else:
        area_increase_pc = 0.0

    # ── Step 12: Slope classes ────────────────────────────────────────────────
    slope_class_stats = _compute_slope_classes(
        slope_percent=slope_percent,
        surface_area_pixel=surface_area_pixel,
        farm_mask=farm_mask,
        pixel_area=pixel_area,
    )

    return TerrainStatistics(
        mean_slope_deg=mean_slope_deg,
        min_slope_deg=min_slope_deg,
        max_slope_deg=max_slope_deg,
        median_slope_deg=median_slope_deg,
        mean_slope_pc=mean_slope_pc,
        mean_elevation_m=mean_elev,
        min_elevation_m=min_elev,
        max_elevation_m=max_elev,
        plane_area_m2=plane_area_m2,
        plane_area_ha=plane_area_ha,
        surface_area_m2=surface_area_m2,
        surface_area_ha=surface_area_ha,
        area_difference_ha=area_difference_ha,
        area_increase_pc=area_increase_pc,
        dtm_count=dtm_count,
        dtm_mean=dtm_mean,
        dtm_sum=dtm_sum,
        slope_classes=slope_class_stats,
        farm_id=farm_id,
    )


def _compute_slope_classes(
    slope_percent: np.ndarray,
    surface_area_pixel: np.ndarray,
    farm_mask: np.ndarray,
    pixel_area: float,
) -> list[SlopeClassStats]:
    """
    Compute planimetric and 3D surface area per slope class (BSWM standard).

    Slope percent = tan(slope_radians) × 100  (correct formula).
    """
    results = []
    for cls in SLOPE_CLASSES:
        lo = cls["min"]
        hi = cls["max"]  # None means open upper bound

        if hi is None:
            class_mask = farm_mask & np.isfinite(slope_percent) & (slope_percent > lo)
        else:
            class_mask = (
                farm_mask
                & np.isfinite(slope_percent)
                & (slope_percent >= lo)
                & (slope_percent < hi)
            )

        pixel_count = int(np.sum(class_mask))
        plane_ha = (pixel_count * pixel_area) / 10_000.0

        sa_vals = surface_area_pixel[class_mask & np.isfinite(surface_area_pixel)]
        surface_ha = float(np.sum(sa_vals)) / 10_000.0 if sa_vals.size else 0.0

        results.append(
            SlopeClassStats(
                label=cls["label"],
                plane_area_ha=round(plane_ha, 6),
                surface_area_ha=round(surface_ha, 6),
            )
        )
    return results
