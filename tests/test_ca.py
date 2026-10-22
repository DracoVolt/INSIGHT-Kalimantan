"""Tests for the Cellular Automaton core."""

from __future__ import annotations

import numpy as np
import pytest

from src.ca import (
    CaGrid,
    CaParams,
    CELLState,
    run_simulation,
    seed_cell,
    step,
    step_explanation,
    spread_probability,
    wind_alignment_factor,
)


def test_grid_initialize_sets_correct_shape():
    grid = CaGrid().initialize(n_rows=5, n_cols=7)
    assert grid.n_rows == 5
    assert grid.n_cols == 7
    assert grid.states.shape == (5, 7)


def test_grid_all_cells_start_healthy():
    grid = CaGrid().initialize(n_rows=3, n_cols=3)
    for r in range(grid.n_rows):
        for c in range(grid.n_cols):
            assert grid.state_at(r, c) == CELLState.HEALTHY


def test_seed_single_cell():
    grid = CaGrid().initialize(n_rows=4, n_cols=4)
    seed_cell(grid, 1, 2)
    assert grid.state_at(1, 2) == CELLState.BURNING
    assert grid.state_at(0, 0) == CELLState.HEALTHY


def test_neighbors_are_moore_neighborhood():
    grid = CaGrid().initialize(n_rows=3, n_cols=3)
    neigh = grid.neighbors(1, 1)
    assert (0, 0) in neigh
    assert (0, 1) in neigh
    assert (0, 2) in neigh
    assert (1, 0) in neigh
    assert (1, 2) in neigh
    assert (2, 0) in neigh
    assert (2, 1) in neigh
    assert (2, 2) in neigh
    assert len(neigh) == 8


def test_neighbors_clamp_at_edges():
    grid = CaGrid().initialize(n_rows=3, n_cols=3)
    assert grid.neighbors(0, 0) == [(0, 1), (1, 0), (1, 1)]


def test_step_burning_becomes_burned():
    grid = CaGrid().initialize(n_rows=3, n_cols=3)
    seed_cell(grid, 1, 1)
    params = CaParams(wind_dir_deg=0, random_seed=123)
    grid = step(grid, params=params)
    assert grid.state_at(1, 1) == CELLState.BURNED


def test_step_can_ignite_neighbor():
    grid = CaGrid().initialize(n_rows=3, n_cols=3)
    seed_cell(grid, 1, 1)
    params = CaParams(wind_dir_deg=0, random_seed=7, spread_base=1.0)
    grid = step(grid, params=params)
    # With spread_base=1.0, all neighbors should ignite.
    for r, c in grid.neighbors(1, 1):
        assert grid.state_at(r, c) == CELLState.IGNITING


def test_run_simulation_produces_frames():
    grid = CaGrid().initialize(n_rows=5, n_cols=5)
    seed_cell(grid, 2, 2)
    params = CaParams(wind_dir_deg=0, random_seed=1, spread_base=0.9)
    frames = run_simulation(grid, steps=3, params=params)
    assert len(frames) == 4  # initial frame + 3 steps
    assert frames[0].state_at(2, 2) == CELLState.BURNING
    assert frames[-1].state_at(2, 2) == CELLState.BURNED


def test_peat_risk_cell_state():
    peat = np.zeros((3, 3), dtype=bool)
    peat[0, 0] = True
    grid = CaGrid().initialize(n_rows=3, n_cols=3, peat_risk_mask=peat)
    assert grid.state_at(0, 0) == CELLState.PEAT_RISK
    assert bool(grid.peat_risk[0, 0]) is True
    assert bool(grid.peat_risk[1, 1]) is False


def test_wind_alignment_factor_directionality():
    center_row = 1.0
    center_col = 1.0
    # Meteorological convention: 0 deg means wind FROM the north, so the fire is
    # pushed southward (row index increases southward -> dr=+1 is downwind).
    align_downwind = wind_alignment_factor(1, 1, 2, 1, 0.0, center_row, center_col)
    assert align_downwind > 0.9
    align_upwind = wind_alignment_factor(1, 1, 0, 1, 0.0, center_row, center_col)
    assert align_upwind < 0.1

    # 90 deg means wind FROM the east, so it pushes the fire westward.
    align_west = wind_alignment_factor(1, 1, 1, 0, 90.0, center_row, center_col)
    assert align_west > 0.9
    align_east = wind_alignment_factor(1, 1, 1, 2, 90.0, center_row, center_col)
    assert align_east < 0.1

    # A step perpendicular to the wind gets exactly half the weight.
    perp = wind_alignment_factor(1, 1, 1, 2, 0.0, center_row, center_col)
    assert abs(perp - 0.5) < 1e-9


def test_spread_probability_matches_documented_range():
    params = CaParams(wind_dir_deg=0)
    downwind_peat = spread_probability(1, 1, 2, 1, True, params, 1.0, 1.0)
    upwind_plain = spread_probability(1, 1, 0, 1, False, params, 1.0, 1.0)
    assert abs(downwind_peat - 0.60) < 1e-9
    assert abs(upwind_plain - 0.15) < 1e-9


def test_spread_probability_bounds():
    params = CaParams(wind_dir_deg=0, spread_base=0.1, random_seed=1)
    p = spread_probability(0, 0, 0, 1, False, params, 1.0, 1.0)
    assert 0.0 <= p <= 1.0


def test_step_explanation_is_nonempty():
    params = CaParams(wind_dir_deg=90)
    text = step_explanation(params)
    assert isinstance(text, str)
    assert len(text) > 0


def test_summary_counts_are_nonnegative():
    grid = CaGrid().initialize(n_rows=4, n_cols=4)
    summary = grid.summary()
    for k, v in summary.items():
        if k not in ("n_rows", "n_cols"):
            assert v >= 0
