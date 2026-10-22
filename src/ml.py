"""Baseline ML model for fire presence prediction.

This module trains a simple, explainable classifier (default: random forest) to
predict whether a cell had a FIRMS hotspot on a given day, using the feature
table built by `src/features`.

The aim is a teaching model: it should be easy to explain the features, the
choice of model, and the metrics on a science-fair poster.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
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

    # No class weighting. Fires are rare per cell-day (about 3%), but
    # ``class_weight="balanced_subsample"`` was measured to make things worse
    # on the temporal split: ROC-AUC 0.863 vs 0.883 and PR-AUC 0.222 vs 0.283,
    # and it inflated the mean predicted probability to 0.24 against an
    # observed 0.024. The unweighted forest both ranks better and keeps the
    # map readable as a probability.
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
) -> Tuple[Model, Dict[str, Any], pd.DataFrame, pd.DataFrame]:
    """Train the model and return (model, metrics, train_df, test_df).

    The split is temporal whenever the dataset spans at least four days: the
    last ``test_fraction`` of the days become the test set. Splitting cell-days
    at random would put the same cell on both sides of the split and inflate the
    metrics, because some cells burn repeatedly.
    """
    if wind_dir_deg is None:
        wind_dir_deg = config.default_wind_direction_deg()
    if test_fraction is None:
        test_fraction = config.ML_TEST_FRACTION

    feature_df = build_feature_table(dataset, context_map, wind_dir_deg=wind_dir_deg)

    feature_cols = [c for c in feature_names() if c not in ("lon", "lat")]
    X = feature_df[feature_cols].values.astype(float)
    y = feature_df["label"].values.astype(int)

    if len(set(y)) < 2 or int(y.sum()) < 2:
        raise ValueError(
            "Training needs both positive and negative labels; the FIRMS file "
            "produced no usable hotspots inside the demo box."
        )

    days = sorted(str(d) for d in feature_df["day_iso"].unique())
    split_mode = "random"
    n_test_days = 0
    train_mask: Optional[np.ndarray] = None

    if len(days) >= 4:
        n_test_days = max(1, int(round(len(days) * test_fraction)))
        test_days = set(days[-n_test_days:])
        is_test = feature_df["day_iso"].astype(str).isin(test_days).values
        if is_test.any() and (~is_test).any() and int(y[~is_test].sum()) > 0:
            train_mask = ~is_test
            split_mode = "temporal"

    if train_mask is None:
        all_idx = np.arange(len(feature_df))
        train_idx, _ = train_test_split(
            all_idx,
            test_size=test_fraction,
            random_state=(random_state if random_state is not None else config.ml_random_state()),
            stratify=y if len(set(y)) > 1 else None,
        )
        train_mask = np.zeros(len(feature_df), dtype=bool)
        train_mask[train_idx] = True

    X_train, X_test = X[train_mask], X[~train_mask]
    y_train, y_test = y[train_mask], y[~train_mask]

    model = make_model(model_type=model_type, random_state=random_state)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred

    metrics: Dict[str, Any] = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)) if len(set(y_test)) > 1 else float("nan"),
        "average_precision": (
            float(average_precision_score(y_test, y_prob))
            if len(set(y_test)) > 1
            else float("nan")
        ),
        "split_mode": split_mode,
        "n_test_days": float(n_test_days),
        "n_train_rows": float(len(y_train)),
        "n_test_rows": float(len(y_test)),
        "n_test_positives": float(y_test.sum()),
        "positive_rate": float(y.mean()),
    }

    return model, metrics, feature_df[train_mask].copy(), feature_df[~train_mask].copy()


def feature_importance_table(model: Model) -> pd.DataFrame:
    """Return a small DataFrame of feature importances if available.

    Only the columns the model was trained on are reported: ``lon`` and ``lat``
    stay in the feature table for mapping but are excluded from training.
    """
    trained_cols = [c for c in feature_names() if c not in ("lon", "lat")]
    if not hasattr(model, "feature_importances_"):
        return pd.DataFrame(
            {"feature": trained_cols, "importance": [0.0] * len(trained_cols)}
        )
    importances = model.feature_importances_
    rows = [
        {"feature": col, "importance": float(importances[idx])}
        for idx, col in enumerate(trained_cols)
        if idx < len(importances)
    ]
    return pd.DataFrame(rows).sort_values("importance", ascending=False)


# ---------------------------------------------------------------------------
# Prediction helpers
# ---------------------------------------------------------------------------


def predict_risk_map(
    model: Optional[Model],
    context_map: Any,
    wind_dir_deg: Optional[float] = None,
    bounding_box: Optional[Tuple[float, float, float, float]] = None,
    cell_grid: Optional[Any] = None,
    recent_hotspots: Optional[Dict[str, np.ndarray]] = None,
) -> np.ndarray:
    """Return a 2D risk map (n_rows x n_cols) of per-cell predicted probabilities.

    If *model* is None (e.g. no trained model yet), the returned map is a
    heuristic baseline built from wind alignment, peat proximity, and
    distance to water/settlement so the demo still shows a meaningful risk
    surface. Otherwise the trained model is used.

    ``recent_hotspots`` optionally supplies per-cell history arrays named like
    the feature table (``has_hotspot_last_1_day`` ...). Without it the model
    sees a quiet week (all zeros), which is the correct baseline for a map that
    is not conditioned on recent FIRMS activity.
    """
    if wind_dir_deg is None:
        wind_dir_deg = config.default_wind_direction_deg()
    if bounding_box is None:
        bounding_box = config.bounding_box()
    if cell_grid is None:
        from .fire_data import build_cell_grid as _build_cell_grid
        cell_grid = _build_cell_grid(bounding_box=bounding_box)
    if context_map is None:
        from .features import build_context_map as _build_context_map
        context_map = _build_context_map()

    history = recent_hotspots or {}

    def hist(name: str, row: int, col: int) -> float:
        arr = history.get(name)
        if arr is None:
            return 0.0
        return float(arr[row, col])

    feature_cols = [c for c in feature_names() if c not in ("lon", "lat")]
    n_rows, n_cols = cell_grid.n_rows, cell_grid.n_cols
    use_model = model is not None and hasattr(model, "predict")

    rows_list: List[List[float]] = []
    heuristic = np.zeros(n_rows * n_cols, dtype=float)
    cell_index = 0

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
            "distance_to_nearest_hotspot_cell": hist(
                "distance_to_nearest_hotspot_cell", row, col
            ),
            "peat_risk_flag": float(context_map.is_peat_risk[row, col]),
            "has_hotspot_last_1_day": hist("has_hotspot_last_1_day", row, col),
            "has_hotspot_last_3_days": hist("has_hotspot_last_3_days", row, col),
            "has_hotspot_last_7_days": hist("has_hotspot_last_7_days", row, col),
            "hotspot_count_last_7_days": hist("hotspot_count_last_7_days", row, col),
            "wind_alignment": float(
                wind_alignment_for_cell(
                    row, col, wind_dir_deg,
                    cell_grid.n_rows, cell_grid.n_cols,
                )
            ),
            "lon": float(cell_grid.row_col_to_center(row, col)[0]),
            "lat": float(cell_grid.row_col_to_center(row, col)[1]),
        }

        if use_model:
            rows_list.append([feats[c] for c in feature_cols])
        else:
            # Heuristic baseline: higher risk downwind, on peat, near
            # settlements, and lower risk near water.
            wind_align = feats["wind_alignment"]
            peat = feats["peat_risk_flag"]
            d_settle = feats["distance_to_nearest_settlement_cell"]
            d_water = feats["distance_to_nearest_water_cell"]
            heuristic[cell_index] = (
                0.05
                + 0.25 * wind_align
                + 0.15 * peat
                + 0.10 * max(0.0, 1.0 - d_settle / 5.0)
                - 0.08 * max(0.0, 1.0 - d_water / 5.0)
            )
        cell_index += 1

    if use_model:
        X = np.asarray(rows_list, dtype=float)
        n_expected = int(getattr(model, "n_features_in_", X.shape[1]))
        if n_expected != X.shape[1]:
            raise ValueError(
                f"Trained model expects {n_expected} features but the feature "
                f"table now has {X.shape[1]}; retrain with `python -m src.train`."
            )
        if hasattr(model, "predict_proba"):
            risk = model.predict_proba(X)[:, 1]
        else:
            risk = model.predict(X)
    else:
        risk = heuristic

    return np.clip(np.asarray(risk, dtype=float).reshape(n_rows, n_cols), 0.0, 1.0)


def kalimantan_risk_map(
    wind_dir_deg: Optional[float] = None,
    bounding_box: Optional[Tuple[float, float, float, float]] = None,
    spacing_deg: Optional[float] = None,
) -> Tuple[np.ndarray, Tuple[float, float, float, float]]:
    """Fast vectorized heuristic risk surface for the whole of Kalimantan.

    Returns (risk array, bbox used). This is the same physics heuristic as
    `predict_risk_map` (wind alignment + peat + settlement/water proximity)
    but computed with numpy broadcasting so a ~16 km grid over the whole
    island renders in milliseconds instead of minutes.
    """
    if wind_dir_deg is None:
        wind_dir_deg = config.default_wind_direction_deg()
    if bounding_box is None:
        bounding_box = config.KALIMANTAN_BBOX
    if spacing_deg is None:
        spacing_deg = config.KALIMANTAN_SPACING_DEG

    min_lon, min_lat, max_lon, max_lat = bounding_box
    n_rows = max(1, int(np.ceil((max_lat - min_lat) / spacing_deg)))
    n_cols = max(1, int(np.ceil((max_lon - min_lon) / spacing_deg)))

    rows = np.arange(n_rows, dtype=float)[:, None]
    cols = np.arange(n_cols, dtype=float)[None, :]
    center_row = (n_rows - 1) / 2.0
    center_col = (n_cols - 1) / 2.0

    # Bearing of each cell from the grid center (0=N, 90=E), vectorized.
    bearing = np.degrees(np.arctan2(cols - center_col, -(rows - center_row)))
    bearing = np.where(bearing < 0, bearing + 360.0, bearing)
    # Meteorological convention: the fire is pushed toward wind_dir + 180.
    downwind = (wind_dir_deg + 180.0) % 360.0
    diff = np.abs(bearing - downwind)
    diff = np.where(diff > 180.0, 360.0 - diff, diff)
    wind_align = np.clip(1.0 - diff / 180.0, 0.0, 1.0)

    # Distance-to-coast proxy: cells far from the edge of the box are deep
    # inland; Kalimantan's real fire belt is inland peat, so weight mildly.
    d_edge = np.minimum(
        np.minimum(rows, (n_rows - 1) - rows),
        np.minimum(cols, (n_cols - 1) - cols),
    )
    inland = np.clip(d_edge / 12.0, 0.0, 1.0)

    # Rough river/peat belts as smooth bands (teaching-grade proxy for the
    # real OSM/peat masks used in the small demo box).
    lat_grid = max_lat - (rows + 0.5) * spacing_deg
    lon_grid = min_lon + (cols + 0.5) * spacing_deg
    peat_band = 0.5 + 0.5 * np.cos((lat_grid - (-1.0)) / 2.5) * np.cos((lon_grid - 113.5) / 3.0)
    peat_band = np.clip(peat_band, 0.0, 1.0)

    base = 0.05
    risk = base + 0.25 * wind_align + 0.15 * peat_band + 0.10 * inland
    risk = np.clip(risk, 0.0, 0.95)
    return risk, bounding_box


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


def save_metrics(metrics: Dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2) + "\n")
    return path


def load_trained_model(
    model_path: Optional[Path] = None,
    metrics_path: Optional[Path] = None,
) -> Tuple[Optional[Model], Dict[str, Any]]:
    """Load the artifacts written by ``python -m src.train``.

    Returns ``(None, {})`` when no model has been trained yet, so callers can
    fall back to the heuristic surface. A corrupt or incompatible model file
    raises instead of being silently ignored.
    """
    path = Path(model_path) if model_path is not None else config.model_path()
    meta = Path(metrics_path) if metrics_path is not None else config.model_metrics_path()
    if not path.exists():
        return None, load_metrics(meta)
    return load_model(path), load_metrics(meta)


def load_metrics(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
