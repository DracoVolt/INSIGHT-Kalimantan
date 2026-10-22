"""Lightweight OSM snapshot stub for offline demo use.

When no live Overpass query is available (e.g. offline science-fair booth),
the app can fall back to this pre-seeded snapshot so the context map,
mitigation panel, and risk map still show meaningful Indonesian content.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from src.osm import OsmFeature, OsmSnapshot
from src import config


def make_kalimantan_stub_snapshot() -> OsmSnapshot:
    """Return a small OsmSnapshot with representative Kalimantan features.

    This is NOT real OSM data; it is a teaching stub that places a handful of
    water features (rivers/lakes), settlement places, and peat/wetland cells
    inside the demo bounding box so the offline demo still shows inland-focused
    content.
    """
    bbox = config.bounding_box()
    min_lon, min_lat, max_lon, max_lat = bbox

    features: List[OsmFeature] = []

    def _add(tags: dict, lat: float, lon: float) -> None:
        if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
            return
        features.append(
            OsmFeature(
                element_id=f"stub-{len(features)}",
                element_type="node",
                tags=tags,
                center=(lat, lon),
            )
        )

    # A few river / waterway points along the Kahayan / Sebangau area.
    _add({"waterway": "river", "name": "Kahayan"}, -2.6, 113.0)
    _add({"waterway": "river", "name": "Sebangau"}, -2.9, 113.6)
    _add({"natural": "water", "name": "Lake"}, -3.1, 114.0)
    _add({"waterway": "stream"}, -2.2, 114.2)

    # A few settlement places.
    _add({"place": "village", "name": "Sungai"},
         -2.7, 113.1)
    _add({"place": "hamlet", "name": "Tumbang"},
         -3.0, 113.3)
    _add({"place": "village", "name": "Bako"},
         -2.4, 114.1)

    # A few peat / wetland cells.
    _add({"natural": "wetland", "wetland": "peat swamp forest"},
         -2.8, 113.4)
    _add({"landuse": "peat"}, -3.2, 114.3)
    _add({"natural": "wetland"}, -2.3, 113.8)

    return OsmSnapshot(
        bounding_box=bbox,
        features=features,
        timestamp=0.0,
    )
