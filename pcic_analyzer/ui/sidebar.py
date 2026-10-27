# =============================================================================
# ui/sidebar.py
# Sidebar: file uploads, settings, and run button
# =============================================================================
from __future__ import annotations

import streamlit as st

from config import APP_NAME, DEFAULT_CRS_NAME, DEFAULT_EPSG


def render_sidebar() -> dict:
    """
    Render the sidebar widgets and return user selections as a dict.

    Returns
    -------
    dict with keys:
        dtm_file, boundary_method, polygon_file, waypoint_file,
        farm_id_field, sequence_field, all_touched, run_clicked
    """
    with st.sidebar:
        # ── Branding ──────────────────────────────────────────────────────────
        st.markdown(
            """
            <div style='text-align:center; padding-bottom: 12px;'>
              <span style='font-size:1.4rem; font-weight:800;
                           color:#1A3A5C; letter-spacing:0.5px;'>
                🛩️ PCIC
              </span><br>
              <span style='font-size:0.75rem; color:#7f8c8d;'>
                Drone 3D Farm Area Analyzer
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        # ── Step 1: DTM ────────────────────────────────────────────────────────
        st.markdown("#### 📁 Step 1 — Upload DTM")
        dtm_file = st.file_uploader(
            "Drone DTM (GeoTIFF)",
            type=["tif", "tiff"],
            key="dtm_uploader",
            help="Upload a projected GeoTIFF DTM. Recommended CRS: "
                 f"EPSG:{DEFAULT_EPSG} ({DEFAULT_CRS_NAME})",
        )

        # ── Step 3: Farm Boundary ─────────────────────────────────────────────
        st.markdown("#### 🗺️ Step 3 — Farm Boundary")
        boundary_method = st.radio(
            "Boundary input method",
            ["Method A — Upload Polygon", "Method B — Upload Waypoints"],
            key="boundary_method",
            label_visibility="collapsed",
        )

        polygon_file  = None
        waypoint_file = None
        farm_id_field = None
        seq_field     = None
        waypoint_columns: list[str] = []

        if boundary_method.startswith("Method A"):
            polygon_file = st.file_uploader(
                "Farm Polygon (.gpkg / .geojson / .shp)",
                type=["gpkg", "geojson", "json", "shp"],
                key="polygon_uploader",
            )

        else:  # Method B
            waypoint_file = st.file_uploader(
                "Waypoints (.csv / .gpkg / .geojson / .shp)",
                type=["csv", "gpkg", "geojson", "json", "shp"],
                key="waypoint_uploader",
            )
            if waypoint_file:
                # Column names are populated after the file is loaded in app.py;
                # we use session_state to pass them back here.
                waypoint_columns = st.session_state.get("waypoint_columns", [])
                if waypoint_columns:
                    farm_id_field = st.selectbox(
                        "Farm ID field",
                        options=waypoint_columns,
                        key="farm_id_field",
                    )
                    seq_field = st.selectbox(
                        "Sequence / order field",
                        options=waypoint_columns,
                        key="seq_field",
                    )
                else:
                    st.info("Upload the waypoint file to select fields.")

        # ── Settings ─────────────────────────────────────────────────────────
        st.markdown("#### ⚙️ Settings")
        all_touched = st.checkbox(
            "Include boundary-touching pixels",
            value=False,
            key="all_touched",
            help=(
                "When enabled, raster pixels that touch the farm boundary edge "
                "are included in the calculation (rasterio all_touched=True). "
                "Default: pixel-centre inclusion only."
            ),
        )

        st.divider()

        # ── Run ──────────────────────────────────────────────────────────────
        run_clicked = st.button(
            "▶ Run Analysis",
            type="primary",
            use_container_width=True,
            key="run_btn",
        )

    return {
        "dtm_file":        dtm_file,
        "boundary_method": boundary_method,
        "polygon_file":    polygon_file,
        "waypoint_file":   waypoint_file,
        "farm_id_field":   farm_id_field,
        "sequence_field":  seq_field,
        "all_touched":     all_touched,
        "run_clicked":     run_clicked,
    }
