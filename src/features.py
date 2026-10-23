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
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

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
    "distance_to_nearest_hotspot_cell",
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


@lru_cache(maxsize=4096)
def _day_offset_iso(base_iso: str, offset_days: int) -> str:
    """Shift an ISO date; cached because it is asked for the same days a lot."""
    dt = datetime.strptime(base_iso, "%Y-%m-%d")
    dt = dt + timedelta(days=offset_days)
    return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Nearest-feature distance (exact, vectorized)
# ---------------------------------------------------------------------------
#
# For every cell we need the Euclidean distance (in cells) to the nearest cell
# whose mask is True (nearest water / settlement). The naive double loop costs
# O(n_rows * n_cols) *per query*, which dominates the feature-table build once
# there are many cells x many days (minutes for real multi-day FIRMS data).
#
# Instead we use an exact Euclidean distance transform (EDT): one separable
# pass per axis computes the distance for ALL cells at once in
# O(n_rows * n_cols). See Felzenszwalb & Huttenlocher, "Distance Transforms of
# Sampled Functions" (2012) for the lower-envelope algorithm used in 1D.


def _edt_1d(f: np.ndarray) -> np.ndarray:
    """Exact 1D squared Euclidean distance transform.

    Computes d[q] = min_p ((q - p)**2 + f[p]) via the lower envelope of
    parabolas in O(len(f)). f must be finite everywhere.
    """
    n = int(f.shape[0])
    d = np.empty(n, dtype=float)
    v = np.zeros(n, dtype=int)       # parabola sites in the lower envelope
    z = np.empty(n + 1, dtype=float)  # boundary positions between parabolas
    k = 0
    v[0] = 0
    z[0] = -np.inf
    z[1] = np.inf
    for q in range(1, n):
        fq = f[q] + q * q
        while True:
            vk = v[k]
            s = (fq - (f[vk] + vk * vk)) / (2.0 * (q - vk))
            if s > z[k]:
                break
            k -= 1
        k += 1
        v[k] = q
        z[k] = s
        z[k + 1] = np.inf
    k = 0
    for q in range(n):
        while z[k + 1] < q:
            k += 1
        d[q] = (q - v[k]) ** 2 + f[v[k]]
    return d


def _squared_edt_2d(mask: np.ndarray) -> np.ndarray:
    """Exact squared Euclidean distance transform of a boolean 2D mask.

    Pass 1 (columns): squared distance to the nearest True cell in the same
    column, vectorized over all columns with two sequential sweeps.
    Pass 2 (rows): the general 1D transform per row combines columns.
    """
    mask = np.asarray(mask, dtype=bool)
    n_rows, n_cols = mask.shape

    g = np.where(mask, 0.0, np.inf)

    # Nearest True cell at or above (swept downward, vectorized over columns).
    above = np.full(n_cols, -1, dtype=int)
    for i in range(n_rows):
        above = np.where(mask[i], i, above)
        gap = i - above
        g[i] = np.minimum(g[i], np.where(above >= 0, gap * gap, np.inf))

    # Nearest True cell at or below (swept upward).
    below = np.full(n_cols, n_rows, dtype=int)
    for i in range(n_rows - 1, -1, -1):
        below = np.where(mask[i], i, below)
        gap = below - i
        g[i] = np.minimum(g[i], np.where(below < n_rows, gap * gap, np.inf))

    # Columns with no True cell at all stay +inf; replace them with a value
    # larger than any real squared distance so the 1D pass stays finite but
    # those columns can never win the minimum.
    big = float((n_rows + n_cols) ** 2 + 1)
    g = np.where(np.isfinite(g), g, big)

    out = np.empty_like(g)
    for i in range(n_rows):
        out[i] = _edt_1d(g[i])
    return out


def nearest_feature_distance(mask: np.ndarray) -> np.ndarray:
    """Distance in cells from every cell to the nearest True cell.

    Exact Euclidean distance, computed for the whole grid in
    O(n_rows * n_cols) with a separable distance transform instead of the
    previous brute-force double scan per query.

    If the mask contains no True cells, every entry is n_rows + n_cols (the
    demo's "very far" sentinel, matching the previous behavior).
    """
    mask = np.asarray(mask, dtype=bool)
    if mask.size == 0:
        return np.zeros(mask.shape, dtype=float)
    if not mask.any():
        return np.full(mask.shape, float(mask.shape[0] + mask.shape[1]))
    return np.sqrt(_squared_edt_2d(mask))


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

    def __post_init__(self) -> None:
        # Precompute exact nearest-feature distances once (vectorized) so
        # per-cell lookups during feature-table building are O(1).
        self._water_dist = nearest_feature_distance(self.is_water)
        self._settlement_dist = nearest_feature_distance(self.is_settlement)

    def nearest_water_distance(self, row: int, col: int) -> float:
        return float(self._water_dist[row, col])

    def nearest_settlement_distance(self, row: int, col: int) -> float:
        return float(self._settlement_dist[row, col])


CONTEXT_MAP_CACHE_VERSION = 1


def build_context_map(
    osm_snapshot: Optional[object] = None,
    cell_grid: Optional[CellGrid] = None,
    cache_path: Optional[Any] = None,
    cache_key: str = "",
) -> ContextMap:
    """Build a ContextMap from an OsmSnapshot.

    If no snapshot is provided, the map is left blank (all False). This lets the
    pipeline run even before OSM data is fetched.

    Passing *cache_path* (plus a *cache_key* that changes whenever the snapshot
    or grid does) keeps the three boolean masks in a small ``.npz``. Parsing the
    OSM snapshot and classifying its ~59k features is the slowest part of a cold
    start, and the result only changes when the snapshot is refreshed.
    """
    if cell_grid is None:
        cell_grid = build_cell_grid()

    n_rows = cell_grid.n_rows
    n_cols = cell_grid.n_cols

    if cache_path is not None and cache_key:
        cached = read_context_cache(cache_path, cache_key, n_rows, n_cols)
        if cached is not None:
            return cached

    is_water = np.zeros((n_rows, n_cols), dtype=bool)
    is_settlement = np.zeros((n_rows, n_cols), dtype=bool)
    is_peat_risk = np.zeros((n_rows, n_cols), dtype=bool)

    if osm_snapshot is not None:
        # Attempt duck-typed access so this works with either the real module or
        # a lightweight test stub.
        features = getattr(osm_snapshot, "features", [])
        lats: List[float] = []
        lons: List[float] = []
        water: List[bool] = []
        settlement: List[bool] = []
        peat: List[bool] = []
        for f in features:
            center = getattr(f, "center", None)
            if center is None:
                continue
            lat, lon = center
            tags = getattr(f, "tags", {}) or {}
            lats.append(lat)
            lons.append(lon)
            water.append(_is_water_tags(tags))
            settlement.append(_is_settlement_tags(tags))
            peat.append(_is_peat_tags(tags))

        if lats:
            lat_arr = np.asarray(lats, dtype=float)
            lon_arr = np.asarray(lons, dtype=float)
            # Same mapping as CellGrid.lon_lat_to_row_col, done in one shot:
            # a per-feature Python call dominated this function's runtime.
            spacing = float(cell_grid.spacing_deg)
            inside = (
                (lon_arr >= cell_grid.min_lon)
                & (lon_arr <= cell_grid.max_lon)
                & (lat_arr >= cell_grid.min_lat)
                & (lat_arr <= cell_grid.max_lat)
            )
            cols = np.clip(((lon_arr - cell_grid.min_lon) / spacing).astype(int), 0, n_cols - 1)
            rows = np.clip(((cell_grid.max_lat - lat_arr) / spacing).astype(int), 0, n_rows - 1)
            for flags, target in (
                (water, is_water),
                (settlement, is_settlement),
                (peat, is_peat_risk),
            ):
                hit = inside & np.asarray(flags, dtype=bool)
                if hit.any():
                    target[rows[hit], cols[hit]] = True

    context_map = ContextMap(
        n_rows=n_rows,
        n_cols=n_cols,
        is_water=is_water,
        is_settlement=is_settlement,
        is_peat_risk=is_peat_risk,
    )
    if cache_path is not None and cache_key:
        _write_context_cache(cache_path, cache_key, context_map)
    return context_map


def read_context_cache(
    path: Any,
    key: str,
    n_rows: int,
    n_cols: int,
) -> Optional[ContextMap]:
    """Return cached masks for *key*, or None when the cache is absent/stale."""
    try:
        with np.load(path) as data:
            if str(data["key"]) != key:
                return None
            water = data["is_water"]
            settlement = data["is_settlement"]
            peat = data["is_peat_risk"]
    except (OSError, ValueError, KeyError):
        return None
    if water.shape != (n_rows, n_cols):
        return None
    return ContextMap(
        n_rows=n_rows,
        n_cols=n_cols,
        is_water=water.astype(bool),
        is_settlement=settlement.astype(bool),
        is_peat_risk=peat.astype(bool),
    )


def _write_context_cache(path: Any, key: str, context_map: ContextMap) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            np.savez_compressed(
                fh,
                key=np.asarray(key),
                is_water=context_map.is_water,
                is_settlement=context_map.is_settlement,
                is_peat_risk=context_map.is_peat_risk,
            )
    except OSError:
        pass


_SETTLEMENT_PLACES = frozenset(p.lower() for p in config.OSM_SETTLEMENT_PLACE_TAGS)
_WATER_NATURAL = frozenset({"water", "coastline"})


def _is_water_tags(tags: Dict[str, str]) -> bool:
    return bool(
        tags.get("natural", "").lower() in _WATER_NATURAL
        or tags.get("water", "").lower()
        or tags.get("waterway", "").lower()
    )


def _is_settlement_tags(tags: Dict[str, str]) -> bool:
    return tags.get("place", "").lower() in _SETTLEMENT_PLACES


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
    target_day: Optional[str] = None,
) -> Dict[str, float]:
    """Compute hotspot-history features for one cell, for one target day.

    History covers the days *before* ``target_day`` only (D-1, D-3, D-7). The
    target day itself is never included, otherwise ``has_hotspot_last_1_day``
    would equal the label and the model would learn nothing but a copy rule.
    """
    if target_day is None:
        target_day = days[-1] if days else None

    if target_day is None:
        return {
            "has_hotspot_last_1_day": 0.0,
            "has_hotspot_last_3_days": 0.0,
            "has_hotspot_last_7_days": 0.0,
            "hotspot_count_last_7_days": 0.0,
        }

    def count_on(offset_days: int) -> int:
        day = _day_offset_iso(target_day, offset_days)
        return int(cell_day_labels.get((row, col, day), 0))

    last3 = sum(count_on(-k) for k in (1, 2, 3))
    last7 = sum(count_on(-k) for k in range(1, 8))

    return {
        "has_hotspot_last_1_day": float(count_on(-1)),
        "has_hotspot_last_3_days": float(min(last3, 1)),
        "has_hotspot_last_7_days": float(min(last7, 1)),
        "hotspot_count_last_7_days": float(last7),
    }


def recent_hotspot_arrays(
    dataset: FireDataset,
    target_day: Optional[str] = None,
) -> Dict[str, np.ndarray]:
    """Per-cell hotspot-history features for one target day.

    This is the inference-time counterpart of the history columns in
    `build_feature_table`: same definitions, same convention that a feature for
    day D only looks at days before D. ``target_day`` defaults to the day after
    the last observed FIRMS day, so the map answers "where will fire occur next
    given what burned up to now" rather than "where did it burn".

    Returns one (n_rows, n_cols) array per history feature name.
    """
    cell_grid = dataset.cell_grid
    shape = (cell_grid.n_rows, cell_grid.n_cols)
    far = float(cell_grid.n_rows + cell_grid.n_cols)

    if target_day is None:
        if dataset.labeled_days:
            last_day = dataset.labeled_days[-1]
            if not isinstance(last_day, str):
                last_day = last_day.strftime("%Y-%m-%d")
            target_day = _day_offset_iso(last_day, 1)

    arrays: Dict[str, np.ndarray] = {
        "has_hotspot_last_1_day": np.zeros(shape, dtype=float),
        "has_hotspot_last_3_days": np.zeros(shape, dtype=float),
        "has_hotspot_last_7_days": np.zeros(shape, dtype=float),
        "hotspot_count_last_7_days": np.zeros(shape, dtype=float),
        "distance_to_nearest_hotspot_cell": np.full(shape, far, dtype=float),
    }
    if target_day is None:
        return arrays

    days = dataset.labeled_days
    for row, col in cell_grid.iter_cells():
        history = hotspot_history_for_cell(
            dataset.hotspots, row, col, cell_grid, days, dataset.labels,
            target_day=target_day,
        )
        for name in (
            "has_hotspot_last_1_day",
            "has_hotspot_last_3_days",
            "has_hotspot_last_7_days",
            "hotspot_count_last_7_days",
        ):
            arrays[name][row, col] = history[name]

    # Distance to the nearest hotspot on the day before the target day (the
    # same definition used for training).
    prev_day = _day_offset_iso(target_day, -1)
    mask = np.zeros(shape, dtype=bool)
    for (r, c, day_iso), value in dataset.labels.items():
        if value and day_iso == prev_day and 0 <= r < shape[0] and 0 <= c < shape[1]:
            mask[r, c] = True
    if mask.any():
        arrays["distance_to_nearest_hotspot_cell"] = nearest_feature_distance(mask)
    return arrays


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

    The feature is 1 - |bearing difference| / 180, clipped to [0, 1]: 1 for a
    cell directly downwind of the grid center, 0.5 perpendicular, 0 upwind.
    ``wind_dir_deg`` is meteorological (the direction the wind comes FROM).

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

    # cell-to-center bearing (clockwise from north); row increases southward.
    bearing = float(np.degrees(np.arctan2(dc, -dr)))
    if bearing < 0:
        bearing += 360.0

    # Meteorological convention: wind_dir_deg is where the wind comes FROM.
    downwind = (wind_dir_deg + 180.0) % 360.0
    diff = abs(bearing - downwind)
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

    # Distance to the nearest hotspot on the previous day, per target day.
    # Fires cluster, so this is usually the strongest single predictor; it is
    # computed once per day with the exact Euclidean distance transform.
    positives_by_day: Dict[str, List[Tuple[int, int]]] = {}
    for (r, c, day_iso), value in labels.items():
        if value:
            positives_by_day.setdefault(day_iso, []).append((r, c))

    shape = (cell_grid.n_rows, cell_grid.n_cols)
    far = float(cell_grid.n_rows + cell_grid.n_cols)
    hotspot_distance: Dict[str, np.ndarray] = {}
    for day_iso in days:
        prev_day = _day_offset_iso(day_iso, -1)
        mask = np.zeros(shape, dtype=bool)
        for r, c in positives_by_day.get(prev_day, []):
            if 0 <= r < shape[0] and 0 <= c < shape[1]:
                mask[r, c] = True
        hotspot_distance[day_iso] = (
            nearest_feature_distance(mask) if mask.any() else np.full(shape, far)
        )

    rows: List[FeatureRow] = []
    for row, col in cell_grid.iter_cells():
        center_lon, center_lat = cell_grid.row_col_to_center(row, col)
        for day_iso in days:
            history = hotspot_history_for_cell(
                dataset.hotspots, row, col, cell_grid, days, labels, target_day=day_iso
            )
            feats: Dict[str, float] = {
                "cell_row": float(row),
                "cell_col": float(col),
                "distance_to_nearest_water_cell": float(
                    context_map.nearest_water_distance(row, col)
                ),
                "distance_to_nearest_settlement_cell": float(
                    context_map.nearest_settlement_distance(row, col)
                ),
                "distance_to_nearest_hotspot_cell": float(
                    hotspot_distance[day_iso][row, col]
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
