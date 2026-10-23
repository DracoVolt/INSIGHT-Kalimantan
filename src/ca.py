"""Cellular Automaton (CA) for wildfire spread in INSIGHT.

This is the physics part of the science project. The CA uses a simple,
transparent update rule:

- Each cell has a state: healthy, igniting, burning, burned, or peat_risk.
- A burning cell can ignite its neighbors with a probability that depends on:
  - a base spread probability,
  - how well the neighbor aligns with the wind direction,
  - whether the neighbor is a peat-risk cell,
  - a small random component so the demo looks natural.

The CA is intentionally simple so it can be explained on a poster and re-run by
judges from one configuration file.
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import config


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class CellState(enum.Enum):
    HEALTHY = config.CA_STATE_HEALTHY
    IGNITING = config.CA_STATE_IGNITING
    BURNING = config.CA_STATE_BURNING
    BURNED = config.CA_STATE_BURNED
    PEAT_RISK = config.CA_STATE_PEAT_RISK


# Convenience accessors
STATE_HEALTHY = CellState.HEALTHY
STATE_IGNITING = CellState.IGNITING
STATE_BURNING = CellState.BURNING
STATE_BURNED = CellState.BURNED
STATE_PEAT_RISK = CellState.PEAT_RISK

STATE_TO_LABEL: Dict[CellState, str] = {s: s.value for s in CellState}
LABEL_TO_STATE: Dict[str, CellState] = {v: k for k, v in STATE_TO_LABEL.items()}


# Public alias used by tests and other modules
CELLState = CellState


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------


@dataclass
class CaGrid:
    """A CA grid over the demo bounding box."""

    n_rows: int = 0
    n_cols: int = 0
    states: np.ndarray = field(default_factory=lambda: np.empty((0, 0), dtype=object))
    peat_risk: np.ndarray = field(default_factory=lambda: np.empty((0, 0), dtype=bool))
    burning_intensity: np.ndarray = field(
        default_factory=lambda: np.empty((0, 0), dtype=float)
    )
    # Cells that can carry fire at all. The app passes the complement of the
    # OSM water mask, so rivers and lakes cut the fire front instead of burning
    # like forest; every inland cell stays burnable.
    burnable: np.ndarray = field(default_factory=lambda: np.empty((0, 0), dtype=bool))

    def initialize(
        self,
        n_rows: int,
        n_cols: int,
        peat_risk_mask: Optional[np.ndarray] = None,
        burnable_mask: Optional[np.ndarray] = None,
    ) -> "CaGrid":
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.states = np.full((n_rows, n_cols), CellState.HEALTHY, dtype=object)
        self.peat_risk = np.zeros((n_rows, n_cols), dtype=bool)
        self.burning_intensity = np.zeros((n_rows, n_cols), dtype=float)
        if burnable_mask is None:
            self.burnable = np.ones((n_rows, n_cols), dtype=bool)
        else:
            self.burnable = np.asarray(burnable_mask, dtype=bool)
            if self.burnable.shape != (n_rows, n_cols):
                raise ValueError(
                    f"burnable_mask must be {n_rows}x{n_cols}, "
                    f"got {self.burnable.shape}"
                )
        if peat_risk_mask is not None:
            self.peat_risk = np.asarray(peat_risk_mask, dtype=bool)
            self.states[peat_risk_mask] = CellState.PEAT_RISK
        return self

    def clone(self) -> "CaGrid":
        g = CaGrid()
        g.n_rows = self.n_rows
        g.n_cols = self.n_cols
        g.states = self.states.copy()
        g.peat_risk = self.peat_risk.copy()
        g.burning_intensity = self.burning_intensity.copy()
        g.burnable = self.burnable.copy()
        return g

    def set_state(self, row: int, col: int, state: CellState) -> None:
        if 0 <= row < self.n_rows and 0 <= col < self.n_cols:
            self.states[row, col] = state

    def state_at(self, row: int, col: int) -> CellState:
        return self.states[row, col]

    def is_burning(self, row: int, col: int) -> bool:
        return self.states[row, col] in (CellState.BURNING, CellState.IGNITING)

    def is_burnable(self, row: int, col: int) -> bool:
        if self.burnable.shape == self.states.shape and not self.burnable[row, col]:
            return False
        s = self.states[row, col]
        return s in (CellState.HEALTHY, CellState.PEAT_RISK)

    def neighbors(self, row: int, col: int) -> List[Tuple[int, int]]:
        out: List[Tuple[int, int]] = []
        for dr, dc in config.ca_neighbors():
            r = row + dr
            c = col + dc
            if 0 <= r < self.n_rows and 0 <= c < self.n_cols:
                out.append((r, c))
        return out

    def summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {label: 0 for label in STATE_TO_LABEL.values()}
        for row in range(self.n_rows):
            for col in range(self.n_cols):
                label = STATE_TO_LABEL[self.states[row, col]]
                counts[label] += 1
        counts["n_rows"] = self.n_rows
        counts["n_cols"] = self.n_cols
        return counts


# ---------------------------------------------------------------------------
# Wind / spread parameters
# ---------------------------------------------------------------------------


@dataclass
class CaParams:
    """Parameters for one CA simulation step."""

    wind_dir_deg: float = config.default_wind_direction_deg()
    spread_base: float = config.CA_SPREAD_BASE
    wind_alignment_strength: float = config.CA_WIND_ALIGNMENT_STRENGTH
    peat_influence: float = config.CA_PEAT_INFLUENCE
    random_seed: Optional[int] = None

    def make_rng(self) -> random.Random:
        if self.random_seed is None:
            return random.Random()
        return random.Random(self.random_seed)


def wind_alignment_factor(
    src_row: int,
    src_col: int,
    dst_row: int,
    dst_col: int,
    wind_dir_deg: float,
    grid_center_row: float,
    grid_center_col: float,
) -> float:
    """Return a [0,1] factor for how well the step from src to dst aligns with wind.

    ``wind_dir_deg`` follows the meteorological convention used everywhere else
    in the project (0 = wind FROM north, 90 = wind FROM east). 1 means the
    neighbor lies exactly downwind of the source cell, 0 means it lies upwind.
    """
    dr = dst_row - src_row
    dc = dst_col - src_col
    if dr == 0 and dc == 0:
        return 0.0

    # Grid convention: row increases southward, col increases eastward.
    # Compass bearing of the src->dst step: 0 = north, 90 = east, ...
    bearing = float(np.degrees(np.arctan2(dc, -dr)))
    if bearing < 0:
        bearing += 360.0

    # wind_dir_deg is meteorological (the direction the wind blows FROM), so a
    # fire pushed by a wind "from 90 deg" travels toward 270 deg.
    downwind = (wind_dir_deg + 180.0) % 360.0
    diff = abs(bearing - downwind)
    if diff > 180.0:
        diff = 360.0 - diff

    return float(max(0.0, min(1.0, 1.0 - diff / 180.0)))


def spread_probability(
    src_row: int,
    src_col: int,
    dst_row: int,
    dst_col: int,
    peat_risk: bool,
    params: CaParams,
    grid_center_row: float,
    grid_center_col: float,
) -> float:
    """Compute the probability that a burning src cell ignites a burnable dst cell."""
    wind_factor = wind_alignment_factor(
        src_row, src_col, dst_row, dst_col,
        params.wind_dir_deg, grid_center_row, grid_center_col,
    )
    peat_factor = config.CA_PEAT_INFLUENCE if peat_risk else 0.0
    p = params.spread_base + params.wind_alignment_strength * wind_factor + peat_factor
    return float(min(1.0, max(0.0, p)))


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------


def seed_cell(grid: CaGrid, row: int, col: int, state: CellState = CellState.BURNING) -> None:
    if 0 <= row < grid.n_rows and 0 <= col < grid.n_cols:
        grid.set_state(row, col, state)


def seed_from_hotspots(
    grid: CaGrid,
    hotspots: List["Hotspot"],
    cell_grid: "CellGrid",
) -> int:
    """Seed burning cells from a list of Hotspots.

    Returns the number of cells seeded.
    """
    from .fire_data import Hotspot as _Hotspot

    seeded = 0
    for hs in hotspots:
        if not isinstance(hs, _Hotspot):
            continue
        try:
            row, col = cell_grid.lon_lat_to_row_col(hs.lon, hs.lat)
        except ValueError:
            continue
        if grid.is_burnable(row, col):
            seed_cell(grid, row, col, CellState.BURNING)
            seeded += 1
    return seeded


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------


def step(
    grid: CaGrid,
    params: Optional[CaParams] = None,
) -> CaGrid:
    """Advance the CA by one step.

    Rules:
    - Burning/igniting cells become burned after one step.
    - Burnable neighbors of burning cells may become igniting based on the
      spread probability.
    - Peat-risk cells that ignite become 'igniting' and then burning next step.
    """
    if params is None:
        params = CaParams()

    rng = params.make_rng()

    center_row = (grid.n_rows - 1) / 2.0
    center_col = (grid.n_cols - 1) / 2.0

    next_states = grid.states.copy()
    next_intensity = np.zeros_like(grid.burning_intensity)

    for row in range(grid.n_rows):
        for col in range(grid.n_cols):
            current = grid.states[row, col]
            if current in (CellState.BURNING, CellState.IGNITING):
                next_states[row, col] = CellState.BURNED
                next_intensity[row, col] = grid.burning_intensity[row, col] + 1.0

    for row in range(grid.n_rows):
        for col in range(grid.n_cols):
            if grid.is_burning(row, col):
                for nr, nc in grid.neighbors(row, col):
                    if not grid.is_burnable(nr, nc):
                        continue
                    p = spread_probability(
                        row, col, nr, nc,
                        grid.peat_risk[nr, nc],
                        params,
                        center_row, center_col,
                    )
                    if rng.random() < p:
                        next_states[nr, nc] = CellState.IGNITING
                        next_intensity[nr, nc] = 0.5

    grid.states = next_states
    grid.burning_intensity = next_intensity
    return grid


def run_simulation(
    grid: CaGrid,
    steps: int,
    params: Optional[CaParams] = None,
) -> List[CaGrid]:
    """Run the CA for a given number of steps and return the frame history."""
    frames: List[CaGrid] = [grid.clone()]
    for _ in range(steps):
        grid = step(grid, params=params)
        frames.append(grid.clone())
    return frames


# ---------------------------------------------------------------------------
# Explanation helpers
# ---------------------------------------------------------------------------


def step_explanation(params: Optional[CaParams] = None) -> str:
    """Return a short plain-language explanation of the CA update rule."""
    if params is None:
        params = CaParams()
    return (
        f"Each step, burning cells become burned. A burning cell can ignite each "
        f"neighboring cell with probability up to "
        f"{params.spread_base + params.wind_alignment_strength + params.peat_influence:.2f}. "
        f"The probability is increased when the neighbor lies downwind "
        f"(wind direction {params.wind_dir_deg:.0f} deg) and when the neighbor is a "
        f"peat-risk cell. This is a teaching model, not an operational fire spread "
        f"model."
    )
