"""FIRMS hotspot loading and labeling for IGNIS-Sim.

This module provides a small, explainable way to turn NASA FIRMS hotspot data
into per-cell labels for the demo bounding box.

For the science project, the hotspot data is the bridge between real observed
fire and the ML label we can train on.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from . import config


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Hotspot:
    """A single FIRMS hotspot record, normalized for the demo."""

    lon: float
    lat: float
    datetime: datetime
    confidence: float
    source: Optional[str] = None
    frp: Optional[float] = None


@dataclass
class FireDataset:
    """A small labeled dataset for the demo bounding box."""

    bounding_box: Tuple[float, float, float, float]
    hotspots: List[Hotspot]
    cell_grid: "CellGrid"
    labeled_days: List[datetime]
    labels: Dict[Tuple[int, int, str], int]  # (row, col, date_iso) -> 0/1


# ---------------------------------------------------------------------------
# Cell grid description (used by both fire_data and ca)
# ---------------------------------------------------------------------------


@dataclass
class CellGrid:
    """A simple rectangular grid over the bounding box."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    spacing_deg: float
    n_rows: int
    n_cols: int

    def cell_bounds(self, row: int, col: int) -> Tuple[float, float, float, float]:
        """Return (min_lon, min_lat, max_lon, max_lat) for a cell."""
        west = self.min_lon + col * self.spacing_deg
        east = west + self.spacing_deg
        south = self.min_lat + row * self.spacing_deg
        north = south + self.spacing_deg
        return (west, south, east, north)

    def lon_lat_to_row_col(self, lon: float, lat: float) -> Tuple[int, int]:
        """Map a lon/lat point to a (row, col) cell index."""
        if not (self.min_lon <= lon <= self.max_lon and self.min_lat <= lat <= self.max_lat):
            raise ValueError(f"Point ({lon}, {lat}) is outside the grid bounds.")
        col = int((lon - self.min_lon) / self.spacing_deg)
        row = int((lat - self.min_lat) / self.spacing_deg)
        col = max(0, min(self.n_cols - 1, col))
        row = max(0, min(self.n_rows - 1, row))
        return (row, col)

    def row_col_to_center(self, row: int, col: int) -> Tuple[float, float]:
        """Return the (lon, lat) center of a cell."""
        lon = self.min_lon + (col + 0.5) * self.spacing_deg
        lat = self.min_lat + (row + 0.5) * self.spacing_deg
        return (lon, lat)

    def iter_cells(self):
        """Iterate over all (row, col) indices."""
        for row in range(self.n_rows):
            for col in range(self.n_cols):
                yield (row, col)

    def all_indices(self) -> List[Tuple[int, int]]:
        return list(self.iter_cells())


# ---------------------------------------------------------------------------
# FIRMS CSV parsing
# ---------------------------------------------------------------------------

FIRMS_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_firms_datetime(value: str) -> datetime:
    value = value.strip()
    for fmt in (FIRMS_DATE_FORMAT, "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Could not parse FIRMS datetime: {value!r}")


def load_firms_csv(path: Path) -> pd.DataFrame:
    """Load a FIRMS CSV into a DataFrame with normalized columns."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    rename = {}
    for col in df.columns:
        low = col.strip().lower()
        if low in {"latitude", "lat"}:
            rename[col] = "lat"
        elif low in {"longitude", "lon", "long"}:
            rename[col] = "lon"
        elif low in {"datetime", "date", "acq_date", "track_date"}:
            rename[col] = "datetime"
        elif low in {"confidence", "conf"}:
            rename[col] = "confidence"
        elif low in {"frp", "fire_radiative_power"}:
            rename[col] = "frp"
        elif low in {"satellite", "instrument", "source"}:
            rename[col] = "source"
    df.rename(columns=rename, inplace=True)

    required = {"lat", "lon", "datetime"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"FIRMS CSV is missing required columns: {missing}")

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(50.0)

    df["datetime"] = df["datetime"].apply(_parse_firms_datetime)

    if "frp" in df.columns:
        df["frp"] = pd.to_numeric(df["frp"], errors="coerce")

    return df


# ---------------------------------------------------------------------------
# Hotspot extraction
# ---------------------------------------------------------------------------


def hotspots_in_bbox(
    df: pd.DataFrame,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    min_confidence: float = 50.0,
) -> List[Hotspot]:
    """Return hotspots inside the bounding box with at least the given confidence."""
    mask = (
        (df["lat"] >= min_lat)
        & (df["lat"] <= max_lat)
        & (df["lon"] >= min_lon)
        & (df["lon"] <= max_lon)
        & (df["confidence"] >= min_confidence)
    )
    kept = df[mask]
    hotspots: List[Hotspot] = []
    for row in kept.itertuples(index=False):
        source = getattr(row, "source", None)
        frp = getattr(row, "frp", None)
        hotspots.append(
            Hotspot(
                lon=float(row.lon),
                lat=float(row.lat),
                datetime=row.datetime,
                confidence=float(row.confidence),
                source=source,
                frp=(float(frp) if frp is not None and pd.notna(frp) else None),
            )
        )
    return hotspots


# ---------------------------------------------------------------------------
# Public loading helpers
# ---------------------------------------------------------------------------


def load_firms_hotspots(path: Optional[Path] = None) -> pd.DataFrame:
    """Load FIRMS hotspots from the configured default path or a custom path."""
    if path is None:
        path = config.firms_data_path()
    if not path.exists():
        raise FileNotFoundError(
            f"FIRMS hotspot file not found at {path}. Place a CSV in data/raw/ "
            "or set FIRMS_HOTSPOTS_FILE in .env."
        )
    return load_firms_csv(path)


def build_cell_grid(
    bounding_box: Optional[Tuple[float, float, float, float]] = None,
    spacing_deg: Optional[float] = None,
) -> CellGrid:
    """Build the CellGrid for the demo bounding box."""
    if bounding_box is None:
        bounding_box = config.bounding_box()
    if spacing_deg is None:
        spacing_deg = config.grid_spacing_deg()

    min_lon, min_lat, max_lon, max_lat = bounding_box
    n_cols = max(1, int(np.ceil((max_lon - min_lon) / spacing_deg)))
    n_rows = max(1, int(np.ceil((max_lat - min_lat) / spacing_deg)))
    return CellGrid(
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        spacing_deg=spacing_deg,
        n_rows=n_rows,
        n_cols=n_cols,
    )


def build_fire_dataset(
    df: Optional[pd.DataFrame] = None,
    bounding_box: Optional[Tuple[float, float, float, float]] = None,
    cell_grid: Optional[CellGrid] = None,
) -> FireDataset:
    """Build a FireDataset from a FIRMS DataFrame."""
    if df is None:
        df = load_firms_hotspots()
    if bounding_box is None:
        bounding_box = config.bounding_box()
    if cell_grid is None:
        cell_grid = build_cell_grid(bounding_box=bounding_box)

    min_lon, min_lat, max_lon, max_lat = bounding_box
    hotspots = hotspots_in_bbox(df, min_lon, min_lat, max_lon, max_lat)

    # Build per-cell per-day labels: 1 if at least one hotspot falls in the cell
    # on that day, else 0.
    labels: Dict[Tuple[int, int, str], int] = {}
    cell_hotspot_counts: Dict[Tuple[int, int], int] = {}

    for hs in hotspots:
        try:
            row, col = cell_grid.lon_lat_to_row_col(hs.lon, hs.lat)
        except ValueError:
            continue
        day_iso = hs.datetime.strftime("%Y-%m-%d")
        key = (row, col, day_iso)
        labels[key] = 1
        cell_hotspot_counts[(row, col)] = cell_hotspot_counts.get((row, col), 0) + 1

    # Fill in the full grid for the range of observed days so the dataset has
    # explicit zeros for non-burning cells.
    days = sorted({hs.datetime.strftime("%Y-%m-%d") for hs in hotspots})
    for row, col in cell_grid.iter_cells():
        for day_iso in days:
            key = (row, col, day_iso)
            labels.setdefault(key, 0)

    return FireDataset(
        bounding_box=bounding_box,
        hotspots=hotspots,
        cell_grid=cell_grid,
        labeled_days=days,
        labels=labels,
    )


def download_firms_hotspots(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    satellite: Optional[str] = None,
) -> Path:
    """Download FIRMS hotspots for the demo and save to data/raw/firms_hotspots.csv.

    This is a best-effort helper. FIRMS access may require a login or API token
    depending on the endpoint you use, so the project also supports loading an
    already-downloaded CSV.
    """
    raise NotImplementedError(
        "FIRMS download is not implemented in the starter scaffold. "
        "Download a CSV from https://firms.modaps.eosdis.nasa.gov/ and place it in "
        "data/raw/firms_hotspots.csv, or set FIRMS_HOTSPOTS_FILE in .env."
    )


# ---------------------------------------------------------------------------
# Convenience summary
# ---------------------------------------------------------------------------


def fire_dataset_summary(dataset: FireDataset) -> Dict[str, object]:
    """Return a small summary of a FireDataset for reporting/debugging."""
    bbox = dataset.bounding_box
    return {
        "bounding_box": list(bbox),
        "n_hotspots": len(dataset.hotspots),
        "n_rows": dataset.cell_grid.n_rows,
        "n_cols": dataset.cell_grid.n_cols,
        "n_cells": dataset.cell_grid.n_rows * dataset.cell_grid.n_cols,
        "n_labeled_days": len(dataset.labeled_days),
        "n_labeled_cells": len(dataset.labels),
        "n_burning_cells": sum(1 for v in dataset.labels.values() if v == 1),
    }
