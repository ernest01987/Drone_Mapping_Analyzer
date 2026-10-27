# =============================================================================
# ui/export.py
# Export panel: CSV, GeoPackage, GeoJSON, GeoTIFF × 2, PDF
# =============================================================================
from __future__ import annotations

import io
import json
from datetime import datetime

import geopandas as gpd
import numpy as np
import pandas as pd
import streamlit as st

from utils.raster_utils import write_geotiff_bytes
from utils.pdf_report import generate_pdf_report


def render_export_panel(
    stats_list: list,
    farm_gdf: gpd.GeoDataFrame,
    slope_degrees: np.ndarray,
    surface_area_pixel: np.ndarray,
    dtm_info,
    qc_result,
    chart_bytes: bytes,
) -> None:
    """
    Render the Export tab with download buttons for all output formats.
    """
    st.markdown("### 📤 Export Results")
    st.info(
        "All outputs below reflect the current analysis. "
        "Run the analysis before exporting."
    )

    if not stats_list:
        st.warning("No analysis results available. Run the analysis first.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stats = stats_list[0]   # primary farm for single-farm outputs

    col1, col2, col3 = st.columns(3)

    # ── 1. CSV ───────────────────────────────────────────────────────────────
    with col1:
        csv_bytes = _build_csv(stats_list)
        st.download_button(
            label="📄 Download CSV",
            data=csv_bytes,
            file_name=f"PCIC_Farm_Analysis_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
            key="dl_csv",
        )

    # ── 2. GeoPackage ─────────────────────────────────────────────────────────
    with col2:
        gpkg_bytes = _build_vector(farm_gdf, stats_list, fmt="GPKG")
        st.download_button(
            label="🗂️ Download GeoPackage",
            data=gpkg_bytes,
            file_name=f"PCIC_Farm_Analysis_{timestamp}.gpkg",
            mime="application/octet-stream",
            use_container_width=True,
            key="dl_gpkg",
        )

    # ── 3. GeoJSON ─────────────────────────────────────────────────────────────
    with col3:
        geojson_bytes = _build_vector(farm_gdf, stats_list, fmt="GeoJSON")
        st.download_button(
            label="🌐 Download GeoJSON",
            data=geojson_bytes,
            file_name=f"PCIC_Farm_Analysis_{timestamp}.geojson",
            mime="application/geo+json",
            use_container_width=True,
            key="dl_geojson",
        )

    col4, col5, col6 = st.columns(3)

    # ── 4. Slope GeoTIFF ─────────────────────────────────────────────────────
    with col4:
        slope_tif = write_geotiff_bytes(slope_degrees, dtm_info.transform, dtm_info.crs)
        st.download_button(
            label="🏔️ Slope GeoTIFF",
            data=slope_tif,
            file_name=f"PCIC_Slope_{timestamp}.tif",
            mime="image/tiff",
            use_container_width=True,
            key="dl_slope_tif",
        )

    # ── 5. Surface-area GeoTIFF ───────────────────────────────────────────────
    with col5:
        sa_tif = write_geotiff_bytes(surface_area_pixel, dtm_info.transform, dtm_info.crs)
        st.download_button(
            label="📐 Surface Area GeoTIFF",
            data=sa_tif,
            file_name=f"PCIC_SurfaceArea_{timestamp}.tif",
            mime="image/tiff",
            use_container_width=True,
            key="dl_sa_tif",
        )

    # ── 6. PDF Report ─────────────────────────────────────────────────────────
    with col6:
        try:
            pdf_bytes = generate_pdf_report(
                stats=stats,
                qc_result=qc_result,
                farm_id=stats.farm_id,
                chart_bytes=chart_bytes,
            )
            st.download_button(
                label="📑 PDF Report",
                data=pdf_bytes,
                file_name=f"PCIC_Report_{timestamp}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="dl_pdf",
            )
        except Exception as exc:
            st.error(f"PDF generation failed: {exc}")

    # ── Output folder note ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        """
        **Suggested output folder structure:**
        ```
        07_Final_Output/
        ├── 01_DTM/
        ├── 02_Waypoints/
        ├── 03_Farm_Polygon/
        ├── 04_Slope/
        ├── 05_Surface_Area_Raster/
        ├── 06_Zonal_Statistics/
        └── 07_Final_Output/
        ```
        Organise your downloaded files into these folders for archiving.
        """
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_csv(stats_list: list) -> bytes:
    rows = []
    for s in stats_list:
        row = {
            "Farm_ID":            s.farm_id,
            "Plane_area_m2":      round(s.plane_area_m2, 4),
            "Plane_area_ha":      round(s.plane_area_ha, 6),
            "Surface_area_m2":    round(s.surface_area_m2, 4),
            "Surface_area_ha":    round(s.surface_area_ha, 6),
            "Area_Difference_ha": round(s.area_difference_ha, 6),
            "Area_Increase_pc":   round(s.area_increase_pc, 4),
            "Mean_Slope_deg":     round(s.mean_slope_deg, 4),
            "Min_Slope_deg":      round(s.min_slope_deg, 4),
            "Max_Slope_deg":      round(s.max_slope_deg, 4),
            "Median_Slope_deg":   round(s.median_slope_deg, 4),
            "Mean_Slope_pc":      round(s.mean_slope_pc, 4),
            "Mean_Elevation_m":   round(s.mean_elevation_m, 3),
            "Min_Elevation_m":    round(s.min_elevation_m, 3),
            "Max_Elevation_m":    round(s.max_elevation_m, 3),
            "dtm_count":          s.dtm_count,
            "dtm_mean":           round(s.dtm_mean, 8),
            "dtm_sum":            round(s.dtm_sum, 4),
        }
        # Slope classes
        for sc in s.slope_classes:
            safe = sc.label.replace("–", "_").replace(">", "gt").replace("%", "pc")
            row[f"SlopeClass_{safe}_plane_ha"]   = round(sc.plane_area_ha, 6)
            row[f"SlopeClass_{safe}_surface_ha"] = round(sc.surface_area_ha, 6)
        rows.append(row)

    df = pd.DataFrame(rows)
    return df.to_csv(index=False).encode("utf-8")


def _build_vector(farm_gdf: gpd.GeoDataFrame, stats_list: list, fmt: str) -> bytes:
    """Attach analysis attributes to the farm GeoDataFrame and export."""
    gdf = farm_gdf.copy()
    # Build lookup by index position (assumes rows match)
    for i, s in enumerate(stats_list):
        if i >= len(gdf):
            break
        gdf.at[gdf.index[i], "Plane_area_ha"]      = round(s.plane_area_ha, 6)
        gdf.at[gdf.index[i], "Surface_area_ha"]    = round(s.surface_area_ha, 6)
        gdf.at[gdf.index[i], "Area_Difference_ha"] = round(s.area_difference_ha, 6)
        gdf.at[gdf.index[i], "Area_Increase_pc"]   = round(s.area_increase_pc, 4)
        gdf.at[gdf.index[i], "Mean_Slope_deg"]     = round(s.mean_slope_deg, 4)
        gdf.at[gdf.index[i], "Mean_Slope_pc"]      = round(s.mean_slope_pc, 4)
        gdf.at[gdf.index[i], "dtm_count"]          = s.dtm_count

    buf = io.BytesIO()
    if fmt == "GPKG":
        gdf.to_file(buf, driver="GPKG", layer="farm_analysis")
    elif fmt == "GeoJSON":
        gdf_wgs84 = gdf.to_crs("EPSG:4326")
        buf.write(gdf_wgs84.to_json().encode("utf-8"))
    buf.seek(0)
    return buf.read()
