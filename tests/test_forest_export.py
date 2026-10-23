"""The numpy forest copy must score exactly like the scikit-learn model.

``src.train`` writes ``models/risk_rf.npz`` so the app can predict without
importing scikit-learn on the way to its first paint. That shortcut is only
sound while the two paths agree, so this test compares them directly.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from src.ml import load_forest_arrays, save_forest_arrays


def _trained_forest(seed: int = 0) -> RandomForestClassifier:
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(400, 6))
    y = (X[:, 0] + 0.5 * X[:, 1] + rng.normal(scale=0.3, size=400) > 0.4).astype(int)
    model = RandomForestClassifier(n_estimators=25, max_depth=5, random_state=seed)
    model.fit(X, y)
    return model


def test_numpy_forest_matches_sklearn_probabilities(tmp_path):
    model = _trained_forest()
    path = save_forest_arrays(model, tmp_path / "forest.npz")
    assert path is not None

    fast = load_forest_arrays(path)
    rng = np.random.default_rng(1)
    X = rng.normal(size=(200, 6))

    assert float(np.abs(model.predict_proba(X) - fast.predict_proba(X)).max()) == 0.0
    assert (model.predict(X) == fast.predict(X)).all()
    assert fast.n_features_in_ == model.n_features_in_
    assert fast.n_estimators == len(model.estimators_)


def test_numpy_forest_reports_feature_importances(tmp_path):
    model = _trained_forest()
    fast = load_forest_arrays(save_forest_arrays(model, tmp_path / "forest.npz"))

    assert np.allclose(fast.feature_importances_, model.feature_importances_)


def test_save_forest_arrays_ignores_non_forest_models(tmp_path):
    from sklearn.linear_model import LogisticRegression

    model = LogisticRegression().fit(np.array([[0.0], [1.0]]), np.array([0, 1]))
    assert save_forest_arrays(model, tmp_path / "forest.npz") is None
