"""CA simulation frontend helpers for INSIGHT.

This module bridges the core CA and ML code with the demo app. It is kept thin
so the app can be either Streamlit-based or a simple script.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src import config
from src.ca import (
    CaGrid,
    CaParams,
    CELLState,
    run_simulation,
    seed_from_hotspots,
    step,
)
from src.fire_data import (
    FireDataset,
    build_cell_grid,
    build_fire_dataset,
    load_firms_hotspots,
)
from src.features import build_context_map, recent_hotspot_arrays

from src.mitigation import (
    build_mitigation_contexts,
    format_actions_for_display,
    MitigationContext,
)

from src.ml import load_trained_model, predict_risk_map, kalimantan_risk_map

from src.bio_loader import BioLayer, load_all_bio_layers

# Lightweight offline stub used when no live OSM query is available.
try:
    from src.osm_stub import make_kalimantan_stub_snapshot
    STUB_SNAPSHOT_AVAILABLE = True
except Exception:
    STUB_SNAPSHOT_AVAILABLE = False


@dataclass
class SimState:
    grid: CaGrid
    frames: List[CaGrid]
    current_step: int
    params: CaParams
    risk_map: Optional[np.ndarray]
    contexts: Dict[Tuple[int, int], MitigationContext]
    settlement_cells: List[Tuple[int, int]]
    rural_cells: List[Tuple[int, int]]
    wind_dir_deg: float
    bio_layers: Dict[str, BioLayer]
    kalimantan_risk: Optional[np.ndarray] = None
    kalimantan_bbox: Optional[Tuple[float, float, float, float]] = None
    # Provenance of ``risk_map``: "random forest" when the trained model
    # produced it, otherwise a description of why the heuristic was used.
    risk_source: str = "heuristic baseline"
    risk_metrics: Dict[str, Any] = field(default_factory=dict)
    # Last FIRMS day the risk map is conditioned on (None = no hotspot data).
    risk_conditioned_on: Optional[str] = None


# Everything below the wind direction — the OSM masks, the FIRMS dataset, the
# trained model, the island surface and the iNaturalist points — costs seconds to
# rebuild and is identical for every wind direction. ``use_static_cache=True``
# keeps it for the lifetime of the process (the app opts in, one-off scripts and
# tests do not, so monkeypatched loaders still take effect).
_STATIC_CACHE: Dict[bool, Dict[str, Any]] = {}


def _context_cache_path():
    from pathlib import Path

    return Path(config.data_cache_dir()) / "context_map.npz"


def _context_cache_key(cell_grid: Any) -> str:
    """Identify the snapshot + grid the cached masks were built from.

    Empty when no snapshot file exists yet: an offline stub or a fresh fetch must
    not be served from (or written to) a cache nobody can invalidate later.
    """
    from src.features import CONTEXT_MAP_CACHE_VERSION

    snapshot_file = config.data_raw_dir() / "osm_snapshot.json"
    if not snapshot_file.exists():
        return ""
    stat = snapshot_file.stat()
    stamp = f"{stat.st_mtime_ns}:{stat.st_size}"
    return (
        f"{CONTEXT_MAP_CACHE_VERSION}|" + "|".join(str(v) for v in (
            config.bounding_box(),
            cell_grid.n_rows,
            cell_grid.n_cols,
            cell_grid.spacing_deg,
            stamp,
        ))
    )


def _nearest_burnable_cell(grid: CaGrid, cell_grid: Any) -> Tuple[int, int]:
    """Return the burnable cell closest to the grid centre."""
    center_row = cell_grid.n_rows // 2
    center_col = cell_grid.n_cols // 2
    if grid.is_burnable(center_row, center_col):
        return center_row, center_col
    rows, cols = np.nonzero(grid.burnable)
    if rows.size == 0:
        return center_row, center_col
    distance = (rows - center_row) ** 2 + (cols - center_col) ** 2
    best = int(np.argmin(distance))
    return int(rows[best]), int(cols[best])


def _static_inputs(use_hotspots: bool) -> Dict[str, Any]:
    """Load the wind-independent half of a simulation state."""
    cell_grid = build_cell_grid()

    # The masks only change when the snapshot or the grid does, so keep them in
    # data/cache: rebuilding means parsing ~59k OSM features (~1 s of JSON alone)
    # on every process start. The cache is keyed on the snapshot file's stamp, so
    # a refreshed snapshot rebuilds it automatically.
    from src.features import read_context_cache

    cache_path = _context_cache_path()
    cache_key = _context_cache_key(cell_grid)
    context_map = (
        read_context_cache(cache_path, cache_key, cell_grid.n_rows, cell_grid.n_cols)
        if cache_key
        else None
    )

    if context_map is None:
        # Reuse the cached OSM snapshot when possible: the Random Forest was
        # trained on exactly those water/settlement/peat masks, and re-fetching
        # Overpass on every run is both slow and a source of train-vs-serve drift.
        # Falls back to the offline Kalimantan stub when no live query is
        # available (e.g. booth demo).
        osm_snapshot = None
        try:
            from src.osm import load_or_fetch_snapshot
            osm_snapshot = load_or_fetch_snapshot()
        except Exception:
            if STUB_SNAPSHOT_AVAILABLE:
                osm_snapshot = make_kalimantan_stub_snapshot()

        # The fetch above may have just written the snapshot file, so the key is
        # recomputed before it is used for the cache write.
        cache_key = _context_cache_key(cell_grid)
        context_map = build_context_map(
            osm_snapshot=osm_snapshot,
            cell_grid=cell_grid,
            cache_path=cache_path if cache_key else None,
            cache_key=cache_key,
        )

    # Inland-only filter: water cells are excluded from the fire-spread / rural
    # surface. Settlement cells are still surfaced for mitigation guidance even if
    # they are adjacent to water.
    settlement_cells: List[Tuple[int, int]] = []
    rural_cells: List[Tuple[int, int]] = []

    for row, col in cell_grid.iter_cells():
        if context_map.is_settlement[row, col]:
            settlement_cells.append((row, col))
        elif context_map.is_water[row, col]:
            continue
        else:
            rural_cells.append((row, col))

    dataset = None
    if use_hotspots:
        try:
            df = load_firms_hotspots()
            dataset = build_fire_dataset(
                df, bounding_box=config.bounding_box(), cell_grid=cell_grid
            )
        except Exception:
            dataset = None

    # Features for the day after the last observed FIRMS day, so the model sees
    # real recent hotspots instead of an artificially quiet week.
    recent = None
    risk_conditioned_on: Optional[str] = None
    if dataset is not None and dataset.labeled_days:
        risk_conditioned_on = str(dataset.labeled_days[-1])
        try:
            recent = recent_hotspot_arrays(dataset)
        except Exception:
            recent = None

    model = None
    model_metrics: Dict[str, Any] = {}
    model_error: Optional[Exception] = None
    try:
        model, model_metrics = load_trained_model()
    except Exception as exc:
        model_error = exc

    # Biodiversity layer: use the v2 iNaturalist endpoint (with an offline-first
    # fallback path in bio_loader if you prefer the local fixture).
    bio_layers = load_all_bio_layers(
        bbox=config.bounding_box(), target_per_taxon=500, use_v2=True,
    )

    return {
        "cell_grid": cell_grid,
        "context_map": context_map,
        "settlement_cells": settlement_cells,
        "rural_cells": rural_cells,
        "dataset": dataset,
        "recent": recent,
        "risk_conditioned_on": risk_conditioned_on,
        "model": model,
        "model_metrics": model_metrics,
        "model_error": model_error,
        "bio_layers": bio_layers,
    }


def initialize_simulation(
    wind_dir_deg: Optional[float] = None,
    n_steps: int = 12,
    use_hotspots: bool = True,
    use_static_cache: bool = False,
) -> SimState:
    """Create the initial SimState for the demo."""
    if wind_dir_deg is None:
        wind_dir_deg = config.default_wind_direction_deg()

    params = CaParams(wind_dir_deg=wind_dir_deg)

    static = _STATIC_CACHE.get(use_hotspots) if use_static_cache else None
    if static is None:
        static = _static_inputs(use_hotspots)
        if use_static_cache:
            _STATIC_CACHE[use_hotspots] = static

    cell_grid = static["cell_grid"]
    context_map = static["context_map"]
    dataset = static["dataset"]

    # Every inland cell carries fire; the OSM water mask is the barrier, so a
    # river or lake cuts the fire front instead of burning like forest. Settled
    # and peat cells stay burnable, they are just reported to mitigation.
    burnable = ~context_map.is_water
    grid = CaGrid().initialize(
        cell_grid.n_rows,
        cell_grid.n_cols,
        burnable_mask=burnable,
        # OSM peat/wetland cells start as PEAT_RISK and get the extra
        # CA_PEAT_INFLUENCE spread term; water cells are left out so a river is
        # never labelled as peat.
        peat_risk_mask=context_map.is_peat_risk & burnable,
    )

    seeded = 0
    if use_hotspots and dataset is not None:
        try:
            seeded = seed_from_hotspots(grid, dataset.hotspots, cell_grid)
        except Exception:
            seeded = 0

    if seeded == 0:
        # The box centre can sit on a river, which no longer ignites, so fall
        # back to the inland cell nearest to it.
        center_row, center_col = _nearest_burnable_cell(grid, cell_grid)
        seed_cell(grid, center_row, center_col, CELLState.BURNING)
        seeded = 1

    frames = run_simulation(grid, steps=n_steps, params=params)

    # Risk map from the trained Random Forest.
    risk_map: Optional[np.ndarray] = None
    risk_source = "heuristic baseline"
    risk_metrics: Dict[str, Any] = {}

    model = static["model"]
    if model is None and static["model_error"] is not None:
        risk_source = (
            f"heuristic baseline (trained model failed to load: {static['model_error']})"
        )

    if model is not None:
        try:
            risk_map = predict_risk_map(
                model, context_map, wind_dir_deg=wind_dir_deg,
                bounding_box=config.bounding_box(), cell_grid=cell_grid,
                recent_hotspots=static["recent"],
            )
            risk_source = "random forest"
            risk_metrics = static["model_metrics"]
        except Exception as exc:
            risk_map = None
            risk_source = f"heuristic baseline (prediction failed: {exc})"

    if risk_map is None:
        risk_map = predict_risk_map(
            None, context_map, wind_dir_deg=wind_dir_deg,
            bounding_box=config.bounding_box(), cell_grid=cell_grid,
        )

    # Kalimantan-wide coarse risk surface (fast, vectorized, wind-dependent).
    kal_risk, kal_bbox = kalimantan_risk_map(wind_dir_deg=wind_dir_deg)

    contexts = build_mitigation_contexts(
        grid, static["settlement_cells"], static["rural_cells"],
        risk_map=risk_map, wind_dir_deg=wind_dir_deg,
    )

    bio_layers = static["bio_layers"]

    return SimState(
        grid=grid,
        frames=frames,
        current_step=0,
        params=params,
        risk_map=risk_map,
        contexts=contexts,
        settlement_cells=static["settlement_cells"],
        rural_cells=static["rural_cells"],
        wind_dir_deg=wind_dir_deg,
        bio_layers=bio_layers,
        kalimantan_risk=kal_risk,
        kalimantan_bbox=kal_bbox,
        risk_source=risk_source,
        risk_metrics=risk_metrics,
        risk_conditioned_on=static["risk_conditioned_on"],
    )


def seed_cell(grid: CaGrid, row: int, col: int, state: CELLState = CELLState.BURNING) -> None:
    from src.ca import seed_cell as _seed
    _seed(grid, row, col, state)


def step_forward(state: SimState) -> SimState:
    """Advance the simulation by one step."""
    next_grid = state.frames[min(len(state.frames) - 1, state.current_step + 1)].clone()
    new_contexts = build_mitigation_contexts(
        next_grid,
        state.settlement_cells,
        state.rural_cells,
        risk_map=state.risk_map,
        wind_dir_deg=state.wind_dir_deg,
    )
    return SimState(
        grid=next_grid,
        frames=state.frames,
        current_step=state.current_step + 1,
        params=state.params,
        risk_map=state.risk_map,
        contexts=new_contexts,
        settlement_cells=state.settlement_cells,
        rural_cells=state.rural_cells,
        wind_dir_deg=state.wind_dir_deg,
        bio_layers=state.bio_layers,
        kalimantan_risk=state.kalimantan_risk,
        kalimantan_bbox=state.kalimantan_bbox,
        risk_source=state.risk_source,
        risk_metrics=state.risk_metrics,
        risk_conditioned_on=state.risk_conditioned_on,
    )


def risk_at(state: SimState, row: int, col: int) -> float:
    if state.risk_map is None:
        return 0.0
    if 0 <= row < state.risk_map.shape[0] and 0 <= col < state.risk_map.shape[1]:
        return float(state.risk_map[row, col])
    return 0.0


def mitigation_for(state: SimState, row: int, col: int) -> List[Dict[str, str]]:
    ctx = state.contexts.get((row, col))
    if ctx is None:
        return []
    from src.mitigation import actions_for
    return format_actions_for_display(actions_for(ctx))


def state_distribution(state: Any) -> Dict[str, int]:
    """Return the cell-state summary for a SimState or a CaGrid."""
    from src.ca import CaGrid
    if isinstance(state, CaGrid):
        return state.summary()
    return state.grid.summary()
