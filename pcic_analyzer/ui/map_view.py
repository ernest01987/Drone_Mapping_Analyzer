# =============================================================================
# ui/map_view.py
# Interactive Folium map with layer toggles
# =============================================================================
from __future__ import annotations

import base64
from typing import Optional

import folium
import geopandas as gpd
import numpy as np
import streamlit as st
from folium.plugins import FloatImage
from streamlit_folium import st_folium

from config import SLOPE_CLASSES
from utils.raster_utils import array_to_png_bytes, raster_wgs84_bounds


def render_map(
    dtm_info,
    farm_gdf: gpd.GeoDataFrame,
    elevation: np.ndarray,
    slope_degrees: np.ndarray,
    surface_area_pixel: np.ndarray,
    farm_mask: np.ndarray,
) -> None:
    """
    Render an interactive Folium map with toggleable layers:
      - Farm boundary polygon
      - DTM elevation overlay
      - Slope raster overlay
      - Surface-area raster overlay

    Parameters
    ----------
    dtm_info : DTMInfo
    farm_gdf : GeoDataFrame  (in projected CRS)
    elevation, slope_degrees, surface_area_pixel : np.ndarray (2-D)
    farm_mask : np.ndarray (2-D bool)
    """
    # ── Convert farm polygon to WGS84 for Folium ────────────────────────────
    farm_wgs84 = farm_gdf.to_crs("EPSG:4326")
    centroid   = farm_wgs84.geometry.union_all().centroid
    center_lat, center_lon = centroid.y, centroid.x

    # ── Raster overlay bounds ────────────────────────────────────────────────
    south, west, north, east = raster_wgs84_bounds(
        dtm_info.transform, dtm_info.width, dtm_info.height, dtm_info.crs
    )
    bounds_folium = [[south, west], [north, east]]   # Folium expects [[s,w],[n,e]]

    # ── Build map ─────────────────────────────────────────────────────────────
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=15,
        tiles=None,   # we add tiles manually so they can be toggled
    )

    # Base layers
    folium.TileLayer("OpenStreetMap",   name="OpenStreetMap",   overlay=False).add_to(m)
    folium.TileLayer("CartoDB positron", name="Light basemap",   overlay=False).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite",
        overlay=False,
    ).add_to(m)

    # ── Farm boundary layer ──────────────────────────────────────────────────
    farm_layer = folium.FeatureGroup(name="Farm Boundary", show=True)
    folium.GeoJson(
        farm_wgs84.__geo_interface__,
        style_function=lambda _: {
            "fillColor": "#3498db",
            "color":     "#1A3A5C",
            "weight":    3,
            "fillOpacity": 0.15,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=list(farm_wgs84.drop(columns="geometry").columns[:3]),
            labels=True,
        ),
    ).add_to(farm_layer)
    farm_layer.add_to(m)

    # ── DTM elevation overlay ────────────────────────────────────────────────
    dtm_layer = folium.FeatureGroup(name="DTM Elevation", show=False)
    dtm_png = array_to_png_bytes(elevation, cmap="terrain", alpha=0.65)
    _add_image_overlay(dtm_layer, dtm_png, bounds_folium, "DTM Elevation")
    dtm_layer.add_to(m)

    # ── Slope overlay ─────────────────────────────────────────────────────────
    slope_layer = folium.FeatureGroup(name="Slope (degrees)", show=True)
    slope_png = array_to_png_bytes(slope_degrees, cmap="RdYlGn_r",
                                   vmin=0, vmax=45, alpha=0.7)
    _add_image_overlay(slope_layer, slope_png, bounds_folium, "Slope")
    slope_layer.add_to(m)

    # ── Surface-area overlay ─────────────────────────────────────────────────
    sa_layer = folium.FeatureGroup(name="Surface Area (per pixel)", show=False)
    sa_png = array_to_png_bytes(surface_area_pixel, cmap="plasma", alpha=0.70)
    _add_image_overlay(sa_layer, sa_png, bounds_folium, "Surface Area")
    sa_layer.add_to(m)

    # ── Layer control + scale ─────────────────────────────────────────────────
    folium.LayerControl(collapsed=False, position="topright").add_to(m)
    folium.plugins.MeasureControl(position="bottomleft", primary_length_unit="meters").add_to(m)
    folium.plugins.Fullscreen().add_to(m)

    # ── Slope legend ─────────────────────────────────────────────────────────
    _add_slope_legend(m)

    # ── Render in Streamlit ──────────────────────────────────────────────────
    st_folium(m, width=None, height=550, returned_objects=[])


def _add_image_overlay(group, png_bytes: bytes, bounds, name: str) -> None:
    b64 = base64.b64encode(png_bytes).decode()
    url = f"data:image/png;base64,{b64}"
    folium.raster_layers.ImageOverlay(
        image=url,
        bounds=bounds,
        name=name,
        opacity=1.0,
        interactive=False,
        cross_origin=False,
    ).add_to(group)


def _add_slope_legend(m: folium.Map) -> None:
    """Add a floating HTML slope-class legend."""
    items = "".join(
        f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:4px;'>"
        f"<div style='width:14px;height:14px;background:{cls['color']};border-radius:2px;'></div>"
        f"<span style='font-size:11px;'>{cls['label']}</span>"
        f"</div>"
        for cls in SLOPE_CLASSES
    )
    legend_html = f"""
    <div id='map-legend' style='
        position: fixed; bottom: 60px; left: 15px; z-index: 1000;
        background: rgba(255,255,255,0.92);
        padding: 10px 14px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        font-family: sans-serif;
    '>
      <div style='font-weight:700;font-size:12px;margin-bottom:6px;color:#1A3A5C;'>
        Slope Classes
      </div>
      {items}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
