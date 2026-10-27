# =============================================================================
# core/planimetric.py
# Step 4 — Planimetric (horizontal) area from the farm polygon
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
from shapely.geometry import Polygon


@dataclass
class PlanimetricResult:
    farm_id: str
    plane_area_m2: float
    plane_area_ha: float


def compute_planimetric_area(
    gdf: gpd.GeoDataFrame,
    farm_id_col: str = "Farm_ID",
) -> list[PlanimetricResult]:
    """
    Calculate planimetric (horizontal, projected) area for each farm polygon.

    The CRS must already be projected (metres).  This uses ``polygon.area``
    directly — NOT pixel counts.

    Parameters
    ----------
    gdf : GeoDataFrame
        Farm boundary layer in a projected metric CRS.
    farm_id_col : str
        Column that identifies each farm.

    Returns
    -------
    list[PlanimetricResult]
        One result per row in the GeoDataFrame.
    """
    results = []
    for _, row in gdf.iterrows():
        geom: Polygon = row.geometry
        plane_area_m2 = float(geom.area)
        plane_area_ha = plane_area_m2 / 10_000.0

        farm_id = str(row.get(farm_id_col, row.name))
        results.append(
            PlanimetricResult(
                farm_id=farm_id,
                plane_area_m2=plane_area_m2,
                plane_area_ha=plane_area_ha,
            )
        )
    return results
