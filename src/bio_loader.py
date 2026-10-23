"""
Offline-first biodiversity loader for the Kalimantan demo box.

Default source: iNaturalist v1 observations API (open data),
taxa: Bornean Orangutan, Proboscis monkey, Rafflesia, Nepenthes.

Uses src/bio_stub_fixture.json when present (offline mode) and
falls back to a live API fetch otherwise. The fixture is a dict:

    { taxon_key: [[lat, lon], ...], ... }
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import config

HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_FIXTURE = os.path.join(HERE, "bio_stub_fixture.json")

# Demo bounding box for Central Kalimantan (Palangkaraya / Sebangau / Kahayan river area).
DEMO_BBOX: Tuple[float, float, float, float] = config.bounding_box()


# Taxa we care about in this demo.
TAXA: Dict[str, str] = {
    "Orangutan": "Orangutan",
    "Proboscis_monkey": "Proboscis monkey",
    "Rafflesia": "Rafflesia arnoldii",
    "Nepenthes": "Nepenthes",
}

class BioLayer:
    """A small read-only container for one taxonomy's observation points."""

    def __init__(self, key: str, query: str, points: List[Tuple[float, float]]):
        self.key = key
        self.query = query
        self.points = points

    @property
    def n(self) -> int:
        return len(self.points)

    def sample(self, n: int = 5) -> List[Tuple[float, float]]:
        if not self.points:
            return []
        step = max(1, len(self.points) // max(1, n))
        return self.points[::step][:n]


def _load_fixture(path: str = _DEFAULT_FIXTURE) -> Optional[Dict[str, List[Tuple[float, float]]]]:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw: Any = json.load(f)
    except Exception:
        return None
    out: Dict[str, List[Tuple[float, float]]] = {}
    for k, v in raw.items():
        if isinstance(v, list):
            pts: List[Tuple[float, float]] = []
            for item in v:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    try:
                        lat = float(item[0])
                        lon = float(item[1])
                        pts.append((lat, lon))
                    except (TypeError, ValueError):
                        continue
            out[str(k)] = pts
    return out if out else None


def _fetch_live(taxon_key: str, taxon_query: str, bbox: Tuple[float, float, float, float],
                target: int = 500, max_pages: int = 999, timeout_sec: int = 5) -> List[Tuple[float, float]]:
    """Fetch research-grade iNaturalist observations for one taxon within bbox."""

    def _raw(page: int, per: int = 200) -> Optional[Any]:
        tn = urllib.parse.quote(taxon_query, safe="")
        # iNaturalist reads bbox as swlat,swlng,nelat,nelng; callers pass
        # (min_lon, min_lat, max_lon, max_lat). Sending the lon/lat order made
        # the API ignore the box and return observations from anywhere.
        min_lon, min_lat, max_lon, max_lat = bbox
        bbox_s = f"{min_lat},{min_lon},{max_lat},{max_lon}"
        qs = ("page=%d&per_page=%d&taxon_name=%s&bbox=%s"
              "&order=desc&quality_grade=research") % (page, per, tn, bbox_s)
        url = "https://api.inaturalist.org/v1/observations?" + qs
        try:
            with urllib.request.urlopen(url, timeout=timeout_sec) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            # Many taxa return 404-style empty results outside their range.
            # Treat distinct HTTP errors as "no observations available".
            return None
        except Exception as exc:  # pragma: no cover - network noise
            return None

    def _extract(obs: Any) -> Optional[Tuple[float, float]]:
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

    pts: List[Tuple[float, float]] = []
    page = 1
    while page <= max_pages and len(pts) < target:
        payload = _raw(page=page, per=200)
        if payload is None:
            break
        results = payload.get("results") or []
        if not results:
            break
        for obs in results:
            p = _extract(obs)
            if p is not None:
                pts.append(p)
        page += 1
        if len(results) < 200:
            break
        if page % 4 == 0:
            time.sleep(0.3)
    return pts


# Kalimantan-only bounding box for the flora & fauna layer (Borneo's
# Indonesian portion). Observations outside this region are filtered out so
# the overlay stays on the island.
KALIMANTAN_BIO_BBOX: Tuple[float, float, float, float] = (108.8, -4.2, 119.1, 7.3)

# The live fetch is the slowest part of a cold start: four taxa, a couple of
# paged iNaturalist requests each, all over the network. Observations change
# slowly, so the points are kept on disk and only re-fetched once the snapshot
# is older than CACHE_TTL_SECONDS.
CACHE_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "cache" / "bio_layers.json"
CACHE_TTL_SECONDS: float = 24 * 3600.0


def _read_cache(
    path: Path = CACHE_PATH,
    ttl: float = CACHE_TTL_SECONDS,
) -> Optional[Dict[str, List[Tuple[float, float]]]]:
    """Return cached points per taxon, or None when missing/stale/unreadable."""
    try:
        if ttl >= 0 and time.time() - path.stat().st_mtime > ttl:
            return None
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    out: Dict[str, List[Tuple[float, float]]] = {}
    for key, points in raw.items():
        if not isinstance(points, list):
            continue
        out[str(key)] = [
            (float(p[0]), float(p[1]))
            for p in points
            if isinstance(p, (list, tuple)) and len(p) >= 2
        ]
    return out or None


def _write_cache(
    layers: Dict[str, "BioLayer"],
    path: Path = CACHE_PATH,
) -> None:
    """Persist the fetched points (best effort: a read-only disk is not fatal)."""
    payload = {
        key: [[round(lat, 5), round(lon, 5)] for (lat, lon) in layer.points]
        for key, layer in layers.items()
        if layer.points
    }
    if not payload:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        os.replace(tmp, path)
    except Exception:
        pass


def filter_points_to_bbox(points: List[Tuple[float, float]],
                          bbox: Tuple[float, float, float, float]) -> List[Tuple[float, float]]:
    """Keep only points whose (lat, lon) lies inside bbox (min_lon, min_lat, max_lon, max_lat)."""
    min_lon, min_lat, max_lon, max_lat = bbox
    return [(lat, lon) for (lat, lon) in points
            if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat]


def load_bio_layer(taxon_key: str, taxon_query: Optional[str] = None,
                   bbox: Optional[Tuple[float, float, float, float]] = None,
                   target: int = 500, fixture_path: Optional[str] = None,
                   ) -> BioLayer:
    """Load one biodiversity layer, offline-first.

    Order of preference:
    1. local fixture (src/bio_stub_fixture.json) if present
    2. live iNaturalist v1 API, with research-grade observations only

    The live API can be slow / blocked in some environments; the offline
    stub is strongly preferred when present."""
    bbox = bbox or DEMO_BBOX
    taxon_query = taxon_query or TAXA.get(taxon_key, taxon_key)

    fixture = _load_fixture(fixture_path)
    if fixture and taxon_key in fixture and fixture[taxon_key]:
        return BioLayer(key=taxon_key, query=taxon_query, points=fixture[taxon_key][:target])

    # Fall back to the live API only when no local fixture is available.
    # In many offline / restricted environments this will return an empty layer.
    try:
        pts = _fetch_live(taxon_key, taxon_query, bbox, target=target, timeout_sec=5)
    except BaseException:
        pts = []
    return BioLayer(key=taxon_key, query=taxon_query, points=pts)


def _fetch_all_parallel(
    bbox: Tuple[float, float, float, float],
    target_per_taxon: int,
    fixture_path: Optional[str],
    use_v2: bool,
) -> Dict[str, BioLayer]:
    """Fetch every taxon at the same time instead of one after another.

    The four requests are independent network round trips, so running them in
    parallel turns ~4x the per-taxon latency into roughly one.
    """
    if use_v2:
        from .bio_v2 import fetch_all as fetch_v2_all

        raw = fetch_v2_all(bbox=bbox, target_per_taxon=target_per_taxon)
        return {
            key: BioLayer(key=key, query=TAXA.get(key, key), points=raw.get(key, []))
            for key in TAXA
        }

    with ThreadPoolExecutor(max_workers=max(1, len(TAXA))) as pool:
        futures = {
            key: pool.submit(
                load_bio_layer,
                key,
                bbox=bbox,
                target=target_per_taxon,
                fixture_path=fixture_path,
            )
            for key in TAXA
        }
        return {key: future.result() for key, future in futures.items()}


def load_all_bio_layers(bbox: Optional[Tuple[float, float, float, float]] = None,
                        target_per_taxon: int = 500,
                        fixture_path: Optional[str] = None,
                        use_v2: bool = False,
                        cache_path: Optional[str] = None,
                        cache_ttl: float = CACHE_TTL_SECONDS,
                        ) -> Dict[str, BioLayer]:
    """Load every demo taxon as a BioLayer.

    Points come from the on-disk snapshot when it is fresh (the common case),
    otherwise they are fetched for all taxa in parallel and written back. A
    failed fetch keeps serving the stale snapshot rather than an empty map.

    By default this uses the offline-first v1 loader (local fixture first,
    then v1 API). Set *use_v2=True* to fetch from the v2 endpoint instead.
    """
    bbox = bbox or DEMO_BBOX
    path = Path(cache_path) if cache_path else CACHE_PATH

    cached = _read_cache(path, ttl=cache_ttl)
    if cached is not None:
        layers = {
            key: BioLayer(key=key, query=TAXA.get(key, key), points=cached.get(key, []))
            for key in TAXA
        }
    else:
        layers = _fetch_all_parallel(
            bbox=bbox,
            target_per_taxon=target_per_taxon,
            fixture_path=fixture_path,
            use_v2=use_v2,
        )
        if not any(layer.points for layer in layers.values()):
            # Offline: an old snapshot beats a blank map.
            stale = _read_cache(path, ttl=-1)
            if stale:
                layers = {
                    key: BioLayer(key=key, query=TAXA.get(key, key), points=stale.get(key, []))
                    for key in TAXA
                }

    # The flora & fauna layer is Kalimantan-only: drop any observation that
    # falls outside the island even if the source bbox was wider.
    for key, layer in layers.items():
        kept = filter_points_to_bbox(layer.points, KALIMANTAN_BIO_BBOX)
        if len(kept) != len(layer.points):
            layers[key] = BioLayer(key=layer.key, query=layer.query, points=kept)

    # Cache what was actually kept, so a cache hit and a fetch agree.
    if cached is None and any(layer.points for layer in layers.values()):
        _write_cache(layers, path)
    return layers


if __name__ == "__main__":
    layers = load_all_bio_layers()
    for key, layer in layers.items():
        print(f"{key:18s} n={layer.n:5d}  sample={layer.sample(3)}")
