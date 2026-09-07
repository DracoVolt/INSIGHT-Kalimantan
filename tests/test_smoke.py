"""Smoke test that the package imports cleanly and basic objects exist."""

from __future__ import annotations

import pytest

from src import config
from src.ca import CaGrid, CaParams, CELLState, step_explanation
from src.fire_data import build_cell_grid, build_fire_dataset
from src.features import feature_names, build_context_map
from src.ml import make_model, train
from src.mitigation import assess_risk, MitigationContext, RiskLevel


def test_config_constants_exist():
    assert config.bounding_box() is not None
    assert config.grid_spacing_deg() > 0
    assert config.default_wind_direction_deg() >= 0


def test_ca_structures_exist():
    assert CELLState.HEALTHY is not None
    params = CaParams(wind_dir_deg=90)
    assert params.wind_dir_deg == 90


def test_fire_data_builders_exist():
    grid = build_cell_grid()
    assert grid.n_rows > 0
    assert grid.n_cols > 0


def test_ml_builders_exist():
    model = make_model(model_type="random_forest")
    assert model is not None


def test_mitigation_structs_exist():
    ctx = MitigationContext(
        cell_row=0,
        cell_col=0,
        is_settlement=True,
        is_rural=False,
        distance_to_nearest_burning_cell=None,
        distance_to_nearest_igniting_cell=None,
        ca_state="healthy",
        predicted_risk=0.0,
        wind_dir_deg=0.0,
    )
    assert assess_risk(ctx) == RiskLevel.NONE


def test_feature_names_include_expected():
    names = feature_names()
    assert "cell_row" in names
    assert "lon" in names
    assert "lat" in names
    assert "wind_alignment" in names
    assert "peat_risk_flag" in names
