# =============================================================================
# utils/raster_utils.py
# Helpers for raster display, colormap rendering, and in-memory export
# =============================================================================
from __future__ import annotations

import io
import tempfile
from typing import Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import rasterio
from rasterio.transform import Affine
from rasterio.warp import transform_bounds
from PIL import Image


def array_to_png_bytes(
    arr: np.ndarray,
    cmap: str = "RdYlGn_r",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    alpha: float = 0.7,
) -> bytes:
    """
    Convert a 2-D float array to a PNG-encoded byte string for Folium overlays.

    Transparent where NaN.
    """
    valid = arr[np.isfinite(arr)]
    if valid.size == 0:
        # Return a 1×1 transparent PNG
        img = Image.fromarray(np.zeros((1, 1, 4), dtype=np.uint8))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    vmin = vmin if vmin is not None else float(np.nanmin(arr))
    vmax = vmax if vmax is not None else float(np.nanmax(arr))

    norm = mcolors.Normalize(vmin=vmin, vmax=vmax, clip=True)
    mapper = plt.cm.get_cmap(cmap)

    normed = norm(arr)
    rgba = mapper(normed)                       # H × W × 4, float [0,1]
    rgba[..., 3] = np.where(np.isfinite(arr), alpha, 0.0)
    rgba_uint8 = (rgba * 255).astype(np.uint8)

    img = Image.fromarray(rgba_uint8, mode="RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def raster_wgs84_bounds(
    transform: Affine,
    width: int,
    height: int,
    crs,
) -> Tuple[float, float, float, float]:
    """
    Return (south, west, north, east) in WGS84 for a Folium ImageOverlay.
    """
    left   = transform.c
    top    = transform.f
    right  = left + width  * transform.a
    bottom = top  + height * transform.e   # transform.e is negative

    west, south, east, north = transform_bounds(
        crs, "EPSG:4326",
        left, min(top, bottom), right, max(top, bottom),
    )
    return south, west, north, east


def write_geotiff_bytes(
    arr: np.ndarray,
    transform: Affine,
    crs,
    nodata: float = -9999.0,
) -> bytes:
    """Return a GeoTIFF as bytes for Streamlit download."""
    arr_out = arr.copy().astype(np.float32)
    arr_out[~np.isfinite(arr_out)] = nodata

    buf = io.BytesIO()
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": arr_out.shape[1],
        "height": arr_out.shape[0],
        "count": 1,
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
        "compress": "lzw",
    }
    with rasterio.open(buf, "w", **profile) as dst:
        dst.write(arr_out[np.newaxis, :, :])
    return buf.getvalue()
