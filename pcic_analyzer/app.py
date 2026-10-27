# =============================================================================
# app.py
# PCIC Drone 3D Farm Area Analyzer — Streamlit entry point
# =============================================================================
from __future__ import annotations

import sys
import os

# Make sure sibling packages (core/, ui/, utils/) are importable
sys.path.insert(0, os.path.dirname(__file__))

import traceback

import geopandas as gpd
import numpy as np
import streamlit as st
from pyproj import CRS

from config import APP_NAME, APP_SUBTITLE, ORGANIZATION

# ── Core modules ───────────────────────────────────────────────────────────────
from core.dtm_loader      import load_dtm, DTMLoadError
from core.pixel_area      import compute_pixel_dimensions
from core.boundary        import (
    load_polygon_file, load_waypoints_file,
    build_polygons_from_waypoints, BoundaryError,
)
from core.planimetric     import compute_planimetric_area
from core.slope           import compute_slope
from core.surface_area    import compute_surface_area
from core.statistics      import compute_statistics
from core.quality_control import run_quality_control

# ── UI modules ─────────────────────────────────────────────────────────────────
from ui.sidebar    import render_sidebar
from ui.dashboard  import (
    render_dtm_info, render_qc_badge, render_metric_cards,
    render_terrain_stats, render_slope_class_table, render_comparison_table,
)
from ui.map_view   import render_map
from ui.charts     import render_area_comparison_chart, render_slope_class_chart
from ui.export     import render_export_panel


# ===========================================================================
# Page configuration
# ===========================================================================
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🛩️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            f"**{APP_NAME}**\n\n"
            f"{APP_SUBTITLE}\n\n"
            f"Developed for {ORGANIZATION}"
        )
    },
)

# ===========================================================================
# Custom CSS — premium dark-accent design
# ===========================================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Header gradient bar ── */
    .header-banner {
        background: linear-gradient(135deg, #1A3A5C 0%, #2471A3 60%, #1ABC9C 100%);
        border-radius: 12px;
        padding: 24px 32px;
        margin-bottom: 18px;
        color: white;
    }
    .header-banner h1 {
        font-size: 1.9rem;
        font-weight: 800;
        margin: 0 0 4px 0;
        letter-spacing: -0.5px;
    }
    .header-banner .subtitle {
        font-size: 0.9rem;
        opacity: 0.85;
        font-weight: 400;
    }
    .header-banner .org {
        font-size: 0.78rem;
        opacity: 0.65;
        margin-top: 6px;
    }

    /* ── Metric cards ── */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #F8FBFF, #EDF2F7);
        border: 1px solid #D5E8F5;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 2px 6px rgba(26,58,92,0.07);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(26,58,92,0.12);
    }
    [data-testid="stMetricLabel"] > div {
        font-size: 0.78rem;
        font-weight: 600;
        color: #5D6D7E;
        letter-spacing: 0.3px;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1A3A5C;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F0F4F8 0%, #E8EFF7 100%);
    }
    [data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #1A3A5C, #2471A3) !important;
        color: white !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px !important;
        letter-spacing: 0.3px !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, #154360, #1A5276) !important;
        box-shadow: 0 4px 12px rgba(26,58,92,0.3) !important;
    }

    /* ── Tab styling ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background: #F0F4F8;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        font-weight: 600;
        padding: 8px 20px;
        color: #5D6D7E;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1A3A5C, #2471A3) !important;
        color: white !important;
    }

    /* ── Dataframe ── */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #D5E8F5;
    }

    /* ── Status messages ── */
    .stSuccess, .stWarning, .stError, .stInfo {
        border-radius: 8px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ===========================================================================
# Header
# ===========================================================================
st.markdown(
    f"""
    <div class='header-banner'>
        <h1>🛩️ {APP_NAME}</h1>
        <div class='subtitle'>{APP_SUBTITLE}</div>
        <div class='org'>{ORGANIZATION}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ===========================================================================
# Session state initialisation
# ===========================================================================
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done  = False
if "results"       not in st.session_state:
    st.session_state.results        = {}
if "waypoint_columns" not in st.session_state:
    st.session_state.waypoint_columns = []


# ===========================================================================
# Sidebar
# ===========================================================================
sidebar = render_sidebar()

dtm_file        = sidebar["dtm_file"]
boundary_method = sidebar["boundary_method"]
polygon_file    = sidebar["polygon_file"]
waypoint_file   = sidebar["waypoint_file"]
farm_id_field   = sidebar["farm_id_field"]
sequence_field  = sidebar["sequence_field"]
all_touched     = sidebar["all_touched"]
run_clicked     = sidebar["run_clicked"]


# ===========================================================================
# Tabs
# ===========================================================================
tab_dash, tab_map, tab_charts, tab_export = st.tabs(
    ["📊 Dashboard", "🗺️ Map", "📈 Charts", "📤 Export"]
)


# ===========================================================================
# Early DTM info display (before analysis)
# ===========================================================================
if dtm_file and not st.session_state.analysis_done:
    try:
        dtm_info, _ = load_dtm(dtm_file)
        with tab_dash:
            render_dtm_info(dtm_info)
    except DTMLoadError as e:
        with tab_dash:
            st.error(f"❌ DTM Error: {e}")

# Pre-load waypoint columns for sidebar field selection
if waypoint_file and not st.session_state.analysis_done:
    try:
        dtm_file_tmp = dtm_file
        if dtm_file_tmp:
            dtm_info_tmp, _ = load_dtm(dtm_file_tmp)
            _wpt_gdf, cols = load_waypoints_file(waypoint_file, dtm_info_tmp.crs)
            st.session_state.waypoint_columns = cols
        else:
            st.session_state.waypoint_columns = []
    except Exception:
        pass


# ===========================================================================
# Analysis
# ===========================================================================
if run_clicked:
    st.session_state.analysis_done = False

    # ── Validate required inputs ─────────────────────────────────────────────
    errors = []
    if dtm_file is None:
        errors.append("Upload a DTM GeoTIFF.")
    if boundary_method.startswith("Method A") and polygon_file is None:
        errors.append("Upload a farm polygon file (Method A).")
    if boundary_method.startswith("Method B"):
        if waypoint_file is None:
            errors.append("Upload a waypoints file (Method B).")
        elif not farm_id_field or not sequence_field:
            errors.append("Select Farm ID field and Sequence field.")

    if errors:
        with tab_dash:
            for e in errors:
                st.error(f"❌ {e}")
        st.stop()

    with tab_dash:
        progress = st.progress(0, text="Starting analysis…")

    try:
        # ── Step 1: Load DTM ─────────────────────────────────────────────────
        with tab_dash:
            progress.progress(5, text="Step 1 — Loading DTM…")
        dtm_file.seek(0)
        dtm_info, elevation = load_dtm(dtm_file)

        with tab_dash:
            render_dtm_info(dtm_info)

        # ── Step 2: Pixel dimensions ─────────────────────────────────────────
        px = compute_pixel_dimensions(dtm_info.transform)
        with tab_dash:
            progress.progress(15, text="Step 2 — Pixel dimensions computed.")

        # ── Step 3: Farm boundary ─────────────────────────────────────────────
        with tab_dash:
            progress.progress(20, text="Step 3 — Loading farm boundary…")

        if boundary_method.startswith("Method A"):
            polygon_file.seek(0)
            farm_gdf = load_polygon_file(polygon_file, dtm_info.crs)
        else:
            waypoint_file.seek(0)
            wpt_gdf, cols = load_waypoints_file(waypoint_file, dtm_info.crs)
            st.session_state.waypoint_columns = cols
            farm_gdf = build_polygons_from_waypoints(
                wpt_gdf, farm_id_field, sequence_field, dtm_info.crs
            )

        # Detect the Farm ID column
        farm_id_col = "Farm_ID" if "Farm_ID" in farm_gdf.columns else farm_gdf.columns[0]

        # ── Step 4: Planimetric area ──────────────────────────────────────────
        with tab_dash:
            progress.progress(30, text="Step 4 — Computing planimetric areas…")
        plan_results = compute_planimetric_area(farm_gdf, farm_id_col)

        # ── Step 5: Slope ─────────────────────────────────────────────────────
        with tab_dash:
            progress.progress(40, text="Step 5 — Computing slope raster…")
        slope_result = compute_slope(elevation, px.pixel_width, px.pixel_height)

        # ── Steps 6–8 & Statistics: per farm ─────────────────────────────────
        all_stats   = []
        qc_results  = []
        last_sa     = None   # For map display (last or only farm)
        last_mask   = None

        total_farms = len(farm_gdf)
        for idx, (row_idx, farm_row) in enumerate(farm_gdf.iterrows()):
            pct = 50 + int((idx / total_farms) * 40)
            with tab_dash:
                progress.progress(pct, text=f"Steps 6–12 — Farm {idx+1}/{total_farms}…")

            farm_poly  = farm_row.geometry
            plan_res   = plan_results[idx]

            # Steps 6–8: surface area
            sa_result = compute_surface_area(
                elevation=elevation,
                slope_radians=slope_result.slope_radians,
                pixel_width=px.pixel_width,
                pixel_height=px.pixel_height,
                farm_polygon=farm_poly,
                transform=dtm_info.transform,
                all_touched=all_touched,
            )

            # Steps 9–12: statistics
            stats = compute_statistics(
                elevation=elevation,
                slope_degrees=slope_result.slope_degrees,
                slope_radians=slope_result.slope_radians,
                slope_percent=slope_result.slope_percent,
                surface_area_pixel=sa_result.surface_area_pixel,
                farm_mask=sa_result.farm_mask,
                plane_area_m2=plan_res.plane_area_m2,
                plane_area_ha=plan_res.plane_area_ha,
                surface_area_m2=sa_result.surface_area_m2,
                surface_area_ha=sa_result.surface_area_ha,
                dtm_count=sa_result.dtm_count,
                dtm_mean=sa_result.dtm_mean,
                dtm_sum=sa_result.dtm_sum,
                pixel_area=px.pixel_area,
                farm_id=plan_res.farm_id,
            )

            # QC
            qc = run_quality_control(
                dtm_info=dtm_info,
                elevation=elevation,
                slope_degrees=slope_result.slope_degrees,
                farm_mask=sa_result.farm_mask,
                plane_area_ha=plan_res.plane_area_ha,
                surface_area_ha=sa_result.surface_area_ha,
                extreme_slope_fraction=slope_result.extreme_pixel_fraction,
                farm_polygon=farm_poly,
            )

            all_stats.append(stats)
            qc_results.append(qc)
            last_sa   = sa_result
            last_mask = sa_result.farm_mask

        # ── Build comparison chart bytes (for PDF) ────────────────────────────
        from ui.charts import render_area_comparison_chart
        chart_bytes = render_area_comparison_chart(all_stats)

        # ── Store results in session state ────────────────────────────────────
        st.session_state.results = {
            "dtm_info":            dtm_info,
            "elevation":           elevation,
            "slope_result":        slope_result,
            "farm_gdf":            farm_gdf,
            "all_stats":           all_stats,
            "qc_results":          qc_results,
            "last_sa":             last_sa,
            "chart_bytes":         chart_bytes,
            "px":                  px,
        }
        st.session_state.analysis_done = True

        with tab_dash:
            progress.progress(100, text="✅ Analysis complete!")

    except (DTMLoadError, BoundaryError) as exc:
        with tab_dash:
            st.error(f"❌ {exc}")
        st.stop()
    except Exception as exc:
        with tab_dash:
            st.error(f"❌ Unexpected error: {exc}")
            with st.expander("Stack trace"):
                st.code(traceback.format_exc())
        st.stop()


# ===========================================================================
# Display results
# ===========================================================================
if st.session_state.analysis_done and st.session_state.results:
    r = st.session_state.results

    dtm_info     = r["dtm_info"]
    elevation    = r["elevation"]
    slope_result = r["slope_result"]
    farm_gdf     = r["farm_gdf"]
    all_stats    = r["all_stats"]
    qc_results   = r["qc_results"]
    last_sa      = r["last_sa"]
    chart_bytes  = r["chart_bytes"]
    px           = r["px"]

    primary_stats = all_stats[0]
    primary_qc    = qc_results[0]

    # ── Dashboard tab ─────────────────────────────────────────────────────────
    with tab_dash:
        render_qc_badge(primary_qc)
        st.markdown("---")
        render_metric_cards(primary_stats)
        st.markdown("---")
        render_terrain_stats(primary_stats)
        st.markdown("---")
        render_slope_class_table(primary_stats)
        if len(all_stats) > 1:
            st.markdown("---")
            render_comparison_table(all_stats)

    # ── Map tab ───────────────────────────────────────────────────────────────
    with tab_map:
        st.markdown("### 🗺️ Interactive Farm Map")
        render_map(
            dtm_info=dtm_info,
            farm_gdf=farm_gdf,
            elevation=elevation,
            slope_degrees=slope_result.slope_degrees,
            surface_area_pixel=last_sa.surface_area_pixel,
            farm_mask=last_sa.farm_mask,
        )

    # ── Charts tab ────────────────────────────────────────────────────────────
    with tab_charts:
        st.markdown("### 📈 Area Comparison")
        from PIL import Image
        import io as _io
        img = Image.open(_io.BytesIO(chart_bytes))
        st.image(img, use_container_width=True)

        st.markdown("---")
        st.markdown("### 📊 Slope Class Distribution")
        render_slope_class_chart(primary_stats)

    # ── Export tab ────────────────────────────────────────────────────────────
    with tab_export:
        render_export_panel(
            stats_list=all_stats,
            farm_gdf=farm_gdf,
            slope_degrees=slope_result.slope_degrees,
            surface_area_pixel=last_sa.surface_area_pixel,
            dtm_info=dtm_info,
            qc_result=primary_qc,
            chart_bytes=chart_bytes,
        )

else:
    # ── Welcome screen ─────────────────────────────────────────────────────────
    with tab_dash:
        st.markdown(
            """
            <div style='
                text-align:center;
                padding: 60px 20px;
                color: #7f8c8d;
            '>
              <div style='font-size: 4rem;'>🛩️</div>
              <h2 style='color:#1A3A5C; font-weight:700; margin-top:12px;'>
                Welcome to the PCIC Farm Area Analyzer
              </h2>
              <p style='font-size:1rem; max-width:560px; margin:12px auto 0;'>
                Upload your <strong>Drone DTM</strong> and <strong>Farm Boundary</strong>
                using the sidebar, then click <strong>▶ Run Analysis</strong> to begin.
              </p>
              <br>
              <div style='display:flex; justify-content:center; gap:24px; flex-wrap:wrap;
                           font-size:0.88rem; color:#5D6D7E;'>
                <span>📐 Planimetric Area</span>
                <span>🏔️ 3D Surface Area</span>
                <span>📊 Slope Analysis</span>
                <span>🗺️ Interactive Map</span>
                <span>📤 Multi-format Export</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
