"""Lightweight data stubs for tests and offline exploration."""

from __future__ import annotations

from typing import List, Tuple

from src.fire_data import CellGrid, FireDataset, Hotspot


def make_fake_grid(bounding_box: Tuple[float, float, float, float] = (-2.6, 2.4, -0.6, 4.4)) -> CellGrid:
    min_lon, min_lat, max_lon, max_lat = bounding_box
    spacing = 0.035
    n_cols = max(1, int((max_lon - min_lon) / spacing))
    n_rows = max(1, int((max_lat - min_lat) / spacing))
    return CellGrid(
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        spacing_deg=spacing,
        n_rows=n_rows,
        n_cols=n_cols,
    )


def make_fake_hotspots(n: int = 3) -> List[Hotspot]:
    import datetime
    base = datetime.datetime(2024, 1, 1)
    return [
        Hotspot(
            lon=-1.6 + (i % 5) * 0.05,
            lat=3.4 + (i // 5) * 0.05,
            datetime=base + datetime.timedelta(days=i),
            confidence=90.0 + i,
            source="VIIRS",
            frp=50.0 + i * 10.0,
        )
        for i in range(n)
    ]


def make_fake_dataset(
    bounding_box: Tuple[float, float, float, float] = (-2.6, 2.4, -0.6, 4.4),
    days: int = 2,
) -> FireDataset:
    grid = make_fake_grid(bounding_box)
    import datetime
    base = datetime.datetime(2024, 1, 1)
    hotspots = make_fake_hotspots(n=4)
    labels: dict = {}
    for row, col in grid.iter_cells():
        for d in range(days):
            day_iso = (base + datetime.timedelta(days=d)).strftime("%Y-%m-%d")
            labels[(row, col, day_iso)] = 0
    for hs in hotspots:
        try:
            row, col = grid.lon_lat_to_row_col(hs.lon, hs.lat)
        except ValueError:
            continue
        day_iso = hs.datetime.strftime("%Y-%m-%d")
        labels[(row, col, day_iso)] = 1
    days_iso = sorted({hs.datetime.strftime("%Y-%m-%d") for hs in hotspots})
    return FireDataset(
        bounding_box=bounding_box,
        hotspots=hotspots,
        cell_grid=grid,
        labeled_days=days_iso,
        labels=labels,
    )
