# =============================================================================
# config.py
# PCIC Drone 3D Farm Area Analyzer — Application Configuration
# =============================================================================

# ---------------------------------------------------------------------------
# Application identity
# ---------------------------------------------------------------------------
APP_NAME = "PCIC Drone 3D Farm Area Analyzer"
APP_SUBTITLE = "Geospatial Area Analysis for Insurance Validation"
ORGANIZATION = "Philippine Crop Insurance Corporation (PCIC)"

# ---------------------------------------------------------------------------
# Default / recommended CRS for PCIC Region 10
# ---------------------------------------------------------------------------
DEFAULT_EPSG = 32651
DEFAULT_CRS_NAME = "WGS 84 / UTM Zone 51N"

# ---------------------------------------------------------------------------
# Slope class boundaries (in percent)
# Based on Bureau of Soils and Water Management (BSWM) classification
# ---------------------------------------------------------------------------
SLOPE_CLASSES = [
    {"label": "0–8%",   "min": 0,   "max": 8,    "color": "#2ecc71"},
    {"label": "8–18%",  "min": 8,   "max": 18,   "color": "#f1c40f"},
    {"label": "18–30%", "min": 18,  "max": 30,   "color": "#e67e22"},
    {"label": ">30%",   "min": 30,  "max": None,  "color": "#e74c3c"},
]

# ---------------------------------------------------------------------------
# Quality-control thresholds
# ---------------------------------------------------------------------------
QC_NODATA_WARNING_THRESHOLD = 0.05   # 5 % NoData → WARNING
QC_NODATA_FAIL_THRESHOLD    = 0.20   # 20 % NoData → FAIL
QC_EXTREME_SLOPE_DEG        = 85.0   # Degrees — flag extreme slope pixels
QC_EXTREME_SLOPE_FRAC_WARN  = 0.01   # >1 % extreme pixels → WARNING
QC_EXTREME_SLOPE_FRAC_FAIL  = 0.50   # >50 % extreme pixels → FAIL
QC_MIN_COS_SLOPE            = 1e-6   # Protect against divide-by-zero

# ---------------------------------------------------------------------------
# Output folder names
# ---------------------------------------------------------------------------
OUTPUT_FOLDERS = {
    "dtm":            "01_DTM",
    "waypoints":      "02_Waypoints",
    "farm_polygon":   "03_Farm_Polygon",
    "slope":          "04_Slope",
    "surface_raster": "05_Surface_Area_Raster",
    "zonal_stats":    "06_Zonal_Statistics",
    "final_output":   "07_Final_Output",
}

# ---------------------------------------------------------------------------
# Rasterization default
# ---------------------------------------------------------------------------
DEFAULT_ALL_TOUCHED = False   # pixel-center inclusion by default

# ---------------------------------------------------------------------------
# Supported file types
# ---------------------------------------------------------------------------
VECTOR_EXTENSIONS = [".gpkg", ".geojson", ".shp"]
RASTER_EXTENSIONS = [".tif", ".tiff"]
WAYPOINT_EXTENSIONS = [".csv", ".gpkg", ".geojson", ".shp"]
