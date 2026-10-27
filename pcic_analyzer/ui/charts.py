# =============================================================================
# ui/charts.py
# Comparison bar chart and slope-class distribution chart
# =============================================================================
from __future__ import annotations

import io

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import streamlit as st

from config import SLOPE_CLASSES


# Colour palette
BLUE_PLAN  = "#2980B9"
GREEN_SURF = "#27AE60"
DARK_BG    = "#FAFBFC"
GRID_COLOR = "#ECF0F1"


def render_area_comparison_chart(stats_list: list) -> bytes:
    """
    Side-by-side grouped bar chart: Planimetric vs 3D Surface Area per farm.

    Returns
    -------
    bytes — PNG image bytes (for PDF embedding and display)
    """
    farm_ids   = [s.farm_id for s in stats_list]
    plane_vals = [s.plane_area_ha for s in stats_list]
    surf_vals  = [s.surface_area_ha for s in stats_list]

    n = len(farm_ids)
    x = np.arange(n)
    width = 0.38

    fig, ax = plt.subplots(figsize=(max(6, n * 1.8), 5), facecolor=DARK_BG)
    ax.set_facecolor(DARK_BG)

    bars1 = ax.bar(x - width / 2, plane_vals, width, label="Planimetric Area",
                   color=BLUE_PLAN, zorder=3, edgecolor="white", linewidth=0.5)
    bars2 = ax.bar(x + width / 2, surf_vals,  width, label="3D Surface Area",
                   color=GREEN_SURF, zorder=3, edgecolor="white", linewidth=0.5)

    # Value labels on bars
    for bar in bars1:
        _bar_label(ax, bar)
    for bar in bars2:
        _bar_label(ax, bar)

    ax.set_xticks(x)
    ax.set_xticklabels(farm_ids, fontsize=9)
    ax.set_ylabel("Area (ha)", fontsize=10)
    ax.set_title("Planimetric vs 3D Surface Area", fontsize=13, fontweight="bold",
                 color="#1A3A5C", pad=14)
    ax.yaxis.grid(True, color=GRID_COLOR, zorder=0)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(framealpha=0.8)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def render_slope_class_chart(stats) -> None:
    """
    Grouped bar chart: planimetric and 3D surface area per slope class.
    Renders directly into Streamlit.
    """
    labels     = [sc.label for sc in stats.slope_classes]
    plane_vals = [sc.plane_area_ha for sc in stats.slope_classes]
    surf_vals  = [sc.surface_area_ha for sc in stats.slope_classes]
    colors     = [cls["color"] for cls in SLOPE_CLASSES]

    x     = np.arange(len(labels))
    width = 0.38

    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor=DARK_BG)
    ax.set_facecolor(DARK_BG)

    bars_p = ax.bar(x - width / 2, plane_vals, width, label="Planimetric",
                    color=BLUE_PLAN, zorder=3, edgecolor="white", linewidth=0.5)
    bars_s = ax.bar(x + width / 2, surf_vals,  width, label="3D Surface",
                    color=GREEN_SURF, zorder=3, edgecolor="white", linewidth=0.5)

    for bar in bars_p:
        _bar_label(ax, bar, fmt="{:.4f}")
    for bar in bars_s:
        _bar_label(ax, bar, fmt="{:.4f}")

    # Colour-coded x-tick labels
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    for tick, col in zip(ax.get_xticklabels(), colors):
        tick.set_color(col)
        tick.set_fontweight("bold")

    ax.set_ylabel("Area (ha)", fontsize=10)
    ax.set_title("Area by Slope Class", fontsize=13, fontweight="bold",
                 color="#1A3A5C", pad=14)
    ax.yaxis.grid(True, color=GRID_COLOR, zorder=0)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(framealpha=0.8)

    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def _bar_label(ax, bar, fmt: str = "{:.4f}") -> None:
    """Add a value label above a bar."""
    h = bar.get_height()
    if h > 0:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h + h * 0.01,
            fmt.format(h),
            ha="center", va="bottom",
            fontsize=7, color="#2C3E50",
        )
