"""Configuration for INSIGHT Kalimantan.

The demo bounding box is centered near Palangkaraya / Sebangau / Kahayan
peatland forest in Central Kalimantan, roughly 2 degrees longitude by 2 degrees
latitude, with a grid resolution of about 4 km x 4 km per cell.

All constants here are deliberately kept simple and transparent so the science
project can explain every number used in the CA and ML pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_RAW_DIR = _PROJECT_ROOT / "data" / "raw"
_DATA_PROCESSED_DIR = _PROJECT_ROOT / "data" / "processed"
_FIGURES_DIR = _PROJECT_ROOT / "figures"


def data_raw_dir() -> Path:
    _DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_RAW_DIR


def data_processed_dir() -> Path:
    _DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_PROCESSED_DIR()


def figures_dir() -> Path:
    _FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    return _FIGURES_DIR


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------

# Demo bounding box: Central Kalimantan around Palangkaraya / Sebangau / Kahayan.
# Coordinates in decimal degrees (WGS84).
#
# Palangkaraya is at approx 2.22 S, 113.90 E. The Sebangau and Kahayan
# peatland forests lie roughly between 112.5-114.5 E and 1.5-3.5 S.
# A ~2 deg x 2 deg box centered here is about 222 km x 222 km; the grid
# resolution (~0.035 deg) gives ~4 km cells.
_MIN_LON: float = 112.5
_MIN_LAT: float = -3.5
_MAX_LON: float = 114.5
_MAX_LAT: float = -1.5

# Cell grid aspect ratio (cols / rows). 1.0 keeps the demo square; larger
# values make the map wider (rectangle) so a sidebar can sit to the right
# without wasting vertical space.
_GRID_ASPECT: float = 1.6

# ---------------------------------------------------------------------------
# Kalimantan-wide map (expanded fire-risk view)
# ---------------------------------------------------------------------------

# Whole-of-Kalimantan bounding box (Borneo's Indonesian portion):
# approx 108.8E-119.1E, 4.2S-7.3N. Used only for the coarse Kalimantan-wide
# risk map; the CA demo still runs on the small Palangka Raya box above.
KALIMANTAN_BBOX: Tuple[float, float, float, float] = (108.8, -4.2, 119.1, 7.3)

# Coarse spacing for the Kalimantan-wide risk map (~16 km per cell) so the
# whole island renders quickly in the browser.
KALIMANTAN_SPACING_DEG: float = 0.15


def bounding_box() -> Tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) as a tuple."""
    return (_MIN_LON, _MIN_LAT, _MAX_LON, _MAX_LAT)


def grid_aspect() -> float:
    """Aspect ratio for the demo grid (cols / rows)."""
    return _GRID_ASPECT


# ---------------------------------------------------------------------------
# Grid resolution
# ---------------------------------------------------------------------------

# Target grid spacing in degrees. Approximately 4 km at this latitude.
# The grid is built by dividing the bounding box into equal steps of this size.
_GRID_SPACING_DEG: float = 0.035

# Approximate meters per degree of latitude at the equator, used only for
# documentation and rough cell size estimation.
_M_PER_DEG_LAT: float = 111_000.0

# Approximate meters per degree of longitude at the mid-latitude of the box.
# Used only for documentation; the CA itself works in index space.
_MID_LAT: float = (_MIN_LAT + _MAX_LAT) / 2.0
import math as _math
_M_PER_DEG_LON: float = _M_PER_DEG_LAT * _math.cos(_math.radians(abs(_MID_LAT)))


def grid_spacing_deg() -> float:
    return _GRID_SPACING_DEG


def grid_dims() -> Tuple[int, int]:
    """Return (n_rows, n_cols) for the demo grid given the bounding box.

    The box is split into equal steps of _GRID_SPACING_DEG; n_cols is scaled
    by _GRID_ASPECT so the resulting raster can be a rectangle instead of a
    square.
    """
    from math import ceil

    min_lon, min_lat, max_lon, max_lat = bounding_box()
    d = grid_spacing_deg()

    n_rows = max(1, ceil((max_lat - min_lat) / d))
    n_cols_base = max(1, ceil((max_lon - min_lon) / d))
    n_cols = max(1, ceil(n_cols_base * grid_aspect()))

    return (n_rows, n_cols)


def cell_size_description() -> str:
    """Return a short human-readable description of the cell size."""
    cell_km_lat = _GRID_SPACING_DEG * _M_PER_DEG_LAT / 1000.0
    cell_km_lon = _GRID_SPACING_DEG * _M_PER_DEG_LON / 1000.0
    return (
        f"Grid spacing: {_GRID_SPACING_DEG} degrees (about "
        f"{cell_km_lat:.1f} km north-south, {cell_km_lon:.1f} km east-west)."
    )


# ---------------------------------------------------------------------------
# OSM / Overpass
# ---------------------------------------------------------------------------

OVERPASS_ENDPOINT: str = "https://overpass-api.de/api/interpreter"

# OpenStreetMap tags of interest for the demo.
# These are used to build the fuel / settlement / water context for each cell.
OSM_LAND_COVER_TAGS = [
    "landuse",
    "natural",
    "leisure",
    "boundary",
    "waterway",
    "water",
    "place",
    "highway",
    "building",
]

OSM_SETTLEMENT_PLACE_TAGS = ["village", "hamlet", "town", "city"]


def osm_query_timeout() -> int:
    """Recommended Overpass query timeout in seconds."""
    return 60


# ---------------------------------------------------------------------------
# FIRMS / fire hotspots
# ---------------------------------------------------------------------------

FIRMS_SOURCE: str = "NASA FIRMS (MODIS/VIIRS)"

# Default FIRMS CSV filename when downloaded manually or via the download step.
FIRMS_DEFAULT_FILENAME: str = "firms_hotspots.csv"


def firms_data_path() -> Path:
    return data_raw_dir() / FIRMS_DEFAULT_FILENAME


# ---------------------------------------------------------------------------
# Wind / weather
# ---------------------------------------------------------------------------

# Wind source options: "static" for the built-in demo field, or "file" if you
# supply a CSV with per-day wind direction.
WIND_SOURCE: str = "static"

# Default demo wind direction in degrees, meteorological convention:
# 0 means wind FROM north (blowing southward), 90 means wind FROM east
# (blowing westward).
DEFAULT_WIND_DIR_DEG: float = 90.0


def default_wind_direction_deg() -> float:
    return DEFAULT_WIND_DIR_DEG


# ---------------------------------------------------------------------------
# Cellular Automaton parameters
# ---------------------------------------------------------------------------

# Base probability that a burning cell ignites a neighboring non-burning cell.
# This is deliberately small so the demo is stable and easy to explain.
CA_SPREAD_BASE: float = 0.15

# Extra spread multiplier when the neighbor lies roughly along the wind
# direction from the burning cell.
CA_WIND_ALIGNMENT_STRENGTH: float = 0.25

# Extra spread multiplier when the target cell is flagged as peat at risk.
CA_PEAT_INFLUENCE: float = 0.20

# Number of CA neighbor offsets (8-neighbor Moore neighborhood).
CA_NEIGHBOR_OFFSETS = (
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
)

# CA state labels.
CA_STATE_HEALTHY: str = "healthy"
CA_STATE_IGNITING: str = "igniting"
CA_STATE_BURNING: str = "burning"
CA_STATE_BURNED: str = "burned"
CA_STATE_PEAT_RISK: str = "peat_risk"

CA_STATES = (
    CA_STATE_HEALTHY,
    CA_STATE_IGNITING,
    CA_STATE_BURNING,
    CA_STATE_BURNED,
    CA_STATE_PEAT_RISK,
)


def ca_neighbors() -> Tuple[Tuple[int, int], ...]:
    return CA_NEIGHBOR_OFFSETS


# ---------------------------------------------------------------------------
# Machine learning parameters
# ---------------------------------------------------------------------------

ML_MODEL_TYPE: str = "random_forest"
ML_TEST_FRACTION: float = 0.2
ML_RANDOM_STATE: int = 42

# Number of days of recent hotspot history to use as features, for the demo.
ML_HOTSPOT_HISTORY_DAYS: int = 7


def ml_random_state() -> int:
    return ML_RANDOM_STATE


# Trained model artifacts (written by ``python -m src.train``).
_MODELS_DIR = _PROJECT_ROOT / "models"
MODEL_FILENAME: str = "risk_rf.joblib"
MODEL_METRICS_FILENAME: str = "risk_rf_metrics.json"


def models_dir() -> Path:
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return _MODELS_DIR


def model_path() -> Path:
    return _MODELS_DIR / MODEL_FILENAME


def model_metrics_path() -> Path:
    return _MODELS_DIR / MODEL_METRICS_FILENAME


# ---------------------------------------------------------------------------
# Mitigation thresholds
# ---------------------------------------------------------------------------

# If a burning cell is within this many grid steps of a settlement cell, the
# demo will surface mitigation advice for that settlement.
MITIGATION_RISK_RADIUS_CELLS: int = 2

# Distance in grid cells for "nearby rural area" detection.
MITIGATION_RURAL_RADIUS_CELLS: int = 3


def mitigation_risk_radius_cells() -> int:
    return MITIGATION_RISK_RADIUS_CELLS


def mitigation_rural_radius_cells() -> int:
    return MITIGATION_RURAL_RADIUS_CELLS
