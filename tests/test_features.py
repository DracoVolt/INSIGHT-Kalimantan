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


def test_cell_grid_rows_run_north_to_south():
    grid = build_cell_grid()
    _lon_n, lat_north = grid.row_col_to_center(0, 0)
    _lon_s, lat_south = grid.row_col_to_center(grid.n_rows - 1, 0)
    assert lat_north > lat_south
    # Cell centres stay inside the box plus at most one rounding cell, because
    # the grid uses ceil() to cover the whole bounding box.
    assert lat_north <= grid.max_lat
    assert lat_south >= grid.min_lat - grid.spacing_deg

    # A point maps back to the cell whose centre it belongs to.
    lon, lat = grid.row_col_to_center(10, 20)
    assert grid.lon_lat_to_row_col(lon, lat) == (10, 20)

    west, south, east, north = grid.cell_bounds(0, 0)
    assert north > south and east > west


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


def test_nearest_feature_distance_matches_brute_force():
    """The vectorized EDT must equal the brute-force nearest-cell distance."""
    from src.features import nearest_feature_distance

    rng = np.random.default_rng(0)
    mask = rng.random((9, 11)) < 0.15
    mask[0, 0] = True  # ensure at least one site

    dist = nearest_feature_distance(mask)

    site_rows, site_cols = np.nonzero(mask)
    expected = np.empty_like(dist)
    for r in range(dist.shape[0]):
        for c in range(dist.shape[1]):
            expected[r, c] = float(
                np.sqrt(np.min((site_rows - r) ** 2 + (site_cols - c) ** 2))
            )

    assert dist.shape == mask.shape
    assert np.allclose(dist, expected)
    assert float(dist[0, 0]) == 0.0  # distance at a site is zero


def test_nearest_feature_distance_empty_mask_uses_sentinel():
    from src.features import nearest_feature_distance

    mask = np.zeros((5, 7), dtype=bool)
    dist = nearest_feature_distance(mask)
    assert dist.shape == (5, 7)
    assert np.all(dist == float(5 + 7))


def test_context_map_distances_match_brute_force():
    """End-to-end: ContextMap lookups equal brute force on a seeded snapshot."""
    from src.osm_stub import make_kalimantan_stub_snapshot

    grid = build_cell_grid()
    ctx = build_context_map(
        osm_snapshot=make_kalimantan_stub_snapshot(), cell_grid=grid
    )

    water_rows, water_cols = np.nonzero(ctx.is_water)
    settle_rows, settle_cols = np.nonzero(ctx.is_settlement)
    assert len(water_rows) > 0 and len(settle_rows) > 0

    for (r, c) in [(0, 0), (29, 29), (grid.n_rows - 1, grid.n_cols - 1)]:
        exp_water = np.sqrt(
            np.min((water_rows - r) ** 2 + (water_cols - c) ** 2)
        )
        exp_settle = np.sqrt(
            np.min((settle_rows - r) ** 2 + (settle_cols - c) ** 2)
        )
        assert np.isclose(ctx.nearest_water_distance(r, c), exp_water)
        assert np.isclose(ctx.nearest_settlement_distance(r, c), exp_settle)


def test_feature_row_label_is_optional():
    from src.features import FeatureRow
    row = FeatureRow(row=0, col=0, day_iso="2024-01-01", features={"x": 1.0}, label=None)
    assert row.label is None
    assert row.features["x"] == 1.0
