# PCIC Drone 3D Farm Area Analyzer

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B.svg)](https://streamlit.io/)
[![Geospatial](https://img.shields.io/badge/GIS-Rasterio%20%7C%20GeoPandas-2ecc71.svg)](https://geopandas.org/)

An automated geospatial web application developed for the **Philippine Crop Insurance Corporation (PCIC)** to calculate and compare 2D planimetric (flat) farm area against 3D terrain surface area derived from high-resolution drone Digital Terrain Models (DTMs).

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technical Architecture](#technical-architecture)
- [Requirements](#requirements)
- [Installation (Windows)](#installation-windows)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [Input Data Requirements](#input-data-requirements)
- [Moving to Another Computer](#moving-to-another-computer)
- [License](#license)

---

## Overview

In hilly and mountainous agricultural regions, traditional flat 2D maps (planimetric measurements) underestimate actual farm surface area, often leading to discrepancies in crop insurance underwriting, damage assessment, and claim settlements.

The **PCIC Drone 3D Farm Area Analyzer** bridges this gap by:
1. Ingesting drone-derived Digital Terrain Models (DTM) and farm parcel boundaries.
2. Deriving pixel-by-pixel terrain slopes using Horn's algorithm and surface geometric corrections.
3. Accurately computing the true 3D continuous surface area over complex micro-topography.
4. Quantifying the area difference and percentage increase caused by slope.
5. Classifying terrain according to official Bureau of Soils and Water Management (BSWM) slope criteria.
6. Generating quality control metrics and comprehensive PDF reports for insurance audits.

---

## Key Features

- **DTM Processing & Validation:**
  - Automated GeoTIFF header parsing (CRS, pixel resolution, bounds, NoData detection).
  - Validation of projected coordinate systems (meters) required for metric area calculations.
  - Recommended default coordinate system: WGS 84 / UTM Zone 51N (`EPSG:32651`) for Philippine Region 10.

- **Flexible Farm Boundary Ingestion:**
  - Polygon boundary upload (`.gpkg`, `.geojson`, `.shp`).
  - Waypoint table upload (`.csv`, `.gpkg`, `.geojson`, `.shp`) with automatic convex hull or coordinate sequencing.
  - Automatic CRS alignment and boundary re-projection to match the DTM.

- **Topographic & Surface Area Engine:**
  - 3D Surface Area calculation: $\text{Surface Area} = \frac{\Delta x \times \Delta y}{\cos(\theta)}$
  - Horn's 8-neighbor gradient algorithm for robust slope calculations.
  - Zonal statistics aggregated across individual farm parcels.

- **BSWM Slope Classification:**
  - `0–8%`: Level to undulating
  - `8–18%`: Rolling
  - `18–30%`: Hilly
  - `>30%`: Steep / Mountainous

- **Interactive UI & Visualizations:**
  - Built with Streamlit featuring a high-contrast, responsive dashboard.
  - Dual-layer interactive maps (Esri World Imagery satellite basemap with overlay boundaries and slope gradients).
  - Area comparison bar charts and slope class distribution breakdowns.

- **Auditable Quality Control & Reporting:**
  - Automated QC indicators (NoData percentage, boundary-DTM overlap, extreme slope anomaly detection).
  - Export capabilities: summary CSV, analysis GeoPackage (`.gpkg`), high-resolution slope GeoTIFF, and multi-page audit-ready PDF reports.

---

## Requirements

- **Operating System:** Windows 10 / 11 (64-bit) (or Linux/macOS)
- **Python Version:** **Python 3.12** (Recommended: 3.12.x)
- **Hardware:** 8 GB RAM minimum (16 GB recommended for high-resolution drone GeoTIFFs > 500 MB)

---

## Installation (Windows)

Follow these steps to set up the environment on Windows:

```powershell
# 1. Clone the repository
git clone https://github.com/ernest01987/Drone_Mapping_Analyzer.git
cd Drone_Mapping_Analyzer

# 2. Create the dedicated virtual environment
python -m venv pcic_env

# 3. Activate the virtual environment
pcic_env\Scripts\activate

# 4. Upgrade pip
python -m pip install --upgrade pip

# 5. Install dependencies
pip install -r requirements.txt
```

---

## Running the Application

### Option A: Via Command Line (Recommended)

From the project root directory with the virtual environment activated:

```powershell
pcic_env\Scripts\activate
streamlit run pcic_analyzer/app.py
```

### Option B: One-Click Windows Launcher

Double-click the included batch script in the root directory:

```bat
Launch_PCIC_Analyzer.bat
```

The script automatically detects the virtual environment and launches Streamlit in your default web browser at `http://localhost:8501`.

---

## Project Structure

```text
├── .streamlit/
│   └── config.toml             # Streamlit server and theme configurations
├── .vscode/
│   └── settings.json           # Portable workspace settings for VS Code
├── pcic_analyzer/              # Main application source code
│   ├── .streamlit/
│   │   └── config.toml         # App-level Streamlit settings
│   ├── core/                   # Geospatial processing core
│   │   ├── boundary.py         # Boundary vector and waypoint parser
│   │   ├── dtm_loader.py       # Rasterio GeoTIFF reader and CRS validator
│   │   ├── pixel_area.py       # Planar pixel dimension calculator
│   │   ├── planimetric.py      # 2D horizontal area calculator
│   │   ├── quality_control.py  # Integrity checks (NoData, extreme slope, overlap)
│   │   ├── slope.py            # Horn's slope algorithm in degrees & percent
│   │   ├── statistics.py       # Zonal summary and slope class distribution
│   │   └── surface_area.py     # 3D surface area integration
│   ├── ui/                     # Streamlit frontend presentation modules
│   │   ├── charts.py           # Matplotlib area and slope charts
│   │   ├── dashboard.py        # KPI metric cards, tables, and QC badges
│   │   ├── export.py           # Exporters (CSV, GeoPackage, PDF, GeoTIFF)
│   │   ├── map_view.py         # Folium / Leaflet interactive GIS map
│   │   └── sidebar.py          # Input upload widgets and analysis parameters
│   ├── utils/                  # Shared utilities
│   │   ├── pdf_report.py       # ReportLab PDF report generation
│   │   └── raster_utils.py     # Raster mask and memory-file utilities
│   ├── app.py                  # Streamlit application entry point
│   ├── config.py               # Application constants, CRS defaults, and thresholds
│   └── requirements.txt        # Application package requirements
├── .gitignore                  # Git ignore rules for venvs, rasters, and temp files
├── .python-version             # Python version pin (3.12.10)
├── Launch_PCIC_Analyzer.bat    # Portable Windows double-click launcher
├── pyrefly.toml                # Static analyzer configuration
├── pyrightconfig.json          # Type checker configuration
├── README.md                   # Project documentation
└── requirements.txt            # Root pip dependencies
```

---

## Input Data Requirements

The application processes user-uploaded datasets during the session. Ensure your files adhere to the following specifications:

| Input File | Supported Formats | Required Attributes / Properties |
| :--- | :--- | :--- |
| **Digital Terrain Model (DTM)** | `.tif`, `.tiff` | Single-band float32/int16 raster representing bare earth elevation. Coordinates **must be projected in meters** (e.g., UTM Zone 51N `EPSG:32651`). Geographic degrees (WGS84 `EPSG:4326`) are rejected because horizontal and vertical units must match for slope calculations. |
| **Farm Boundary Polygon** | `.gpkg`, `.geojson`, `.shp` | Single or multi-polygon defining farm parcel boundaries. Z-coordinates (if present) are automatically flattened. |
| **Boundary Waypoints** | `.csv`, `.gpkg`, `.geojson`, `.shp` | Point data. If CSV: must contain coordinate columns (e.g., `X`/`Y`, `Easting`/`Northing`, or `Longitude`/`Latitude`) and an optional parcel identifier. Points are closed into a polygon automatically. |

---

## Moving to Another Computer

To replicate this environment on another Windows computer:

1. **Prerequisites:** Install [Python 3.12](https://www.python.org/downloads/) (ensure **"Add python.exe to PATH"** is checked during installation) and [Git](https://git-scm.com/download/win).
2. **Clone the repository:**
   ```powershell
   git clone https://github.com/ernest01987/Drone_Mapping_Analyzer.git
   cd Drone_Mapping_Analyzer
   ```
3. **Setup environment:**
   ```powershell
   python -m venv pcic_env
   pcic_env\Scripts\activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. **Run the analyzer:**
   ```powershell
   streamlit run pcic_analyzer/app.py
   ```
   Or double-click `Launch_PCIC_Analyzer.bat`.

---

## Large Files & Data Storage Note

- Drone DTM rasters and orthomosaics can exceed several gigabytes. In accordance with standard repository practices, raw GeoTIFF files and processing outputs are intentionally excluded via `.gitignore` to keep the repository lightweight and fast to clone.
- If your team requires tracking standardized benchmark sample GeoTIFF datasets in Git, consider using **Git LFS (Large File Storage)** or hosting sample datasets in a dedicated cloud storage bucket (e.g., Google Cloud Storage or AWS S3).
