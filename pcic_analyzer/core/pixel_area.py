# =============================================================================
# core/pixel_area.py
# Step 2 — Derive pixel dimensions and pixel area from raster transform
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass

import rasterio


@dataclass
class PixelDimensions:
    pixel_width: float   # metres
    pixel_height: float  # metres
    pixel_area: float    # m²


def compute_pixel_dimensions(transform: rasterio.transform.Affine) -> PixelDimensions:
    """
    Derive pixel width, height, and area from the raster affine transform.

    This NEVER hard-codes 0.0025 m² or any specific resolution.
    It works for any DTM resolution (0.05 m, 0.10 m, 0.20 m, 0.50 m, 1.00 m …).

    Parameters
    ----------
    transform : rasterio.transform.Affine
        The affine transform of the opened raster (``dataset.transform``).

    Returns
    -------
    PixelDimensions
        Contains pixel_width, pixel_height, and pixel_area (all in metres / m²).
    """
    pixel_width  = abs(transform.a)   # column pixel size
    pixel_height = abs(transform.e)   # row pixel size  (negative in north-up rasters)
    pixel_area   = pixel_width * pixel_height

    return PixelDimensions(
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        pixel_area=pixel_area,
    )
