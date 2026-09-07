"""CA simulation frontend helpers for IGNIS-Sim.

This module bridges the core CA and ML code with the demo app. It is kept thin
so the app can be either Streamlit-based or a simple script.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src import config
from src.ca import (
    CaGrid,
    CaParams,
    CELLState,
    run_simulation,
    seed_from_hotspots,
    step,
)
from src.fire_data import FireDataset, build_cell_grid, build_fire_dataset, load_firms_hotspots
from src.features import build_context_map
from src.ml import predict_risk_map
from src.mitigation import (
    build_mitigation_contexts,
    format_actions_for_display,
    MitigationContext,
)


@dataclass
class SimState:
    grid: CaGrid
    frames: List[CaGrid]
    current_step: int
    params: CaParams
    risk_map: Optional[np.ndarray]
    contexts: Dict[Tuple[int, int], MitigationContext]
    settlement_cells: List[Tuple[int, int]]
    rural_cells: List[Tuple[int, int]]
    wind_dir_deg: float


def initialize_simulation(
    wind_dir_deg: Optional[float] = None,
    n_steps: int = 12,
    use_hotspots: bool = True,
) -> SimState:
    """Create the initial SimState for the demo."""
    if wind_dir_deg is None:
        wind_dir_deg = config.default_wind_direction_deg()

    params = CaParams(wind_dir_deg=wind_dir_deg)

    cell_grid = build_cell_grid()
    grid = CaGrid().initialize(cell_grid.n_rows, cell_grid.n_cols)

    settlement_cells: List[Tuple[int, int]] = []
    rural_cells: List[Tuple[int, int]] = []
    context_map = build_context_map()

    for row, col in cell_grid.iter_cells():
        if context_map.is_settlement[row, col]:
            settlement_cells.append((row, col))
        elif context_map.is_water[row, col]:
            continue
        else:
            rural_cells.append((row, col))

    if use_hotspots:
        try:
            df = load_firms_hotspots()
            dataset = build_fire_dataset(df, bounding_box=cell_grid.__dict__ if hasattr(cell_grid, "__dict__") else None)
            seeded = seed_from_hotspots(grid, dataset.hotspots, cell_grid)
        except Exception:
            seeded = 0
    else:
        seeded = 0

    if seeded == 0:
        center_row = cell_grid.n_rows // 2
        center_col = cell_grid.n_cols // 2
        seed_cell(grid, center_row, center_col, CELLState.BURNING)
        seeded = 1

    frames = run_simulation(grid, steps=n_steps, params=params)
    risk_map = predict_risk_map(
        None, context_map, wind_dir_deg=wind_dir_deg,
        bounding_box=config.bounding_box(), cell_grid=cell_grid,
    )

    contexts = build_mitigation_contexts(
        grid, settlement_cells, rural_cells, risk_map=risk_map, wind_dir_deg=wind_dir_deg,
    )

    return SimState(
        grid=grid,
        frames=frames,
        current_step=0,
        params=params,
        risk_map=risk_map,
        contexts=contexts,
        settlement_cells=settlement_cells,
        rural_cells=rural_cells,
        wind_dir_deg=wind_dir_deg,
    )


def seed_cell(grid: CaGrid, row: int, col: int, state: CELLState = CELLState.BURNING) -> None:
    from src.ca import seed_cell as _seed
    _seed(grid, row, col, state)


def step_forward(state: SimState) -> SimState:
    """Advance the simulation by one step."""
    next_grid = state.frames[min(len(state.frames) - 1, state.current_step + 1)].clone()
    new_contexts = build_mitigation_contexts(
        next_grid,
        state.settlement_cells,
        state.rural_cells,
        risk_map=state.risk_map,
        wind_dir_deg=state.wind_dir_deg,
    )
    return SimState(
        grid=next_grid,
        frames=state.frames,
        current_step=state.current_step + 1,
        params=state.params,
        risk_map=state.risk_map,
        contexts=new_contexts,
        settlement_cells=state.settlement_cells,
        rural_cells=state.rural_cells,
        wind_dir_deg=state.wind_dir_deg,
    )


def risk_at(state: SimState, row: int, col: int) -> float:
    if state.risk_map is None:
        return 0.0
    if 0 <= row < state.risk_map.shape[0] and 0 <= col < state.risk_map.shape[1]:
        return float(state.risk_map[row, col])
    return 0.0


def mitigation_for(state: SimState, row: int, col: int) -> List[Dict[str, str]]:
    ctx = state.contexts.get((row, col))
    if ctx is None:
        return []
    from src.mitigation import actions_for
    return format_actions_for_display(actions_for(ctx))


def state_distribution(state: SimState) -> Dict[str, int]:
    return state.grid.summary()
