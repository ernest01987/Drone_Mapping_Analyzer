# =============================================================================
# core/quality_control.py
# Quality Control — validate inputs and analysis outputs
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

from config import (
    QC_EXTREME_SLOPE_DEG,
    QC_EXTREME_SLOPE_FRAC_FAIL,
    QC_EXTREME_SLOPE_FRAC_WARN,
    QC_NODATA_FAIL_THRESHOLD,
    QC_NODATA_WARNING_THRESHOLD,
)


class QCStatus(str, Enum):
    PASS    = "PASS"
    WARNING = "WARNING"
    FAIL    = "FAIL"


@dataclass
class QCResult:
    status: QCStatus
    messages: list[str] = field(default_factory=list)

    def _add(self, level: QCStatus, msg: str) -> None:
        self.messages.append(f"[{level.value}] {msg}")
        if level == QCStatus.FAIL:
            self.status = QCStatus.FAIL
        elif level == QCStatus.WARNING and self.status == QCStatus.PASS:
            self.status = QCStatus.WARNING

    def warn(self, msg: str) -> None:
        self._add(QCStatus.WARNING, msg)

    def fail(self, msg: str) -> None:
        self._add(QCStatus.FAIL, msg)

    def info(self, msg: str) -> None:
        self.messages.append(f"[OK] {msg}")


def run_quality_control(
    dtm_info,                        # DTMInfo from dtm_loader
    elevation: np.ndarray,
    slope_degrees: np.ndarray,
    farm_mask: np.ndarray,
    plane_area_ha: float,
    surface_area_ha: float,
    extreme_slope_fraction: float,
    farm_polygon=None,               # shapely Polygon for overlap check
) -> QCResult:
    """
    Run all QC checks and return a consolidated QCResult.

    Parameters
    ----------
    dtm_info : DTMInfo
    elevation : np.ndarray (2-D, float32) — NaN = NoData
    slope_degrees : np.ndarray (2-D, float32)
    farm_mask : np.ndarray (2-D bool)
    plane_area_ha : float
    surface_area_ha : float
    extreme_slope_fraction : float — from SlopeResult
    farm_polygon : shapely Polygon (optional) — for overlap test
    """
    qc = QCResult(status=QCStatus.PASS)

    # ── 1. Projected CRS ──────────────────────────────────────────────────────
    if not dtm_info.is_projected:
        qc.fail(
            "DTM CRS is geographic (degrees). "
            "A projected metric CRS (e.g. EPSG:32651) is required."
        )
    else:
        qc.info(f"CRS is projected: {dtm_info.crs_name} (EPSG:{dtm_info.epsg})")

    # ── 2. CRS units are metres ───────────────────────────────────────────────
    units_lower = dtm_info.units.lower()
    if "metre" in units_lower or "meter" in units_lower:
        qc.info(f"CRS units: {dtm_info.units}")
    else:
        qc.fail(
            f"CRS units are '{dtm_info.units}', not metres. "
            "Surface-area calculation requires a metric CRS."
        )

    # ── 3. Valid pixel resolution ─────────────────────────────────────────────
    if dtm_info.pixel_width > 0 and dtm_info.pixel_height > 0:
        qc.info(
            f"Pixel resolution: {dtm_info.pixel_width:.4f} m × "
            f"{dtm_info.pixel_height:.4f} m"
        )
    else:
        qc.fail(
            f"Invalid pixel resolution: {dtm_info.pixel_width} × "
            f"{dtm_info.pixel_height}. Check raster transform."
        )

    # ── 4. DTM contains valid elevations ─────────────────────────────────────
    valid_elev = np.isfinite(elevation)
    if not valid_elev.any():
        qc.fail(
            "DTM contains no valid elevation values. "
            "Check NoData settings and raster content."
        )
    else:
        qc.info(
            f"Elevation range: {dtm_info.min_elevation:.2f} m – "
            f"{dtm_info.max_elevation:.2f} m"
        )

    # ── 5. Farm polygon overlaps DTM ─────────────────────────────────────────
    pixels_in_farm = int(np.sum(farm_mask))
    if pixels_in_farm == 0:
        qc.fail(
            "Farm polygon does not overlap the DTM extent. "
            "Check that both are in the same projected CRS."
        )
    else:
        # Check for partial overlap (farm pixels vs. total farm bounding area)
        total_raster = elevation.size
        farm_px_ratio = pixels_in_farm / total_raster
        if farm_px_ratio > 0.99:
            qc.warn(
                "Farm polygon covers almost the entire DTM extent. "
                "Verify that the polygon is correctly drawn."
            )
        else:
            qc.info(f"Farm pixels within DTM: {pixels_in_farm:,}")

    # ── 6. NoData inside farm ─────────────────────────────────────────────────
    farm_pixels_total = int(np.sum(farm_mask))
    nodata_in_farm = int(np.sum(farm_mask & ~np.isfinite(elevation)))
    if farm_pixels_total > 0:
        nodata_frac = nodata_in_farm / farm_pixels_total
        if nodata_frac >= QC_NODATA_FAIL_THRESHOLD:
            qc.fail(
                f"{nodata_frac * 100:.1f}% of farm pixels are NoData — "
                "results may be unreliable."
            )
        elif nodata_frac >= QC_NODATA_WARNING_THRESHOLD:
            qc.warn(
                f"{nodata_frac * 100:.1f}% of farm pixels are NoData — "
                "review DTM coverage."
            )
        else:
            qc.info(f"NoData inside farm: {nodata_frac * 100:.2f}%")

    # ── 7. Extreme slopes ─────────────────────────────────────────────────────
    if extreme_slope_fraction >= QC_EXTREME_SLOPE_FRAC_FAIL:
        qc.fail(
            f"Extreme slope values detected in "
            f"{extreme_slope_fraction * 100:.1f}% of pixels "
            f"(>{QC_EXTREME_SLOPE_DEG}°). "
            "Check DTM quality and NoData handling."
        )
    elif extreme_slope_fraction >= QC_EXTREME_SLOPE_FRAC_WARN:
        qc.warn(
            f"Extreme slope values (>{QC_EXTREME_SLOPE_DEG}°) found in "
            f"{extreme_slope_fraction * 100:.2f}% of pixels."
        )
    else:
        qc.info("No excessive extreme slope values detected.")

    # ── 8. Surface area ≥ planimetric area ────────────────────────────────────
    if plane_area_ha > 0:
        ratio = surface_area_ha / plane_area_ha
        if ratio < 1.0 - 1e-4:
            qc.fail(
                f"Surface area ({surface_area_ha:.6f} ha) is smaller than "
                f"planimetric area ({plane_area_ha:.6f} ha). "
                "Check DTM, CRS, polygon, and NoData handling."
            )
        else:
            qc.info(
                f"Surface area >= planimetric area "
                f"(ratio = {ratio:.6f})."
            )

    return qc
