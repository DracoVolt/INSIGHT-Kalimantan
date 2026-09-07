"""Per-cell feature engineering for the ML pipeline.

The goal is a small set of explainable features that can be computed from:
- the CA-style cell grid,
- OSM-derived context (water, settlement, peat-like features),
- wind direction,
- recent hotspot history.

This keeps the ML part of the science project explainable and reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from . import config
from .fire_data import CellGrid, FireDataset, Hotspot, build_cell_grid


# ---------------------------------------------------------------------------
# Feature schema
# ---------------------------------------------------------------------------

FEATURE_NAMES: Tuple[str, ...] = (
    "cell_row",
    "cell_col",
    "distance_to_nearest_water_cell",
    "distance_to_nearest_settlement_cell",
    "peat_risk_flag",
    "has_hotspot_last_1_day",
    "has_hotspot_last_3_days",
    "has_hotspot_last_7_days",
    "hotspot_count_last_7_days",
    "wind_alignment",
    "lon",
    "lat",
)


def feature_names() -> Tuple[str, ...]:
    return FEATURE_NAMES


# ---------------------------------------------------------------------------
# Feature row
# ---------------------------------------------------------------------------


@dataclass
class FeatureRow:
    """One feature row for one cell on one day."""

    row: int
    col: int
    day_iso: str
    features: Dict[str, float]
    label: Optional[int] = None


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _day_offset_iso(base_iso: str, offset_days: int) -> str:
    dt = datetime.strptime(base_iso, "%Y-%m-%d")
    dt = dt + timedelta(days=offset_days)
    return dt.strftime("%Y-%m-%d")


def _euclidean_distance(row1: int, col1: int, row2: int, col2: int) -> float:
    return float(((row1 - row2) ** 2 + (col1 - col2) ** 2) ** 0.5)


# ---------------------------------------------------------------------------
# Context maps
# ---------------------------------------------------------------------------


@dataclass
class ContextMap:
    """A small per-cell context map built from OSM-derived features."""

    n_rows: int
    n_cols: int
    is_water: np.ndarray      # shape (n_rows, n_cols)
    is_settlement: np.ndarray
    is_peat_risk: np.ndarray

    def nearest_water_distance(self, row: int, col: int) -> float:
        return self._nearest_distance(row, col, self.is_water)

    def nearest_settlement_distance(self, row: int, col: int) -> float:
        return self._nearest_distance(row, col, self.is_settlement)

    def _nearest_distance(
        self, row: int, col: int, mask: np.ndarray
    ) -> float:
        """Nearest Manhattan-ish cell distance to any True cell in mask.

        For the demo, we use Euclidean cell distance. This is fast and easy to
        explain.
        """
        best = np.inf
        for r in range(self.n_rows):
            for c in range(self.n_cols):
                if mask[r, c]:
                    d = _euclidean_distance(row, col, r, c)
                    if d < best:
                        best = d
        if np.isinf(best):
            return float(self.n_rows + self.n_cols)
        return best


def build_context_map(
    osm_snapshot: Optional[object] = None,
    cell_grid: Optional[CellGrid] = None,
) -> ContextMap:
    """Build a ContextMap from an OsmSnapshot.

    If no snapshot is provided, the map is left blank (all False). This lets the
    pipeline run even before OSM data is fetched.
    """
    if cell_grid is None:
        cell_grid = build_cell_grid()

    n_rows = cell_grid.n_rows
    n_cols = cell_grid.n_cols

    is_water = np.zeros((n_rows, n_cols), dtype=bool)
    is_settlement = np.zeros((n_rows, n_cols), dtype=bool)
    is_peat_risk = np.zeros((n_rows, n_cols), dtype=bool)

    if osm_snapshot is not None:
        # Attempt duck-typed access so this works with either the real module or
        # a lightweight test stub.
        features = getattr(osm_snapshot, "features", [])
        for f in features:
            if f.center is None:
                continue
            lat, lon = f.center
            try:
                row, col = cell_grid.lon_lat_to_row_col(lon, lat)
            except ValueError:
                continue

            tags = getattr(f, "tags", {})
            if _is_water_tags(tags):
                is_water[row, col] = True
            if _is_settlement_tags(tags):
                is_settlement[row, col] = True
            if _is_peat_tags(tags):
                is_peat_risk[row, col] = True

    return ContextMap(
        n_rows=n_rows,
        n_cols=n_cols,
        is_water=is_water,
        is_settlement=is_settlement,
        is_peat_risk=is_peat_risk,
    )


def _is_water_tags(tags: Dict[str, str]) -> bool:
    return bool(
        tags.get("natural", "").lower() in {"water", "coastline"}
        or tags.get("water", "").lower()
        or tags.get("waterway", "").lower()
    )


def _is_settlement_tags(tags: Dict[str, str]) -> bool:
    place = tags.get("place", "").lower()
    return place in {p.lower() for p in config.OSM_SETTLEMENT_PLACE_TAGS}


def _is_peat_tags(tags: Dict[str, str]) -> bool:
    natural = tags.get("natural", "").lower()
    landuse = tags.get("landuse", "").lower()
    return natural == "wetland" or landuse in {"peat", "peat_extraction"}


# ---------------------------------------------------------------------------
# Hotspot history per cell
# ---------------------------------------------------------------------------


def hotspot_history_for_cell(
    hotspots: List[Hotspot],
    row: int,
    col: int,
    cell_grid: CellGrid,
    days: List[str],
    cell_day_labels: Dict[Tuple[int, int, str], int],
) -> Dict[str, float]:
    """Compute hotspot-history features for one cell across the given days."""
    counts: Dict[str, int] = {}
    for day_iso in days:
        counts[day_iso] = cell_day_labels.get((row, col, day_iso), 0)

    out: Dict[str, float] = {}
    out["has_hotspot_last_1_day"] = float(
        int(counts.get(days[0], 0)) if days else 0
    )
    last3 = sum(counts.get(_day_offset_iso(days[0], -k), 0) for k in range(0, 3))
    out["has_hotspot_last_3_days"] = float(min(last3, 1))
    last7 = sum(counts.get(_day_offset_iso(days[0], -k), 0) for k in range(0, 7))
    out["has_hotspot_last_7_days"] = float(min(last7, 1))
    out["hotspot_count_last_7_days"] = float(last7)
    return out


# ---------------------------------------------------------------------------
# Wind alignment feature
# ---------------------------------------------------------------------------


def wind_alignment(
    row: int,
    col: int,
    wind_dir_deg: float,
    grid_center_lon: float,
    grid_center_lat: float,
) -> float:
    """Compute a wind-alignment feature for a cell relative to the grid center.

    The feature is the cosine of the angle between the wind direction and the
    direction from the grid center to the cell, clipped to [0, 1].

    This is a teaching feature, not a meteorological calculation.
    """
    center_row = (config.bounding_box()[3] - config.bounding_box()[1]) / (
        config.grid_spacing_deg()
    ) / 2.0
    center_col = (config.bounding_box()[2] - config.bounding_box()[0]) / (
        config.grid_spacing_deg()
    ) / 2.0

    dr = row - center_row
    dc = col - center_col
    if dr == 0 and dc == 0:
        return 0.0

    # cell-to-center bearing (clockwise from north)
    bearing = float(np.degrees(np.arctan2(dc, dr)))
    if bearing < 0:
        bearing += 360.0

    wind_dir = wind_dir_deg % 360.0
    diff = abs(bearing - wind_dir)
    if diff > 180.0:
        diff = 360.0 - diff

    alignment = (1.0 - diff / 180.0)
    return float(max(0.0, min(1.0, alignment)))


# ---------------------------------------------------------------------------
# Build feature table
# ---------------------------------------------------------------------------


def build_feature_table(
    dataset: FireDataset,
    context_map: Optional[ContextMap] = None,
    wind_dir_deg: Optional[float] = None,
) -> pd.DataFrame:
    """Build a feature DataFrame for the demo ML pipeline.

    Each row is one cell on one day. The label is 1 if the cell had at least one
    FIRMS hotspot that day inside the bounding box, else 0.
    """
    if context_map is None:
        context_map = build_context_map()
    if wind_dir_deg is None:
        wind_dir_deg = config.default_wind_direction_deg()

    cell_grid = dataset.cell_grid
    days = dataset.labeled_days
    labels = dataset.labels

    rows: List[FeatureRow] = []
    for row, col in cell_grid.iter_cells():
        center_lon, center_lat = cell_grid.row_col_to_center(row, col)
        history = hotspot_history_for_cell(
            dataset.hotspots, row, col, cell_grid, days, labels
        )
        for day_iso in days:
            feats: Dict[str, float] = {
                "cell_row": float(row),
                "cell_col": float(col),
                "distance_to_nearest_water_cell": float(
                    context_map.nearest_water_distance(row, col)
                ),
                "distance_to_nearest_settlement_cell": float(
                    context_map.nearest_settlement_distance(row, col)
                ),
                "peat_risk_flag": float(context_map.is_peat_risk[row, col]),
                "has_hotspot_last_1_day": history["has_hotspot_last_1_day"],
                "has_hotspot_last_3_days": history["has_hotspot_last_3_days"],
                "has_hotspot_last_7_days": history["has_hotspot_last_7_days"],
                "hotspot_count_last_7_days": history["hotspot_count_last_7_days"],
                "wind_alignment": wind_alignment(
                    row, col, wind_dir_deg, center_lon, center_lat
                ),
                "lon": center_lon,
                "lat": center_lat,
            }
            label = labels.get((row, col, day_iso))
            rows.append(FeatureRow(row=row, col=col, day_iso=day_iso, features=feats, label=label))

    records = [r.features for r in rows]
    df = pd.DataFrame(records, columns=list(feature_names()))
    df["label"] = [r.label for r in rows]
    df["row"] = [r.row for r in rows]
    df["col"] = [r.col for r in rows]
    df["day_iso"] = [r.day_iso for r in rows]
    return df


def feature_table_summary(df: pd.DataFrame) -> Dict[str, object]:
    """Return a small summary of a feature DataFrame."""
    return {
        "n_rows": int(len(df)),
        "n_features": int(df.shape[1] - 4),  # exclude row/col/day_iso/label
        "n_positives": int((df["label"] == 1).sum()),
        "n_negatives": int((df["label"] == 0).sum()),
        "feature_columns": list(feature_names()),
    }
