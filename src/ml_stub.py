"""Lightweight ML stubs for tests and offline exploration."""

from __future__ import annotations

from typing import Any, Dict, Tuple

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from src import config
from src.features import feature_names
from src.fire_data_stub import make_fake_dataset


def make_stub_model(model_type: str = "random_forest") -> Any:
    if model_type == "logistic_regression":
        from sklearn.linear_model import LogisticRegression
        return LogisticRegression(max_iter=2000, random_state=config.ml_random_state())
    return RandomForestClassifier(
        n_estimators=50,
        max_depth=4,
        random_state=config.ml_random_state(),
    )


def train_on_fake_data(model_type: str = "random_forest") -> Tuple[Any, Dict[str, float], str]:
    dataset = make_fake_dataset()
    from src.features import build_context_map, build_feature_table
    from src.ml import train

    ctx = build_context_map()
    model, metrics, train_df, test_df = train(
        dataset,
        context_map=ctx,
        wind_dir_deg=config.default_wind_direction_deg(),
        model_type=model_type,
    )
    return model, metrics, "stub"


def predict_risk_on_fake(model: Any) -> np.ndarray:
    from src.features import build_context_map
    from src.fire_data_stub import make_fake_grid
    from src.ml import predict_risk_map
    from src import config

    ctx = build_context_map()
    grid = make_fake_grid()
    return predict_risk_map(
        model,
        context_map=ctx,
        wind_dir_deg=config.default_wind_direction_deg(),
        bounding_box=config.bounding_box(),
        cell_grid=grid,
    )


def save_and_load_stub(path):
    model = make_stub_model()
    saved = joblib.dump(model, path)
    loaded = joblib.load(path)
    return loaded
