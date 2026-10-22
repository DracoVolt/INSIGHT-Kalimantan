"""Tests for the island-wide land mask used by the Kalimantan risk map.

The map used to scatter risk circles over the Java Sea and the South China Sea.
These tests pin the two behaviours that matter: land cells survive, sea cells do
not, and a missing coastline degrades gracefully to the old draw-everything map.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src import config
from src.land_mask import (
    ISLAND_BBOX,
    build_land_geojson,
    land_cell_mask,
    land_geometry,
)


def _grid_shape() -> tuple[int, int]:
    min_lon, min_lat, max_lon, max_lat = config.KALIMANTAN_BBOX
    n_rows = max(1, int(np.ceil((max_lat - min_lat) / config.KALIMANTAN_SPACING_DEG)))
    n_cols = max(1, int(np.ceil((max_lon - min_lon) / config.KALIMANTAN_SPACING_DEG)))
    return n_rows, n_cols


def _cell_of(lat: float, lon: float) -> tuple[int, int]:
    min_lon, min_lat, max_lon, max_lat = config.KALIMANTAN_BBOX
    n_rows, n_cols = _grid_shape()
    d_lat = (max_lat - min_lat) / n_rows
    d_lon = (max_lon - min_lon) / n_cols
    return int((max_lat - lat) / d_lat), int((lon - min_lon) / d_lon)


def test_bundled_coastline_is_present_and_clipped():
    geometry = land_geometry()
    assert geometry is not None
    min_lon, min_lat, max_lon, max_lat = ISLAND_BBOX
    west, south, east, north = geometry.bounds
    assert west >= min_lon - 1e-6 and east <= max_lon + 1e-6
    assert south >= min_lat - 1e-6 and north <= max_lat + 1e-6


def test_land_mask_keeps_inland_and_drops_open_sea():
    n_rows, n_cols = _grid_shape()
    mask = land_cell_mask(config.KALIMANTAN_BBOX, n_rows, n_cols)
    assert mask.shape == (n_rows, n_cols)

    for lat, lon in [(-2.2, 113.9), (-0.02, 109.34), (-3.32, 114.59)]:
        assert mask[_cell_of(lat, lon)], f"{lat}, {lon} should be land"

    for lat, lon in [(3.0, 109.0), (-3.9, 111.0), (0.5, 118.5)]:
        assert not mask[_cell_of(lat, lon)], f"{lat}, {lon} should be sea"

    # The rectangle is roughly half water: keep a sanity band rather than an
    # exact count so a finer coastline does not break the test.
    land_fraction = mask.mean()
    assert 0.3 < land_fraction < 0.7


def test_missing_coastline_falls_back_to_every_cell(tmp_path: Path):
    n_rows, n_cols = _grid_shape()
    mask = land_cell_mask(
        config.KALIMANTAN_BBOX, n_rows, n_cols, path=tmp_path / "absent.geojson"
    )
    assert mask.all()


def test_build_land_geojson_clips_to_the_requested_bbox(tmp_path: Path):
    source = tmp_path / "land.geojson"
    square = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[112.0, -3.0], [114.0, -3.0], [114.0, -1.0], [112.0, -1.0], [112.0, -3.0]]
                    ],
                },
            }
        ],
    }
    source.write_text(json.dumps(square), encoding="utf-8")
    target = tmp_path / "clipped.geojson"

    build_land_geojson(source, target, bbox=(112.5, -2.5, 113.5, -1.5), simplify_deg=0.0)

    geometry = land_geometry(target)
    assert geometry is not None
    assert geometry.bounds == (112.5, -2.5, 113.5, -1.5)

    mask = land_cell_mask((112.5, -2.5, 113.5, -1.5), 4, 4, path=target)
    assert mask.all()
