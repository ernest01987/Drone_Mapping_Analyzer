# =============================================================================
# core/boundary.py
# Step 3 — Farm boundary: polygon upload (Method A) or waypoints (Method B)
# =============================================================================
from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import CRS
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.validation import make_valid


class BoundaryError(ValueError):
    """Raised when a farm boundary cannot be created or validated."""


# ---------------------------------------------------------------------------
# Method A — Upload an existing polygon file
# ---------------------------------------------------------------------------

def load_polygon_file(source, target_crs: CRS) -> gpd.GeoDataFrame:
    """
    Load a vector polygon file (.gpkg / .geojson / .shp).

    Parameters
    ----------
    source : str | Path | BytesIO
        File path or in-memory buffer.
    target_crs : CRS
        The projected CRS of the DTM.  The polygon will be reprojected
        if its CRS differs.

    Returns
    -------
    GeoDataFrame
        Valid, single-part polygon(s) in the DTM's CRS.
    """
    try:
        if hasattr(source, "read"):
            # Streamlit UploadedFile — write to a temp file first
            suffix = _guess_suffix(source)
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(source.read())
                tmp_path = tmp.name
            gdf = gpd.read_file(tmp_path)
        else:
            gdf = gpd.read_file(source)
    except Exception as exc:
        raise BoundaryError(f"Cannot open boundary file: {exc}") from exc

    if gdf.empty:
        raise BoundaryError("Boundary file contains no features.")

    # ── Ensure polygon geometry ───────────────────────────────────────────────
    gdf = gdf[gdf.geometry.notna()].copy()
    polygons = [_ensure_polygon(g) for g in gdf.geometry]
    valid_indices = [i for i, p in enumerate(polygons) if p is not None]
    if not valid_indices:
        raise BoundaryError("No valid polygon geometry found in boundary file.")

    gdf = gdf.iloc[valid_indices].copy()
    valid_polys: list[Polygon] = [p for p in polygons if p is not None]
    gdf.geometry = valid_polys

    # ── Validate & repair ─────────────────────────────────────────────────────
    repaired_polys: list[Polygon] = [_validate_and_repair(g) for g in valid_polys]
    gdf.geometry = repaired_polys

    # ── Reproject if needed ───────────────────────────────────────────────────
    if gdf.crs is None:
        raise BoundaryError(
            "Farm boundary file has no CRS. "
            "Please assign the correct CRS before uploading."
        )
    if not CRS.from_user_input(gdf.crs).equals(target_crs):
        gdf = gdf.to_crs(target_crs.to_epsg() or target_crs.to_wkt())

    return gdf


# ---------------------------------------------------------------------------
# Method B — Build polygon from ordered waypoints
# ---------------------------------------------------------------------------

def load_waypoints_file(source, target_crs: CRS) -> tuple[gpd.GeoDataFrame, list[str]]:
    """
    Load a waypoint file and return a GeoDataFrame plus its column names.

    Supports .csv (with x/lon and y/lat columns), .gpkg, .geojson, .shp.
    Returns the raw GeoDataFrame so the caller (UI) can let the user pick
    Farm ID and sequence fields.

    Returns
    -------
    (GeoDataFrame, column_names)
    """
    try:
        if hasattr(source, "read"):
            suffix = _guess_suffix(source)
            raw_bytes = source.read()
            if suffix == ".csv":
                df = pd.read_csv(io.BytesIO(raw_bytes))
                # Try to detect coordinate columns
                x_col, y_col = _detect_xy_columns(df)
                gdf = gpd.GeoDataFrame(
                    df,
                    geometry=gpd.points_from_xy(df[x_col], df[y_col]),
                    crs="EPSG:4326" if _looks_geographic(df[x_col]) else None,
                )
            else:
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(raw_bytes)
                    gdf = gpd.read_file(tmp.name)
        else:
            path = Path(source)
            if path.suffix.lower() == ".csv":
                df = pd.read_csv(path)
                x_col, y_col = _detect_xy_columns(df)
                gdf = gpd.GeoDataFrame(
                    df,
                    geometry=gpd.points_from_xy(df[x_col], df[y_col]),
                    crs="EPSG:4326" if _looks_geographic(df[x_col]) else None,
                )
            else:
                gdf = gpd.read_file(path)
    except Exception as exc:
        raise BoundaryError(f"Cannot open waypoints file: {exc}") from exc

    if gdf.empty:
        raise BoundaryError("Waypoints file contains no records.")

    # Reproject if needed
    if gdf.crs is not None and not CRS.from_user_input(gdf.crs).equals(target_crs):
        gdf = gdf.to_crs(target_crs.to_epsg() or target_crs.to_wkt())

    columns = list(gdf.columns)
    return gdf, columns


def build_polygons_from_waypoints(
    gdf: gpd.GeoDataFrame,
    farm_id_field: str,
    sequence_field: str,
    target_crs: CRS,
) -> gpd.GeoDataFrame:
    """
    Convert ordered waypoint rows into closed farm polygons.

    Parameters
    ----------
    gdf : GeoDataFrame
        Waypoint GeoDataFrame (point geometry).
    farm_id_field : str
        Column used to group points by farm.
    sequence_field : str
        Column used to sort points within each farm.
    target_crs : CRS
        The CRS to assign / reproject to.

    Returns
    -------
    GeoDataFrame with Polygon geometry, one row per farm.
    """
    farms = []
    for farm_id, group in gdf.groupby(farm_id_field):
        group = group.sort_values(sequence_field)
        coords = [(geom.x, geom.y) for geom in group.geometry]
        if len(coords) < 3:
            raise BoundaryError(
                f"Farm '{farm_id}' has fewer than 3 waypoints — "
                "cannot create a polygon."
            )
        # Close the ring
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        poly = Polygon(coords)
        poly = _validate_and_repair(poly)
        farms.append({"Farm_ID": farm_id, "geometry": poly})

    if not farms:
        raise BoundaryError("No farm polygons could be built from the waypoints.")

    result = gpd.GeoDataFrame(farms, crs=target_crs.to_epsg() or target_crs.to_wkt())
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_polygon(geom) -> Optional[Polygon]:
    """Return a Polygon from Polygon/MultiPolygon geometry, else None."""
    if geom is None:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        # Return the largest part
        return max(geom.geoms, key=lambda g: g.area)
    return None


def _validate_and_repair(geom: Polygon) -> Polygon:
    """Return a valid geometry, attempting repair via make_valid."""
    if geom.is_valid:
        return geom
    repaired = make_valid(geom)
    if isinstance(repaired, MultiPolygon):
        return max(repaired.geoms, key=lambda g: g.area)
    if isinstance(repaired, Polygon):
        return repaired
    return geom


def _guess_suffix(file_like) -> str:
    name = getattr(file_like, "name", "") or ""
    suffix = Path(name).suffix.lower()
    return suffix if suffix else ".gpkg"


def _detect_xy_columns(df: pd.DataFrame) -> tuple[str, str]:
    """Heuristically find X and Y coordinate columns in a CSV."""
    lower = {c.lower(): c for c in df.columns}
    x_candidates = ["longitude", "lon", "x", "easting",  "long"]
    y_candidates = ["latitude",  "lat", "y", "northing"]
    x_col = next((lower[k] for k in x_candidates if k in lower), None)
    y_col = next((lower[k] for k in y_candidates if k in lower), None)
    if x_col is None or y_col is None:
        raise BoundaryError(
            "Cannot detect X/Y coordinate columns in CSV. "
            f"Detected columns: {list(df.columns)}. "
            "Name them longitude/latitude, lon/lat, x/y, or easting/northing."
        )
    return x_col, y_col


def _looks_geographic(series: pd.Series) -> bool:
    """Return True if values look like longitude (degrees, roughly -180..180)."""
    vals = series.dropna()
    if vals.empty:
        return False
    return float(vals.abs().max()) <= 180.0
