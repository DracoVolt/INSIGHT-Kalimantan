"""Tests for the trained-model pipeline and its app wiring.

Covers three things the risk map depends on:
- history features never include the target day (no label leakage),
- the inference history arrays line up with the training definitions,
- the app uses the saved Random Forest (not the heuristic) when one exists.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from src import config
from src.features import (
    build_context_map,
    build_feature_table,
    feature_names,
    nearest_feature_distance,
    recent_hotspot_arrays,
)
from src.fire_data import CellGrid, FireDataset, build_fire_dataset
from src.ml import (
    feature_importance_table,
    load_metrics,
    load_trained_model,
    predict_risk_map,
    save_metrics,
    save_model,
)

DAYS = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]


def _toy_grid() -> CellGrid:
    return CellGrid(
        min_lon=112.5,
        min_lat=-3.0,
        max_lon=114.5,
        max_lat=-1.0,
        spacing_deg=0.5,
        n_rows=4,
        n_cols=4,
    )


def _toy_dataset(grid: CellGrid, positives, days=DAYS) -> FireDataset:
    labels = {(r, c, d): 0 for r in range(grid.n_rows) for c in range(grid.n_cols) for d in days}
    for (r, c, d) in positives:
        labels[(r, c, d)] = 1
    return FireDataset(
        bounding_box=(grid.min_lon, grid.min_lat, grid.max_lon, grid.max_lat),
        hotspots=[],
        cell_grid=grid,
        labeled_days=list(days),
        labels=labels,
    )


class ConstantModel:
    """Stand-in for a fitted model so tests can spot which code path ran."""

    def __init__(self, prob: float = 0.42, n_features: int = 11):
        self.prob = prob
        self.n_features_in_ = n_features

    def predict_proba(self, X):
        X = np.asarray(X, dtype=float)
        return np.tile([1.0 - self.prob, self.prob], (X.shape[0], 1))

    def predict(self, X):
        X = np.asarray(X, dtype=float)
        return np.full(X.shape[0], 1 if self.prob >= 0.5 else 0, dtype=int)


# ---------------------------------------------------------------------------
# History features and leakage
# ---------------------------------------------------------------------------


def test_recent_history_targets_the_day_after_the_last_observation():
    grid = _toy_grid()
    dataset = _toy_dataset(grid, {(1, 1, "2024-01-04"), (2, 2, "2024-01-02")})
    arrays = recent_hotspot_arrays(dataset)

    assert isinstance(arrays, dict)
    assert set(arrays) == {
        "has_hotspot_last_1_day",
        "has_hotspot_last_3_days",
        "has_hotspot_last_7_days",
        "hotspot_count_last_7_days",
        "distance_to_nearest_hotspot_cell",
    }
    for arr in arrays.values():
        assert arr.shape == (grid.n_rows, grid.n_cols)

    # Feature for the day after the last observation: "yesterday" is the last
    # observed day, not the day before it.
    assert arrays["has_hotspot_last_1_day"][1, 1] == 1.0
    assert arrays["has_hotspot_last_1_day"][2, 2] == 0.0
    assert arrays["has_hotspot_last_3_days"][2, 2] == 1.0
    assert arrays["distance_to_nearest_hotspot_cell"][1, 1] == 0.0
    assert np.isclose(arrays["distance_to_nearest_hotspot_cell"][0, 0], np.sqrt(2.0))


def test_recent_history_does_not_read_the_target_day():
    grid = _toy_grid()
    # Hotspots on 01-04 only. For target day 01-04 nothing has burned yet.
    dataset = _toy_dataset(grid, {(1, 1, "2024-01-04")})
    arrays = recent_hotspot_arrays(dataset, target_day="2024-01-04")

    assert arrays["has_hotspot_last_1_day"][1, 1] == 0.0
    assert arrays["hotspot_count_last_7_days"][1, 1] == 0.0
    assert arrays["distance_to_nearest_hotspot_cell"][1, 1] == float(
        grid.n_rows + grid.n_cols
    )


def test_training_features_use_previous_day_not_the_label_day():
    """A cell that burns on day D must not look burned in D's own features."""
    grid = _toy_grid()
    dataset = _toy_dataset(grid, {(1, 1, "2024-01-03")})
    df = build_feature_table(dataset, context_map=build_context_map(cell_grid=grid))
    df = df[(df["row"] == 1) & (df["col"] == 1)].set_index("day_iso")

    burn_day = df.loc["2024-01-03"]
    assert burn_day["label"] == 1
    assert burn_day["has_hotspot_last_1_day"] == 0.0
    assert burn_day["has_hotspot_last_3_days"] == 0.0
    assert burn_day["distance_to_nearest_hotspot_cell"] == float(grid.n_rows + grid.n_cols)

    next_day = df.loc["2024-01-04"]
    assert next_day["label"] == 0
    assert next_day["has_hotspot_last_1_day"] == 1.0
    assert next_day["has_hotspot_last_3_days"] == 1.0
    assert next_day["distance_to_nearest_hotspot_cell"] == 0.0


def test_history_arrays_accept_datetime_days():
    grid = _toy_grid()
    days = [datetime(2024, 1, 1), datetime(2024, 1, 2)]
    labels = {(0, 0, "2024-01-02"): 1}
    dataset = FireDataset(
        bounding_box=(grid.min_lon, grid.min_lat, grid.max_lon, grid.max_lat),
        hotspots=[],
        cell_grid=grid,
        labeled_days=days,
        labels=labels,
    )
    arrays = recent_hotspot_arrays(dataset)
    assert arrays["has_hotspot_last_1_day"][0, 0] == 1.0


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------


def test_predict_risk_map_uses_the_model_when_available():
    grid = _toy_grid()
    ctx = build_context_map(cell_grid=grid)
    model = ConstantModel(prob=0.42)

    risk = predict_risk_map(model, ctx, wind_dir_deg=90.0, cell_grid=grid)
    assert risk.shape == (grid.n_rows, grid.n_cols)
    assert np.allclose(risk, 0.42)

    heuristic = predict_risk_map(None, ctx, wind_dir_deg=90.0, cell_grid=grid)
    assert not np.allclose(heuristic, 0.42)


def test_predict_risk_map_feeds_recent_history_to_the_model():
    grid = _toy_grid()
    ctx = build_context_map(cell_grid=grid)
    captured = {}

    class Recorder(ConstantModel):
        def predict_proba(self, X):
            captured["X"] = np.asarray(X, dtype=float)
            return super().predict_proba(X)

    dataset = _toy_dataset(grid, {(2, 3, "2024-01-04")})
    recent = recent_hotspot_arrays(dataset)
    predict_risk_map(Recorder(), ctx, wind_dir_deg=90.0, cell_grid=grid, recent_hotspots=recent)

    cols = [c for c in feature_names() if c not in ("lon", "lat")]
    values = captured["X"]
    assert values.shape == (grid.n_rows * grid.n_cols, len(cols))
    idx = cols.index("has_hotspot_last_1_day")
    # Cell (2, 3) is the only one that burned on the last observed day.
    assert values[2 * grid.n_cols + 3, idx] == 1.0
    assert float(values[:, idx].sum()) == 1.0


def test_predict_risk_map_rejects_a_stale_model():
    grid = _toy_grid()
    ctx = build_context_map(cell_grid=grid)
    with pytest.raises(ValueError, match="retrain"):
        predict_risk_map(ConstantModel(n_features=3), ctx, cell_grid=grid)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_model_roundtrip_predicts_identically(tmp_path: Path):
    rng = np.random.default_rng(0)
    n_features = len([c for c in feature_names() if c not in ("lon", "lat")])
    X = rng.random((40, n_features))
    y = (rng.random(40) < 0.3).astype(int)
    y[0], y[1] = 0, 1

    model = RandomForestClassifier(n_estimators=5, random_state=0).fit(X, y)
    path = tmp_path / "rf.joblib"
    meta = tmp_path / "rf_metrics.json"
    save_model(model, path)
    save_metrics({"roc_auc": 0.8}, meta)

    loaded, metrics = load_trained_model(path, meta)
    assert loaded is not None
    assert metrics["roc_auc"] == 0.8
    assert np.allclose(
        loaded.predict_proba(X), model.predict_proba(X)
    )
    assert load_metrics(meta)["roc_auc"] == 0.8


def test_load_trained_model_returns_none_when_missing(tmp_path: Path):
    model, metrics = load_trained_model(tmp_path / "absent.joblib", tmp_path / "absent.json")
    assert model is None
    assert metrics == {}


def test_feature_importance_table_reads_the_attribute():
    """Regression: the table used to return zeros for every feature."""
    rng = np.random.default_rng(1)
    n_features = len([c for c in feature_names() if c not in ("lon", "lat")])
    X = rng.random((60, n_features))
    y = (X[:, 0] + X[:, 1] > 1.0).astype(int)

    model = RandomForestClassifier(n_estimators=5, random_state=0).fit(X, y)
    table = feature_importance_table(model)
    assert len(table) == n_features
    assert np.isclose(float(table["importance"].sum()), 1.0)
    assert float(table["importance"].max()) > 0.0


# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------


def _firms_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "lat": [-2.0, -1.5],
            "lon": [113.0, 114.0],
            "confidence": [90.0, 80.0],
            "datetime": [datetime(2024, 1, 4, 5), datetime(2024, 1, 3, 5)],
        }
    )


def test_initialize_simulation_uses_the_trained_model(monkeypatch):
    import app.ca_simulator as sim

    grid = _toy_grid()
    monkeypatch.setattr(sim, "build_cell_grid", lambda *a, **k: grid)
    monkeypatch.setattr(sim, "load_firms_hotspots", _firms_frame)
    monkeypatch.setattr(sim, "load_all_bio_layers", lambda **kw: {})
    monkeypatch.setattr(
        sim, "load_trained_model",
        lambda *a, **k: (ConstantModel(prob=0.33), {"roc_auc": 0.87}),
    )
    # No OSM snapshot in tests; the stub/blank context map is enough here.
    import src.osm as osm

    def _no_osm(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(osm, "load_or_fetch_snapshot", _no_osm)

    state = sim.initialize_simulation(wind_dir_deg=90.0, n_steps=1, use_hotspots=True)

    assert state.risk_source == "random forest"
    assert state.risk_metrics["roc_auc"] == 0.87
    assert state.risk_conditioned_on == "2024-01-04"
    assert np.allclose(state.risk_map, 0.33)

    stepped = sim.step_forward(state)
    assert stepped.risk_source == "random forest"
    assert stepped.risk_conditioned_on == "2024-01-04"


def test_initialize_simulation_falls_back_to_heuristic(monkeypatch):
    import app.ca_simulator as sim
    import src.osm as osm

    grid = _toy_grid()
    monkeypatch.setattr(sim, "build_cell_grid", lambda *a, **k: grid)
    monkeypatch.setattr(sim, "load_firms_hotspots", _firms_frame)
    monkeypatch.setattr(sim, "load_all_bio_layers", lambda **kw: {})
    monkeypatch.setattr(sim, "load_trained_model", lambda *a, **k: (None, {}))
    monkeypatch.setattr(
        osm,
        "load_or_fetch_snapshot",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    state = sim.initialize_simulation(wind_dir_deg=90.0, n_steps=1, use_hotspots=True)

    assert "heuristic" in state.risk_source
    assert state.risk_metrics == {}
    assert np.isfinite(state.risk_map).all()
