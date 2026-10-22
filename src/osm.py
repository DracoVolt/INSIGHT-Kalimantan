"""OpenStreetMap data fetching and parsing for the demo bounding box.

This module contains a small Overpass helper and lightweight parsing so the rest
of the project can build per-cell context (water, settlements, land cover) from
OSM features.

For a 1-month science project, the goal is transparency and reproducibility,
not a full GIS pipeline.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from . import config

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class OsmFeature:
    """A single OSM element relevant to the demo."""

    element_id: str
    element_type: str  # "node", "way", or "relation"
    tags: Dict[str, str]
    geometry: Optional[List[Tuple[float, float]]] = None
    center: Optional[Tuple[float, float]] = None


@dataclass
class OsmSnapshot:
    """A small parsed OSM extract for the bounding box."""

    bounding_box: Tuple[float, float, float, float]
    features: List[OsmFeature]
    timestamp: float


# ---------------------------------------------------------------------------
# Overpass helpers
# ---------------------------------------------------------------------------


# Tag keys the feature builder actually reads (water, settlements, peat).
# Buildings and roads are not used as features, so fetching them would only
# inflate the Overpass payload and slow the first render.
OSM_FEATURE_TAGS = ("natural", "waterway", "water", "place", "landuse")


def _build_overpass_query(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    tags: Optional[List[str]] = None,
    timeout: int = 60,
    max_rows: Optional[int] = None,
) -> str:
    """Build an Overpass QL query for the demo bounding box.

    This is intentionally simple. It fetches nodes and ways with any of the
    requested tags inside the bounding box.
    """
    # Overpass bounding boxes are (south, west, north, east) = (lat, lon, lat, lon).
    box = f"{min_lat},{min_lon},{max_lat},{max_lon}"
    keys = list(tags) if tags else list(OSM_FEATURE_TAGS)

    # One statement per key uses Overpass' tag indexes; a single key-regex
    # filter would force a scan and time out even on a small bbox.
    statements = []
    for key in keys:
        statements.append(f'  node["{key}"]({box});')
        statements.append(f'  way["{key}"]({box});')

    query = (
        f"[out:json][timeout:{timeout}];\n(\n"
        + "\n".join(statements)
        + "\n);\nout center;"
    )
    return query


def build_tag_filter(tags: Optional[List[str]] = None) -> str:
    """Build a valid Overpass key-regex filter for the requested tag keys.

    Overpass rejects a union of several ``["key"]`` filters, which is why the
    earlier query returned HTTP 400. A single key-regex filter is valid QL and
    matches any element carrying one of the requested keys.
    """
    keys = list(tags) if tags else list(OSM_FEATURE_TAGS)
    pattern = "|".join(re.escape(key) for key in keys)
    return f'[~"^({pattern})$"~"."]'


def fetch_overpass(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    tags: Optional[List[str]] = None,
    timeout_sec: Optional[int] = None,
    max_rows: Optional[int] = None,
    retries: int = 3,
    sleep_between_retries: float = 3.0,
) -> Dict[str, Any]:
    """Fetch JSON from Overpass for the given bounding box.

    This is a thin wrapper around the Overpass endpoint. It retries on failure
    and raises the last exception if all retries fail.
    """
    if timeout_sec is None:
        timeout_sec = config.osm_query_timeout()

    endpoint = config.OVERPASS_ENDPOINT
    query = _build_overpass_query(
        min_lon, min_lat, max_lon, max_lat, tags=tags,
        timeout=timeout_sec, max_rows=max_rows,
    )

    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                endpoint,
                data={"data": query},
                timeout=timeout_sec + 30,
                headers={"User-Agent": "INSIGHT-Kalimantan/0.1.0 (science project)"},
            )
            resp.raise_for_status()
            payload = resp.json()
            return payload
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(sleep_between_retries)
            else:
                raise last_exc from last_exc

    # Should not be reached because the loop raises, but keep the type checker happy.
    raise RuntimeError("Unexpected exit from fetch_overpass retry loop")


def parse_overpass_json(payload: Dict[str, Any]) -> List[OsmFeature]:
    """Parse an Overpass JSON response into a list of OsmFeature."""
    elements = payload.get("elements", [])
    features: List[OsmFeature] = []
    for elem in elements:
        elem_type = elem.get("type", "unknown")
        elem_id = str(elem.get("id", ""))
        tags = {str(k): str(v) for k, v in elem.get("tags", {}).items()}

        geometry: Optional[List[Tuple[float, float]]] = None
        center: Optional[Tuple[float, float]] = None

        if elem_type == "node":
            lat = elem.get("lat")
            lon = elem.get("lon")
            if lat is not None and lon is not None:
                center = (float(lat), float(lon))
        else:
            center_entry = elem.get("center")
            if center_entry is not None:
                lat = center_entry.get("lat")
                lon = center_entry.get("lon")
                if lat is not None and lon is not None:
                    center = (float(lat), float(lon))

            if elem_type == "way" and "geometry" in elem:
                geometry = [
                    (float(pt["lat"]), float(pt["lon"]))
                    for pt in elem["geometry"]
                    if pt.get("lat") is not None and pt.get("lon") is not None
                ]

        features.append(
            OsmFeature(
                element_id=elem_id,
                element_type=elem_type,
                tags=tags,
                geometry=geometry,
                center=center,
            )
        )

    return features


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_bounding_box_features(
    bounding_box: Optional[Tuple[float, float, float, float]] = None,
    tags: Optional[List[str]] = None,
) -> OsmSnapshot:
    """Fetch and parse OSM features for the demo bounding box."""
    if bounding_box is None:
        bounding_box = config.bounding_box()

    min_lon, min_lat, max_lon, max_lat = bounding_box
    payload = fetch_overpass(min_lon, min_lat, max_lon, max_lat, tags=tags)
    features = parse_overpass_json(payload)
    return OsmSnapshot(
        bounding_box=bounding_box,
        features=features,
        timestamp=time.time(),
    )


def load_or_fetch_snapshot(max_age_days: float = 7.0) -> OsmSnapshot:
    """Return a cached OSM snapshot, fetching a new one when it is missing or old.

    Training and inference must see the same water/settlement/peat masks, so the
    snapshot is cached on disk (``data/raw/osm_snapshot.json``) and reused by
    both. Overpass is also the slowest part of the first render.
    """
    path = config.data_raw_dir() / "osm_snapshot.json"
    if path.exists():
        age_days = (time.time() - path.stat().st_mtime) / 86400.0
        if age_days <= max_age_days:
            try:
                return load_snapshot(path)
            except (OSError, ValueError, KeyError):
                pass
    snapshot = fetch_bounding_box_features()
    save_snapshot(snapshot, path)
    return snapshot


def save_snapshot(snapshot: OsmSnapshot, path: Optional[Path] = None) -> Path:
    """Save an OsmSnapshot to a JSON file."""
    if path is None:
        path = config.data_raw_dir() / "osm_snapshot.json"
    payload = {
        "bounding_box": list(snapshot.bounding_box),
        "timestamp": snapshot.timestamp,
        "features": [
            {
                "element_id": f.element_id,
                "element_type": f.element_type,
                "tags": f.tags,
                "geometry": f.geometry,
                "center": f.center,
            }
            for f in snapshot.features
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    return path


def load_snapshot(path: Optional[Path] = None) -> OsmSnapshot:
    """Load an OsmSnapshot from a JSON file."""
    if path is None:
        path = config.data_raw_dir() / "osm_snapshot.json"
    payload = json.loads(path.read_text())
    return OsmSnapshot(
        bounding_box=tuple(payload["bounding_box"]),  # type: ignore[arg-type]
        features=[
            OsmFeature(
                element_id=f["element_id"],
                element_type=f["element_type"],
                tags=f["tags"],
                geometry=f.get("geometry"),
                center=f.get("center"),
            )
            for f in payload["features"]
        ],
        timestamp=float(payload["timestamp"]),
    )


# ---------------------------------------------------------------------------
# Convenience helpers for the demo
# ---------------------------------------------------------------------------


def features_in_bbox(
    features: List[OsmFeature],
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
) -> List[OsmFeature]:
    """Filter features to those whose center lies within a bounding box."""
    out: List[OsmFeature] = []
    for f in features:
        if f.center is None:
            continue
        lat, lon = f.center
        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
            out.append(f)
    return out


def is_settlement_feature(f: OsmFeature) -> bool:
    """Return True if the feature looks like a settlement place."""
    place = f.tags.get("place", "").lower()
    return place in {p.lower() for p in config.OSM_SETTLEMENT_PLACE_TAGS}


def is_water_feature(f: OsmFeature) -> bool:
    """Return True if the feature looks like water-related."""
    natural = f.tags.get("natural", "").lower()
    water = f.tags.get("water", "").lower()
    waterway = f.tags.get("waterway", "").lower()
    return bool(natural in {"water", "coastline"} or water or waterway)


def is_peat_or_wetland_feature(f: OsmFeature) -> bool:
    """Return True if the feature looks peat- or wetland-related.

    OSM tagging for peat is inconsistent, so this is a best-effort heuristic
    for the demo.
    """
    wetland = f.tags.get("natural", "").lower() == "wetland"
    landuse = f.tags.get("landuse", "").lower()
    peat = landuse in {"peat", "peat_extraction"}
    return wetland or peat


def feature_summary(snapshot: OsmSnapshot) -> Dict[str, Any]:
    """Return a small summary of an OsmSnapshot for reporting/debugging."""
    features = snapshot.features
    by_type: Dict[str, int] = {}
    n_settlement = 0
    n_water = 0
    n_peat = 0
    for f in features:
        by_type[f.element_type] = by_type.get(f.element_type, 0) + 1
        if is_settlement_feature(f):
            n_settlement += 1
        if is_water_feature(f):
            n_water += 1
        if is_peat_or_wetland_feature(f):
            n_peat += 1
    return {
        "bounding_box": list(snapshot.bounding_box),
        "n_features": len(features),
        "by_type": by_type,
        "n_settlement": n_settlement,
        "n_water": n_water,
        "n_peat_like": n_peat,
    }
