"""Configuration for IGNIS-Sim Kalimantan.

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
# A 2 deg x 2 deg box centered here is about 222 km x 222 km; the grid
# resolution (~0.035 deg) gives ~4 km cells.
_MIN_LON: float = 112.5
_MIN_LAT: float = -3.5
_MAX_LON: float = 114.5
_MAX_LAT: float = -1.5


def bounding_box() -> Tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) as a tuple."""
    return (_MIN_LON, _MIN_LAT, _MAX_LON, _MAX_LAT)


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


def cell_size_description() -> str:
    """Return a short human-readable description of the cell size."""
    approx_lat_m = _GRID_SPACING_DEG * _M_PER_DEG_LAT
    approx_lon_m = _GRID_SPACING_DEG * _M_PER_DEG_LAT * (
        1.0 / (1.0 + 0.0)  # rough; real longitude scaling depends on latitude
    )
    return (
        f"Grid spacing: {_GRID_SPACING_DEG} degrees (about "
        f"{approx_lat_m:.0f} m north-south)."
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
