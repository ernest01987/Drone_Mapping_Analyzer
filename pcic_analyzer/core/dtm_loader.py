# =============================================================================
# core/dtm_loader.py
# Step 1 — Load and validate the drone DTM GeoTIFF
# =============================================================================
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from pyproj import CRS


@dataclass
class DTMInfo:
    """Container for all metadata extracted from a DTM raster."""
    crs: CRS
    epsg: Optional[int]
    crs_name: str
    is_projected: bool
    units: str

    pixel_width: float   # metres (abs of transform.a)
    pixel_height: float  # metres (abs of transform.e)

    width: int           # raster columns
    height: int          # raster rows

    bounds: rasterio.coords.BoundingBox
    nodata: Optional[float]

    min_elevation: float
    max_elevation: float
    mean_elevation: float

    transform: rasterio.transform.Affine
    profile: dict = field(repr=False)


class DTMLoadError(ValueError):
    """Raised when the DTM cannot be loaded or fails validation."""


def load_dtm(source) -> tuple[DTMInfo, np.ndarray]:
    """
    Load a GeoTIFF DTM from a file path or a file-like object.

    Parameters
    ----------
    source : str | Path | BytesIO
        Path to the GeoTIFF, or an in-memory bytes buffer (from
        Streamlit's ``st.file_uploader``).

    Returns
    -------
    info : DTMInfo
        Metadata extracted from the raster.
    elevation : np.ndarray  (float32, 2-D)
        Elevation array with NoData replaced by np.nan.

    Raises
    ------
    DTMLoadError
        If the file cannot be opened, CRS is missing, or CRS is
        geographic (degrees) rather than projected (metres).
    """
    try:
        dataset = rasterio.open(source)
    except Exception as exc:
        raise DTMLoadError(f"Cannot open DTM file: {exc}") from exc

    with dataset:
        # ── CRS ──────────────────────────────────────────────────────────────
        if dataset.crs is None:
            raise DTMLoadError(
                "DTM has no CRS defined. "
                "Please assign the correct projected CRS before uploading."
            )

        crs = CRS.from_user_input(dataset.crs)
        is_projected = crs.is_projected

        try:
            epsg = crs.to_epsg()
        except Exception:
            epsg = None

        try:
            units = crs.axis_info[0].unit_name
        except Exception:
            units = "unknown"

        if not is_projected:
            raise DTMLoadError(
                "DTM must be projected to a metric coordinate system before "
                "surface-area calculation.\n\n"
                "For PCIC Region 10 workflows the recommended CRS is:\n"
                "  EPSG:32651  —  WGS 84 / UTM Zone 51N\n\n"
                "Do NOT simply reassign the CRS to an incorrectly projected "
                "raster. Reproject the raster first, then re-upload."
            )

        # ── Transform & pixel size ────────────────────────────────────────────
        transform = dataset.transform
        pixel_width  = abs(transform.a)
        pixel_height = abs(transform.e)

        if pixel_width <= 0 or pixel_height <= 0:
            raise DTMLoadError(
                f"Invalid pixel resolution: width={pixel_width}, "
                f"height={pixel_height}. "
                "Check that the GeoTIFF transform is valid."
            )

        # ── Read elevation ────────────────────────────────────────────────────
        raw = dataset.read(1).astype(np.float32)
        nodata = dataset.nodata
        if nodata is not None:
            raw[raw == nodata] = np.nan
        # Also mask values that are unrealistically large/small (common artefacts)
        raw[(raw < -500) | (raw > 9000)] = np.nan

        valid = raw[np.isfinite(raw)]
        if valid.size == 0:
            raise DTMLoadError(
                "DTM contains no valid elevation values. "
                "Check NoData settings and raster content."
            )

        profile = dict(dataset.profile)

        info = DTMInfo(
            crs=crs,
            epsg=epsg,
            crs_name=crs.name,
            is_projected=is_projected,
            units=units,
            pixel_width=pixel_width,
            pixel_height=pixel_height,
            width=dataset.width,
            height=dataset.height,
            bounds=dataset.bounds,
            nodata=nodata,
            min_elevation=float(np.nanmin(raw)),
            max_elevation=float(np.nanmax(raw)),
            mean_elevation=float(np.nanmean(raw)),
            transform=transform,
            profile=profile,
        )

    return info, raw
