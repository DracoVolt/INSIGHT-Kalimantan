"""Tests for feature engineering shapes and basic invariants."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features import (
    build_context_map,
    build_feature_table,
    feature_names,
    hotspot_history_for_cell,
)
from src.fire_data import CellGrid, build_cell_grid, FireDataset


def test_feature_names_are_nonempty():
    names = feature_names()
    assert len(names) > 0
    assert isinstance(names, tuple)


def test_context_map_shape_matches_grid():
    grid = build_cell_grid()
    ctx = build_context_map()
    assert ctx.n_rows == grid.n_rows
    assert ctx.n_cols == grid.n_cols
    assert ctx.is_water.shape == (grid.n_rows, grid.n_cols)
    assert ctx.is_settlement.shape == (grid.n_rows, grid.n_cols)
    assert ctx.is_peat_risk.shape == (grid.n_rows, grid.n_cols)


def test_context_map_blank_when_no_osm():
    ctx = build_context_map()
    assert int(ctx.is_water.sum()) == 0
    assert int(ctx.is_settlement.sum()) == 0
    assert int(ctx.is_peat_risk.sum()) == 0


def test_nearest_distance_is_finite():
    grid = build_cell_grid()
    ctx = build_context_map()
    d = ctx.nearest_water_distance(0, 0)
    assert np.isfinite(d) or d == float(grid.n_rows + grid.n_cols)


def test_feature_table_has_expected_columns():
    grid = build_cell_grid()
    dataset = FireDataset(
        bounding_box=grid.__dict__ if hasattr(grid, "__dict__") else None,
        hotspots=[],
        cell_grid=grid,
        labeled_days=["2024-01-01"],
        labels={},
    )
    ctx = build_context_map()
    df = build_feature_table(dataset, context_map=ctx, wind_dir_deg=90.0)
    expected_base = set(feature_names())
    actual = set(df.columns) - {"label", "row", "col", "day_iso"}
    assert expected_base == actual


def test_feature_table_has_rows_for_cells_and_days():
    grid = build_cell_grid()
    dataset = FireDataset(
        bounding_box=grid.__dict__ if hasattr(grid, "__dict__") else None,
        hotspots=[],
        cell_grid=grid,
        labeled_days=["2024-01-01", "2024-01-02"],
        labels={},
    )
    ctx = build_context_map()
    df = build_feature_table(dataset, context_map=ctx, wind_dir_deg=90.0)
    expected_rows = grid.n_rows * grid.n_cols * len(dataset.labeled_days)
    assert len(df) == expected_rows


def test_hotspot_history_has_expected_keys():
    rows = hotspot_history_for_cell(
        hotspots=[],
        row=0,
        col=0,
        cell_grid=build_cell_grid(),
        days=["2024-01-01"],
        cell_day_labels={},
    )
    assert "has_hotspot_last_1_day" in rows
    assert "has_hotspot_last_3_days" in rows
    assert "has_hotspot_last_7_days" in rows
    assert "hotspot_count_last_7_days" in rows


def test_feature_row_label_is_optional():
    from src.features import FeatureRow
    row = FeatureRow(row=0, col=0, day_iso="2024-01-01", features={"x": 1.0}, label=None)
    assert row.label is None
    assert row.features["x"] == 1.0
