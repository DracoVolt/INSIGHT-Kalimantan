"""Baseline ML model for fire presence prediction.

This module trains a simple, explainable classifier (default: random forest) to
predict whether a cell had a FIRMS hotspot on a given day, using the feature
table built by `src/features`.

The aim is a teaching model: it should be easy to explain the features, the
choice of model, and the metrics on a science-fair poster.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from . import config
from .features import build_feature_table, feature_names


Model = Any


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------


def make_model(model_type: Optional[str] = None, random_state: Optional[int] = None) -> Model:
    if model_type is None:
        model_type = config.ML_MODEL_TYPE
    if random_state is None:
        random_state = config.ml_random_state()

    if model_type == "logistic_regression":
        return LogisticRegression(
            max_iter=2000,
            random_state=random_state,
            solver="lbfgs",
        )
    return RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        random_state=random_state,
        n_jobs=1,
    )


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


FEATURE_COLUMNS: List[str] = list(feature_names())


def train(
    dataset: Any,
    context_map: Any,
    wind_dir_deg: Optional[float] = None,
    model_type: Optional[str] = None,
    random_state: Optional[int] = None,
    test_fraction: Optional[float] = None,
) -> Tuple[Model, Dict[str, float], pd.DataFrame, pd.DataFrame]:
    """Train the baseline model and return (model, metrics, train_df, test_df)."""
    if wind_dir_deg is None:
        wind_dir_deg = config.default_wind_direction_deg()
    if test_fraction is None:
        test_fraction = config.ML_TEST_FRACTION

    feature_df = build_feature_table(dataset, context_map, wind_dir_deg=wind_dir_deg)

    feature_cols = [c for c in feature_names() if c not in ("lon", "lat")]
    X = feature_df[feature_cols].values.astype(float)
    y = feature_df["label"].values.astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_fraction, random_state=(random_state or config.ml_random_state()),
        stratify=y if len(set(y)) > 1 else None,
    )

    model = make_model(model_type=model_type, random_state=random_state)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

    metrics: Dict[str, float] = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)) if len(set(y_test)) > 1 else float("nan"),
    }

    train_df = feature_df.iloc[:0].copy()
    test_df = feature_df.iloc[:0].copy()
    train_df = feature_df.iloc[:0]
    test_df = feature_df.iloc[:0]
    # Re-attach indices properly
    train_idx = np.where(np.isin(np.arange(len(feature_df)), np.arange(len(feature_df))[:0]))[0]
    test_idx = np.where(np.isin(np.arange(len(feature_df)), np.arange(len(feature_df))[:0]))[0]

    # Simpler: rebuild train/test frames from the split indices.
    all_idx = np.arange(len(feature_df))
    train_idx, test_idx = train_test_split(
        all_idx, test_size=test_fraction,
        random_state=(random_state or config.ml_random_state()),
        stratify=y if len(set(y)) > 1 else None,
    )
    train_df = feature_df.iloc[train_idx].copy()
    test_df = feature_df.iloc[test_idx].copy()

    return model, metrics, train_df, test_df


def feature_importance_table(model: Model) -> pd.DataFrame:
    """Return a small DataFrame of feature importances if available."""
    if not hasattr(model, "feature_importances_"):
        return pd.DataFrame({"feature": FEATURE_COLUMNS, "importance": [0.0] * len(FEATURE_COLUMNS)})
    importances = model.feature_importances_
    full_cols = list(feature_names())
    rows = []
    for col in full_cols:
        if col in FEATURE_COLUMNS:
            idx = FEATURE_COLUMNS.index(col)
            rows.append({"feature": col, "importance": float(importances[idx])})
        else:
            rows.append({"feature": col, "importance": 0.0})
    return pd.DataFrame(rows).sort_values("importance", ascending=False)


# ---------------------------------------------------------------------------
# Prediction helpers
# ---------------------------------------------------------------------------


def predict_risk_map(
    model: Model,
    context_map: Any,
    wind_dir_deg: Optional[float] = None,
    bounding_box: Optional[Tuple[float, float, float, float]] = None,
    cell_grid: Optional[Any] = None,
) -> np.ndarray:
    """Return a 2D risk map (n_rows x n_cols) of per-cell predicted probabilities."""
    from .features import build_context_map
    from .fire_data import build_cell_grid

    if wind_dir_deg is None:
        wind_dir_deg = config.default_wind_direction_deg()
    if bounding_box is None:
        bounding_box = config.bounding_box()
    if cell_grid is None:
        cell_grid = build_cell_grid(bounding_box=bounding_box)
    if context_map is None:
        context_map = build_context_map()

    feature_cols = [c for c in feature_names() if c not in ("lon", "lat")]
    risk = np.zeros((cell_grid.n_rows, cell_grid.n_cols), dtype=float)

    for row, col in cell_grid.iter_cells():
        feats: Dict[str, float] = {
            "cell_row": float(row),
            "cell_col": float(col),
            "distance_to_nearest_water_cell": float(
                context_map.nearest_water_distance(row, col)
            ),
            "distance_to_nearest_settlement_cell": float(
                context_map.nearest_settlement_distance(row, col)
            ),
            "peat_risk_flag": float(context_map.is_peat_risk[row, col]),
            "has_hotspot_last_1_day": 0.0,
            "has_hotspot_last_3_days": 0.0,
            "has_hotspot_last_7_days": 0.0,
            "hotspot_count_last_7_days": 0.0,
            "wind_alignment": float(
                wind_alignment_for_cell(
                    row, col, wind_dir_deg,
                    cell_grid.n_rows, cell_grid.n_cols,
                )
            ),
            "lon": float(cell_grid.row_col_to_center(row, col)[0]),
            "lat": float(cell_grid.row_col_to_center(row, col)[1]),
        }
        x = np.array([[feats[c] for c in feature_cols]], dtype=float)
        prob = model.predict_proba(x)[0, 1] if hasattr(model, "predict_proba") else float(model.predict(x)[0])
        risk[row, col] = float(prob)

    return risk


def wind_alignment_for_cell(
    row: int,
    col: int,
    wind_dir_deg: float,
    n_rows: int,
    n_cols: int,
) -> float:
    """Simplified wind-alignment feature for prediction-time use."""
    from .ca import wind_alignment_factor
    center_row = (n_rows - 1) / 2.0
    center_col = (n_cols - 1) / 2.0
    dr = row - center_row
    dc = col - center_col
    if dr == 0 and dc == 0:
        return 0.0
    return wind_alignment_factor(center_row, center_col, row, col, wind_dir_deg, center_row, center_col)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_model(model: Model, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    return path


def load_model(path: Path) -> Model:
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    return joblib.load(path)


def save_metrics(metrics: Dict[str, float], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "{\n" + ",\n".join(f'  "{k}": {v}' for k, v in metrics.items()) + "\n}\n"
    )
    return path
