"""Civilian-mitigation logic for INSIGHT.

This module implements a small, transparent rule set that decides when to show
mitigation guidance to civilians in a rural or settlement area that the CA
predicts is at risk. It is intentionally simple so the science project can
explain the logic on a poster.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import config
from .ca import CaGrid


# ---------------------------------------------------------------------------
# Location helpers (re-exported for the app layer)
# ---------------------------------------------------------------------------


def loc_to_cell(lat: float, lon: float) -> Tuple[int, int]:
    """Map a WGS84 lat/lon to the demo grid cell (row, col).

    Returns (row, col) where row increases southward and col increases eastward.
    Raises ValueError if the location is outside the demo bounding box.
    """
    min_lon, min_lat, max_lon, max_lat = config.bounding_box()
    d_lon = config.grid_spacing_deg()
    d_lat = config.grid_spacing_deg()

    if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
        raise ValueError(
            f"Location ({lat:.4f}, {lon:.4f}) is outside the demo bounding box "
            f"({min_lon}, {min_lat}) -> ({max_lon}, {max_lat})."
        )

    col = int((lon - min_lon) / d_lon)
    row = int((max_lat - lat) / d_lat)

    n_rows = max(1, (max_lat - min_lat) / d_lat)
    n_cols = max(1, (max_lon - min_lon) / d_lon)

    row = min(row, int(n_rows) - 1)
    col = min(col, int(n_cols) - 1)

    return (row, col)


def cell_center_lat_lon(row: int, col: int) -> Tuple[float, float]:
    """Return the center lat/lon of a grid cell."""
    min_lon, min_lat, max_lon, max_lat = config.bounding_box()
    d_lon = config.grid_spacing_deg()
    d_lat = config.grid_spacing_deg()

    lon = min_lon + (col + 0.5) * d_lon
    lat = max_lat - (row + 0.5) * d_lat
    return (lat, lon)


def cells_within_radius(
    center_row: int,
    center_col: int,
    radius_cells: int,
    n_rows: int,
    n_cols: int,
) -> List[Tuple[int, int]]:
    """Return all cell (row, col) within radius_cells of the center cell."""
    out: List[Tuple[int, int]] = []
    r0 = max(0, center_row - radius_cells)
    r1 = min(n_rows - 1, center_row + radius_cells)
    c0 = max(0, center_col - radius_cells)
    c1 = min(n_cols - 1, center_col + radius_cells)

    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            d = float(((r - center_row) ** 2 + (c - center_col) ** 2) ** 0.5)
            if d <= float(radius_cells):
                out.append((r, c))

    return out


# ---------------------------------------------------------------------------
# Risk level
# ---------------------------------------------------------------------------


class RiskLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Mitigation action
# ---------------------------------------------------------------------------


@dataclass
class MitigationAction:
    title: str
    description: str
    timing: str
    icon: str = "⚠️"


MITIGATION_ACTIONS: Dict[RiskLevel, List[MitigationAction]] = {
    RiskLevel.NONE: [],
    RiskLevel.LOW: [
        MitigationAction(
            title="Prepare",
            description="Review your evacuation route and keep a phone charged.",
            timing="Now",
        ),
        MitigationAction(
            title="Clear perimeter",
            description="Remove dry leaves and debris around your home if safe to do so.",
            timing="Now",
        ),
    ],
    RiskLevel.MEDIUM: [
        MitigationAction(
            title="Alert neighbors",
            description="Tell nearby households to prepare and watch for smoke.",
            timing="Within hours",
        ),
        MitigationAction(
            title="Wet the perimeter",
            description="If water is available and safe, dampen the area around structures.",
            timing="Now",
        ),
        MitigationAction(
            title="Protect peat areas",
            description="Avoid actions that dry out peat, such as drainage, which can worsen fire spread.",
            timing="Now",
        ),
    ],
    RiskLevel.HIGH: [
        MitigationAction(
            title="Evacuate early",
            description="Move to a safer location before roads become difficult.",
            timing="Immediate",
        ),
        MitigationAction(
            title="Contact authorities",
            description="Alert local emergency services or community leaders.",
            timing="Immediate",
        ),
        MitigationAction(
            title="Secure livestock and valuables",
            description="If time allows, move animals and important items to safety.",
            timing="Before leaving",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Risk assessment
# ---------------------------------------------------------------------------


@dataclass
class MitigationContext:
    """What the app knows about a rural/settlement cell and its surroundings."""

    cell_row: int
    cell_col: int
    is_settlement: bool
    is_rural: bool
    distance_to_nearest_burning_cell: Optional[float]
    distance_to_nearest_igniting_cell: Optional[float]
    ca_state: str
    predicted_risk: float
    wind_dir_deg: float
    note: str = ""


def assess_risk(ctx: MitigationContext) -> RiskLevel:
    """Return the risk level for a mitigation context."""
    if ctx.distance_to_nearest_burning_cell is not None and ctx.distance_to_nearest_burning_cell <= 1.0:
        return RiskLevel.HIGH
    if ctx.distance_to_nearest_igniting_cell is not None and ctx.distance_to_nearest_igniting_cell <= 2.0:
        return RiskLevel.HIGH

    if ctx.distance_to_nearest_burning_cell is not None and ctx.distance_to_nearest_burning_cell <= 2.0:
        return RiskLevel.MEDIUM
    if ctx.distance_to_nearest_igniting_cell is not None and ctx.distance_to_nearest_igniting_cell <= 3.0:
        return RiskLevel.MEDIUM

    if ctx.predicted_risk > 0.5:
        return RiskLevel.HIGH
    if ctx.predicted_risk > 0.2:
        return RiskLevel.LOW

    return RiskLevel.NONE


def actions_for(ctx: MitigationContext) -> List[MitigationAction]:
    """Return the mitigation actions for a context, plus any custom note."""
    risk = assess_risk(ctx)
    actions = list(MITIGATION_ACTIONS.get(risk, []))
    if ctx.note:
        actions.append(
            MitigationAction(
                title="Local note",
                description=ctx.note,
                timing="As relevant",
            )
        )
    return actions


# ---------------------------------------------------------------------------
# Scanning helper
# ---------------------------------------------------------------------------


def _distance_to_points(
    rows: np.ndarray,
    cols: np.ndarray,
    row: int,
    col: int,
    radius: float,
) -> Optional[float]:
    """Distance to the closest (rows, cols) pair, or None beyond radius."""
    if rows.size == 0:
        return None
    distances = np.hypot(rows - row, cols - col)
    within = distances[distances <= radius]
    return float(within.min()) if within.size else None


def _nearest_distance(
    mask: np.ndarray,
    row: int,
    col: int,
    radius: float,
) -> Optional[float]:
    """Distance to the closest True cell, or None when none is within radius."""
    return _distance_to_points(*np.nonzero(mask), row, col, radius)


def nearest_burning_or_igniting_distance(
    grid: "CaGrid",
    row: int,
    col: int,
    max_radius: Optional[int] = None,
) -> Tuple[Optional[float], Optional[float]]:
    """Return (nearest_burning_distance, nearest_igniting_distance) in cell units.

    Vectorised: a Python double loop over every cell was the single slowest step
    of a run (~10 s for the demo box), because it was repeated once per
    settlement and rural cell.
    """
    from .ca import CellState

    radius = max_radius if max_radius is not None else (grid.n_rows + grid.n_cols)
    states = np.asarray(grid.states, dtype=object)
    if states.size == 0:
        return (None, None)

    burning = _nearest_distance(states == CellState.BURNING, row, col, radius)
    igniting = _nearest_distance(states == CellState.IGNITING, row, col, radius)
    return (burning, igniting)


def build_mitigation_contexts(
    grid: "CaGrid",
    settlement_cells: List[Tuple[int, int]],
    rural_cells: List[Tuple[int, int]],
    risk_map: Optional[np.ndarray] = None,
    wind_dir_deg: Optional[float] = None,
) -> Dict[Tuple[int, int], MitigationContext]:
    """Build mitigation contexts for settlement and rural cells near the fire."""
    if wind_dir_deg is None:
        wind_dir_deg = config.default_wind_direction_deg()

    contexts: Dict[Tuple[int, int], MitigationContext] = {}
    radius = config.mitigation_risk_radius_cells()
    rural_radius = config.mitigation_rural_radius_cells()

    combined = []
    for row, col in settlement_cells:
        combined.append((row, col, True, False))
    for row, col in rural_cells:
        combined.append((row, col, False, True))

    # Locate the fire once instead of rescanning the grid for every cell.
    from .ca import CellState

    states = np.asarray(grid.states, dtype=object)
    burn_rows, burn_cols = np.nonzero(states == CellState.BURNING)
    ign_rows, ign_cols = np.nonzero(states == CellState.IGNITING)
    scan_radius = radius * 2

    for row, col, is_settlement, is_rural in combined:
        burning_dist = _distance_to_points(burn_rows, burn_cols, row, col, scan_radius)
        igniting_dist = _distance_to_points(ign_rows, ign_cols, row, col, scan_radius)
        if burning_dist is None and igniting_dist is None:
            continue

        predicted_risk = float(risk_map[row, col]) if risk_map is not None else 0.0
        ctx = MitigationContext(
            cell_row=row,
            cell_col=col,
            is_settlement=is_settlement,
            is_rural=is_rural,
            distance_to_nearest_burning_cell=burning_dist,
            distance_to_nearest_igniting_cell=igniting_dist,
            ca_state=grid.state_at(row, col).value,
            predicted_risk=predicted_risk,
            wind_dir_deg=wind_dir_deg,
        )
        contexts[(row, col)] = ctx

    return contexts


def format_actions_for_display(actions: List[MitigationAction]) -> List[Dict[str, str]]:
    """Convert actions into a display-friendly list of dicts."""
    return [
        {
            "title": a.title,
            "description": a.description,
            "timing": a.timing,
            "icon": a.icon,
        }
        for a in actions
    ]
