"""iNaturalist v2 observations fetcher for the Kalimantan demo box.

v2 is the next-gen endpoint: https://api.inaturalist.org/v2/observations
It accepts the same search parameters as v1 (taxon_name, bbox, quality_grade,
etc.) and paginates the same way (page + per_page, max 200 per page).

We request explicit fields so geolocation is returned in the response; by
default v2 returns only very lightweight observation records.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, List, Optional, Tuple

V2_BASE = "https://api.inaturalist.org/v2/observations"

TAXA: dict[str, str] = {
    "Orangutan": "Orangutan",
    "Proboscis_monkey": "Proboscis monkey",
    "Rafflesia": "Rafflesia arnoldii",
    "Nepenthes": "Nepenthes",
}

# Which fields to request so we get geolocation back (v2 returns very little by default).
V2_FIELDS = [
    "geojson",
    "location",
    "latitude",
    "longitude",
    "taxon",
    "id",
    "uuid",
]


def _fetch_v2(
    taxon_query: str,
    bbox: Tuple[float, float, float, float],
    target: int = 500,
    max_pages: int = 40,
    timeout_sec: int = 8,
) -> List[Tuple[float, float]]:
    """Fetch research-grade iNaturalist v2 observations for one taxon within bbox."""
    pts: List[Tuple[float, float]] = []
    page = 1

    while page <= max_pages and len(pts) < target:
        tn = urllib.parse.quote(taxon_query, safe="")
        # iNaturalist reads bbox as swlat,swlng,nelat,nelng; callers pass
        # (min_lon, min_lat, max_lon, max_lat). Sending the lon/lat order made
        # the API ignore the box and return observations from anywhere.
        min_lon, min_lat, max_lon, max_lat = bbox
        bbox_s = f"{min_lat},{min_lon},{max_lat},{max_lon}"
        qs = (
            "page=%d&per_page=%d&taxon_name=%s&bbox=%s"
            "&order=desc&quality_grade=research"
            "&fields=" + ",".join(V2_FIELDS)
        ) % (page, 200, tn, bbox_s)
        url = V2_BASE + "?" + qs

        try:
            with urllib.request.urlopen(url, timeout=timeout_sec) as resp:
                payload = json.loads(resp.read())
        except urllib.error.HTTPError:
            # Many taxa return empty / 404-style results outside their range.
            break
        except Exception:
            # Network noise: stop paging rather than hanging the demo.
            break

        results = payload.get("results") or []
        if not results:
            break

        for obs in results:
            p = _extract_coords(obs)
            if p is not None:
                pts.append(p)

        page += 1
        if len(results) < 200:
            break
        time.sleep(0.2)

    return pts


def _extract_coords(obs: Any) -> Optional[Tuple[float, float]]:
    gj = obs.get("geojson")
    if isinstance(gj, dict) and gj.get("coordinates"):
        lon, lat = gj["coordinates"]
        try:
            return float(lat), float(lon)
        except (TypeError, ValueError):
            pass
    loc = obs.get("location")
    if isinstance(loc, str):
        parts = loc.split(",")
        if len(parts) >= 2:
            try:
                return float(parts[0].strip()), float(parts[1].strip())
            except (TypeError, ValueError):
                pass
    if obs.get("latitude") is not None and obs.get("longitude") is not None:
        try:
            return float(obs["latitude"]), float(obs["longitude"])
        except (TypeError, ValueError):
            pass
    return None


def fetch_all(
    bbox: Tuple[float, float, float, float] = (112.5, -3.5, 114.5, -1.5),
    target_per_taxon: int = 500,
    timeout_sec: int = 8,
) -> dict[str, List[Tuple[float, float]]]:
    """Return one coordinate list per demo taxon from the v2 API.

    The taxa are fetched concurrently: each one is an independent set of
    paged HTTP requests, so four sequential fetches only add latency.
    """
    with ThreadPoolExecutor(max_workers=max(1, len(TAXA))) as pool:
        futures = {
            key: pool.submit(
                _fetch_v2, query, bbox, target=target_per_taxon, timeout_sec=timeout_sec
            )
            for key, query in TAXA.items()
        }
        return {key: future.result() for key, future in futures.items()}
