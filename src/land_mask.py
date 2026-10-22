"""Land mask for the island-wide risk map.

The Kalimantan-wide surface is a coarse rectangle over 108.8-119.1 E and
4.2 S-7.3 N, so a large share of its cells fall in the Java Sea, the Karimata
Strait or the South China Sea. Drawing a risk circle for those cells is visual
noise: there is no fuel at sea, and the heuristic behind them has no OSM or
FIRMS support outside the demo box anyway.

``assets/geo/kalimantan_land.geojson`` is a simplified coastline clipped to that
rectangle, derived from Natural Earth 1:50m land (public domain,
https://www.naturalearthdata.com/). Rebuild it with::

    python -m src.land_mask build --source data/raw/ne_50m_land.geojson

The mask is a pure geometry test. If the file or shapely is unavailable the
callers fall back to drawing every cell, exactly as before.
"""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Tuple

import numpy as np

# Simplified coastline shipped with the repository (coordinates rounded to
# 4 decimals, rings simplified to ~1 km).
LAND_GEOJSON = Path(__file__).resolve().parent.parent / "assets" / "geo" / "kalimantan_land.geojson"

# Kalimantan-wide extent used by the risk map (kept in sync with config).
ISLAND_BBOX = (108.8, -4.2, 119.1, 7.3)

# Rings smaller than this (in square degrees, ~10 km^2 near the equator) are
# dropped: the coarse 0.15 degree grid can never land a cell centre on them.
MIN_ISLAND_AREA_DEG2 = 0.001


@lru_cache(maxsize=1)
def _land_geometry(path: str) -> Any:
    """Load the bundled coastline as one shapely geometry (cached)."""
    from shapely.geometry import shape
    from shapely.ops import unary_union

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    polygons = [shape(feature["geometry"]) for feature in data["features"]]
    if not polygons:
        return None
    return unary_union(polygons)


def land_geometry(path: Optional[Path] = None) -> Any:
    """Return the union of the bundled land polygons, or None if unavailable."""
    target = Path(path) if path is not None else LAND_GEOJSON
    if not target.exists():
        return None
    try:
        return _land_geometry(str(target))
    except Exception:
        return None


def land_cell_mask(
    bbox: Tuple[float, float, float, float],
    n_rows: int,
    n_cols: int,
    path: Optional[Path] = None,
) -> np.ndarray:
    """Boolean (n_rows, n_cols) mask: True where the cell centre is on land.

    ``bbox`` is ``(min_lon, min_lat, max_lon, max_lat)`` and row 0 is the
    northern edge, matching ``CellGrid`` everywhere else in the project. A
    missing coastline or shapely installation returns an all-True mask so the
    map still renders (just with the sea dots back).
    """
    all_land = np.ones((n_rows, n_cols), dtype=bool)
    geometry = land_geometry(path)
    if geometry is None:
        return all_land

    try:
        from shapely import contains_xy
    except Exception:  # shapely < 2.0
        return all_land

    min_lon, min_lat, max_lon, max_lat = bbox
    d_lat = (max_lat - min_lat) / max(1, n_rows)
    d_lon = (max_lon - min_lon) / max(1, n_cols)

    lats = max_lat - (np.arange(n_rows) + 0.5) * d_lat
    lons = min_lon + (np.arange(n_cols) + 0.5) * d_lon
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    return np.asarray(contains_xy(geometry, lon_grid, lat_grid), dtype=bool)


def build_land_geojson(
    source: Path,
    target: Optional[Path] = None,
    bbox: Tuple[float, float, float, float] = ISLAND_BBOX,
    simplify_deg: float = 0.01,
) -> Path:
    """Clip and simplify a Natural Earth land file for the island-wide map."""
    from shapely.geometry import box, mapping, shape
    from shapely.ops import unary_union

    data = json.loads(Path(source).read_text(encoding="utf-8"))
    clip = box(*bbox)
    pieces = []
    for feature in data["features"]:
        geometry = shape(feature["geometry"])
        if geometry.intersects(clip):
            clipped = geometry.intersection(clip)
            if not clipped.is_empty:
                pieces.append(clipped)
    if not pieces:
        raise ValueError(f"no land found inside {bbox} in {source}")

    land = unary_union(pieces).simplify(simplify_deg, preserve_topology=True)
    polygons = [land] if land.geom_type == "Polygon" else list(land.geoms)
    features = [
        {
            "type": "Feature",
            "properties": {"source": "Natural Earth 1:50m land, simplified"},
            "geometry": _round_geometry(mapping(polygon)),
        }
        for polygon in polygons
        if polygon.area >= MIN_ISLAND_AREA_DEG2
    ]
    if not features:
        raise ValueError("every land polygon was smaller than MIN_ISLAND_AREA_DEG2")

    out = Path(target) if target is not None else LAND_GEOJSON
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}),
        encoding="utf-8",
    )
    _land_geometry.cache_clear()
    return out


def _round_geometry(geometry: Any) -> Any:
    """Round GeoJSON coordinates to 4 decimals (~11 m) to keep the file small."""
    if isinstance(geometry, dict):
        if geometry.get("type") == "Polygon":
            return {
                "type": "Polygon",
                "coordinates": [_round_ring(ring) for ring in geometry["coordinates"]],
            }
        if geometry.get("type") == "MultiPolygon":
            return {
                "type": "MultiPolygon",
                "coordinates": [
                    [_round_ring(ring) for ring in polygon]
                    for polygon in geometry["coordinates"]
                ],
            }
        return geometry
    return geometry


def _round_ring(ring: Any) -> list:
    return [[round(float(x), 4), round(float(y), 4)] for x, y in ring]


def main(argv: Optional[list] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build the island land mask.")
    parser.add_argument("command", choices=["build"])
    parser.add_argument(
        "--source",
        default="data/raw/ne_50m_land.geojson",
        help="Natural Earth land GeoJSON (download from naturalearthdata.com)",
    )
    parser.add_argument("--target", default=str(LAND_GEOJSON))
    args = parser.parse_args(argv)

    path = build_land_geojson(Path(args.source), Path(args.target))
    geometry = land_geometry(path)
    mask = land_cell_mask(ISLAND_BBOX, 77, 69, path=path)
    print(
        f"wrote {path} ({path.stat().st_size / 1024:.0f} KiB), "
        f"{mask.sum()} of {mask.size} island cells on land"
    )
    if geometry is None:
        print("warning: written file could not be reloaded", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
