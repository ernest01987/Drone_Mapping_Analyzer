# =============================================================================
# ui/dashboard.py
# Results dashboard: QC badge, metric cards, terrain stats, slope classes
# =============================================================================
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import SLOPE_CLASSES
from core.quality_control import QCStatus


_QC_STYLE = {
    QCStatus.PASS:    ("🟢", "#27AE60", "#EAF6EF"),
    QCStatus.WARNING: ("🟡", "#E67E22", "#FEF9E7"),
    QCStatus.FAIL:    ("🔴", "#E74C3C", "#FDEDEC"),
}


def render_dtm_info(dtm_info) -> None:
    """Show a collapsible DTM information panel."""
    with st.expander("📋 DTM Information", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**CRS:** {dtm_info.crs_name}")
            st.markdown(f"**EPSG:** {dtm_info.epsg}")
            st.markdown(f"**Projected:** {'✅ Yes' if dtm_info.is_projected else '❌ No'}")
            st.markdown(f"**Units:** {dtm_info.units}")
        with col2:
            st.markdown(f"**Pixel Width:** {dtm_info.pixel_width:.6f} m")
            st.markdown(f"**Pixel Height:** {dtm_info.pixel_height:.6f} m")
            st.markdown(f"**Pixel Area:** {dtm_info.pixel_width * dtm_info.pixel_height:.8f} m²")
            st.markdown(f"**Raster Size:** {dtm_info.width} × {dtm_info.height} px")
        st.markdown(
            f"**Elevation Range:** {dtm_info.min_elevation:.2f} m – "
            f"{dtm_info.max_elevation:.2f} m  |  "
            f"**Mean:** {dtm_info.mean_elevation:.2f} m"
        )
        st.markdown(
            f"**Bounds:** W {dtm_info.bounds.left:.2f}, S {dtm_info.bounds.bottom:.2f}, "
            f"E {dtm_info.bounds.right:.2f}, N {dtm_info.bounds.top:.2f}"
        )


def render_qc_badge(qc_result) -> None:
    """Render a coloured QC status banner with expandable message list."""
    icon, color, bg = _QC_STYLE.get(
        qc_result.status, ("⚪", "#7f8c8d", "#F4F6F9")
    )
    st.markdown(
        f"""
        <div style='
            background:{bg};
            border-left: 6px solid {color};
            border-radius: 6px;
            padding: 12px 18px;
            margin-bottom: 12px;
        '>
          <span style='font-size:1.2rem; font-weight:700; color:{color};'>
            {icon} Quality Control — {qc_result.status.value}
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("QC Details", expanded=(qc_result.status != QCStatus.PASS)):
        for msg in qc_result.messages:
            if msg.startswith("[OK]"):
                st.success(msg)
            elif msg.startswith("[WARNING]"):
                st.warning(msg)
            elif msg.startswith("[FAIL]"):
                st.error(msg)
            else:
                st.info(msg)


def render_metric_cards(stats) -> None:
    """Six primary metric cards."""
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            "📐 Planimetric Area",
            f"{stats.plane_area_ha:.6f} ha",
            f"{stats.plane_area_m2:,.2f} m²",
        )
    with c2:
        st.metric(
            "🏔️ 3D Surface Area",
            f"{stats.surface_area_ha:.6f} ha",
            f"{stats.surface_area_m2:,.2f} m²",
        )
    with c3:
        st.metric(
            "📊 Area Difference",
            f"{stats.area_difference_ha:.6f} ha",
            f"{stats.area_difference_ha * 10000:,.2f} m²",
        )

    c4, c5, c6 = st.columns(3)
    with c4:
        delta_color = "normal" if stats.area_increase_pc >= 0 else "inverse"
        st.metric(
            "📈 Terrain Increase",
            f"{stats.area_increase_pc:.4f} %",
            delta=None,
        )
    with c5:
        st.metric("⛰️ Mean Slope", f"{stats.mean_slope_deg:.2f}°")
    with c6:
        st.metric("📉 Mean Slope (%)", f"{stats.mean_slope_pc:.2f}%")


def render_terrain_stats(stats) -> None:
    """Terrain statistics table."""
    st.markdown("##### Terrain Statistics")
    data = {
        "Parameter": [
            "Mean Slope (°)", "Min Slope (°)", "Max Slope (°)", "Median Slope (°)",
            "Mean Slope (%)",
            "Mean Elevation (m)", "Min Elevation (m)", "Max Elevation (m)",
            "Valid DTM Pixels", "Mean Cell Contribution (m²)",
        ],
        "Value": [
            f"{stats.mean_slope_deg:.4f}",
            f"{stats.min_slope_deg:.4f}",
            f"{stats.max_slope_deg:.4f}",
            f"{stats.median_slope_deg:.4f}",
            f"{stats.mean_slope_pc:.4f}",
            f"{stats.mean_elevation_m:.2f}",
            f"{stats.min_elevation_m:.2f}",
            f"{stats.max_elevation_m:.2f}",
            f"{stats.dtm_count:,}",
            f"{stats.dtm_mean:.8f}",
        ],
    }
    st.dataframe(
        pd.DataFrame(data),
        use_container_width=True,
        hide_index=True,
    )


def render_slope_class_table(stats) -> None:
    """Slope class breakdown table."""
    st.markdown("##### Slope Class Distribution")
    rows = []
    total_plane = sum(sc.plane_area_ha for sc in stats.slope_classes)
    total_surf  = sum(sc.surface_area_ha for sc in stats.slope_classes)
    for sc in stats.slope_classes:
        plane_pc = (sc.plane_area_ha / total_plane * 100) if total_plane else 0
        surf_pc  = (sc.surface_area_ha / total_surf * 100) if total_surf else 0
        rows.append({
            "Slope Class":          sc.label,
            "Planimetric (ha)":     f"{sc.plane_area_ha:.6f}",
            "Plan. %":              f"{plane_pc:.1f}%",
            "3D Surface (ha)":      f"{sc.surface_area_ha:.6f}",
            "Surf. %":              f"{surf_pc:.1f}%",
        })
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )


def render_comparison_table(all_stats: list) -> None:
    """Multi-farm comparison table."""
    st.markdown("##### Multi-Farm Comparison")
    rows = []
    for s in all_stats:
        rows.append({
            "Farm_ID":            s.farm_id,
            "Plane_area_ha":      round(s.plane_area_ha, 6),
            "Surface_area_ha":    round(s.surface_area_ha, 6),
            "Area_Difference_ha": round(s.area_difference_ha, 6),
            "Area_Increase_pc":   round(s.area_increase_pc, 4),
            "Mean_Slope_deg":     round(s.mean_slope_deg, 4),
            "Mean_Slope_pc":      round(s.mean_slope_pc, 4),
            "dtm_count":          s.dtm_count,
        })
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )
