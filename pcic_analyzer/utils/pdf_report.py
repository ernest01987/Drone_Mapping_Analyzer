# =============================================================================
# utils/pdf_report.py
# Generate a PDF analysis report using reportlab
# =============================================================================
from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config import APP_NAME, APP_SUBTITLE, ORGANIZATION


# Colour palette
PCIC_BLUE   = colors.HexColor("#1A3A5C")
PCIC_GOLD   = colors.HexColor("#D4A017")
LIGHT_GRAY  = colors.HexColor("#F4F6F9")
MID_GRAY    = colors.HexColor("#95A5A6")
DARK_TEXT   = colors.HexColor("#2C3E50")
GREEN_OK    = colors.HexColor("#27AE60")
ORANGE_WARN = colors.HexColor("#E67E22")
RED_FAIL    = colors.HexColor("#E74C3C")


def generate_pdf_report(
    stats,          # TerrainStatistics
    qc_result,      # QCResult
    farm_id: str,
    chart_bytes: Optional[bytes] = None,   # PNG bytes of comparison chart
) -> bytes:
    """
    Build a PDF analysis report and return it as bytes.

    Parameters
    ----------
    stats : TerrainStatistics
    qc_result : QCResult
    farm_id : str
    chart_bytes : bytes, optional
        PNG image of the area comparison chart.

    Returns
    -------
    bytes — PDF file content
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    story  = []

    # ── Header ────────────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        textColor=PCIC_BLUE,
        fontSize=18,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        textColor=PCIC_GOLD,
        fontSize=11,
        spaceAfter=2,
    )
    normal = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        textColor=DARK_TEXT,
        fontSize=10,
        leading=14,
    )
    small = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        textColor=MID_GRAY,
        fontSize=8,
    )

    story.append(Paragraph(APP_NAME, title_style))
    story.append(Paragraph(APP_SUBTITLE, subtitle_style))
    story.append(Paragraph(ORGANIZATION, small))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=PCIC_BLUE))
    story.append(Spacer(1, 0.3 * cm))

    # Report metadata
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(f"<b>Farm ID:</b> {farm_id}", normal))
    story.append(Paragraph(f"<b>Generated:</b> {now}", normal))
    story.append(Spacer(1, 0.4 * cm))

    # ── QC Status ─────────────────────────────────────────────────────────────
    story.append(Paragraph("<b>Quality Control</b>", styles["Heading2"]))
    qc_color = {
        "PASS": GREEN_OK, "WARNING": ORANGE_WARN, "FAIL": RED_FAIL
    }.get(qc_result.status.value, MID_GRAY)

    qc_table = Table(
        [["QC Status", qc_result.status.value]],
        colWidths=[4 * cm, 14 * cm],
    )
    qc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), PCIC_BLUE),
        ("BACKGROUND", (1, 0), (1, 0), qc_color),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 12),
        ("ALIGN",     (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GRAY]),
        ("BOX",       (0, 0), (-1, -1), 0.5, MID_GRAY),
    ]))
    story.append(qc_table)
    story.append(Spacer(1, 0.2 * cm))

    for msg in qc_result.messages:
        story.append(Paragraph(f"• {msg}", small))
    story.append(Spacer(1, 0.4 * cm))

    # ── Area Results ──────────────────────────────────────────────────────────
    story.append(Paragraph("<b>Area Results</b>", styles["Heading2"]))

    area_data = [
        ["Metric", "Value (m²)", "Value (ha)"],
        ["Planimetric Area",
            f"{stats.plane_area_m2:,.2f}",
            f"{stats.plane_area_ha:.6f}"],
        ["3D Surface Area",
            f"{stats.surface_area_m2:,.2f}",
            f"{stats.surface_area_ha:.6f}"],
        ["Area Difference",
            f"{stats.area_difference_ha * 10000:,.2f}",
            f"{stats.area_difference_ha:.6f}"],
        ["Area Increase (%)", "—", f"{stats.area_increase_pc:.4f} %"],
    ]
    area_table = _build_table(area_data)
    story.append(area_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── Terrain Statistics ────────────────────────────────────────────────────
    story.append(Paragraph("<b>Terrain Statistics</b>", styles["Heading2"]))

    terrain_data = [
        ["Parameter", "Value"],
        ["Mean Slope (°)",    f"{stats.mean_slope_deg:.2f}°"],
        ["Min Slope (°)",     f"{stats.min_slope_deg:.2f}°"],
        ["Max Slope (°)",     f"{stats.max_slope_deg:.2f}°"],
        ["Median Slope (°)",  f"{stats.median_slope_deg:.2f}°"],
        ["Mean Slope (%)",    f"{stats.mean_slope_pc:.2f}%"],
        ["Mean Elevation (m)", f"{stats.mean_elevation_m:.2f} m"],
        ["Min Elevation (m)",  f"{stats.min_elevation_m:.2f} m"],
        ["Max Elevation (m)",  f"{stats.max_elevation_m:.2f} m"],
        ["Valid DTM Pixels",   f"{stats.dtm_count:,}"],
    ]
    story.append(_build_table(terrain_data))
    story.append(Spacer(1, 0.4 * cm))

    # ── Slope Classes ─────────────────────────────────────────────────────────
    story.append(Paragraph("<b>Slope Class Distribution</b>", styles["Heading2"]))
    sc_data = [["Slope Class", "Planimetric Area (ha)", "3D Surface Area (ha)"]]
    for sc in stats.slope_classes:
        sc_data.append([sc.label, f"{sc.plane_area_ha:.6f}", f"{sc.surface_area_ha:.6f}"])
    story.append(_build_table(sc_data))
    story.append(Spacer(1, 0.4 * cm))

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=MID_GRAY))
    story.append(Spacer(1, 0.2 * cm))
    disclaimer = (
        "<i>This report presents both planimetric and 3D terrain surface area "
        "measurements for technical review. Neither measurement is automatically "
        "declared the official insured area. Results are produced by the "
        f"{APP_NAME} and are intended to support validation of insured "
        "agricultural land on sloping terrain.</i>"
    )
    story.append(Paragraph(disclaimer, small))

    doc.build(story)
    return buf.getvalue()


def _build_table(data: list) -> Table:
    col_count = len(data[0])
    col_width = 17 * cm / col_count
    tbl = Table(data, colWidths=[col_width] * col_count, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  PCIC_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("GRID",          (0, 0), (-1, -1), 0.3, MID_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tbl
