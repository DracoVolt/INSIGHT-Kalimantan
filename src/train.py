"""Train the INSIGHT fire-risk Random Forest from real NASA FIRMS hotspots.

Usage:
    python -m src.train --firms data/raw/MODIS_C6_1_Global_7d.csv

The input can be the global 7-day FIRMS CSV or any FIRMS export that covers the
demo bounding box. Rows outside the box or below the confidence threshold are
dropped, and the filtered subset is written to ``data/raw/firms_hotspots.csv``
so the app seeds the CA from the same hotspots the model was trained on.

The model and its metrics are written to ``models/`` and picked up by the app on
the next run. Features are computed from a cached OSM snapshot
(``data/raw/osm_snapshot.json``) so training and inference share the same water,
settlement and peat masks.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from src import config
from src.features import build_context_map
from src.fire_data import build_cell_grid, build_fire_dataset, load_firms_csv
from src.ml import (
    feature_importance_table,
    save_forest_arrays,
    save_metrics,
    save_model,
    train,
)


def _export_demo_subset(df, min_confidence: float = 50.0) -> Path:
    """Write the bbox-limited hotspots the app should use for seeding."""
    min_lon, min_lat, max_lon, max_lat = config.bounding_box()
    mask = (
        df["lon"].between(min_lon, max_lon)
        & df["lat"].between(min_lat, max_lat)
        & (df["confidence"] >= min_confidence)
    )
    subset = df[mask]
    path = config.firms_data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    subset.to_csv(path, index=False)
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Train the INSIGHT risk model.")
    parser.add_argument(
        "--firms",
        default=str(config.firms_data_path()),
        help="FIRMS CSV (global 7-day export or a pre-filtered file)",
    )
    parser.add_argument("--model", default=str(config.model_path()))
    parser.add_argument("--metrics", default=str(config.model_metrics_path()))
    parser.add_argument(
        "--wind",
        type=float,
        default=config.default_wind_direction_deg(),
        help="Wind direction used for the wind-alignment feature (meteorological)",
    )
    parser.add_argument("--random-state", type=int, default=config.ml_random_state())
    parser.add_argument(
        "--stub-osm",
        action="store_true",
        help="Use the offline OSM stub instead of fetching/caching Overpass data",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Do not rewrite data/raw/firms_hotspots.csv from the input file",
    )
    args = parser.parse_args(argv)

    firms_path = Path(args.firms)
    if not firms_path.exists():
        print(
            f"FIRMS file not found: {firms_path}\n"
            "Download a 7-day export from https://firms.modaps.eosdis.nasa.gov/ "
            "and pass it with --firms.",
            file=sys.stderr,
        )
        return 2

    df = load_firms_csv(firms_path)
    print(f"Loaded {len(df):,} FIRMS rows from {firms_path}")

    if not args.no_export:
        exported = _export_demo_subset(df)
        print(f"Wrote demo hotspot subset to {exported}")

    grid = build_cell_grid()

    if args.stub_osm:
        from src.osm_stub import make_kalimantan_stub_snapshot

        snapshot = make_kalimantan_stub_snapshot()
        print("Using offline OSM stub")
    else:
        from src.osm import load_or_fetch_snapshot

        snapshot = load_or_fetch_snapshot()
        print(f"OSM snapshot: {len(snapshot.features):,} features")

    context_map = build_context_map(osm_snapshot=snapshot, cell_grid=grid)
    dataset = build_fire_dataset(df, bounding_box=config.bounding_box(), cell_grid=grid)

    print(
        f"Dataset: {len(dataset.hotspots):,} hotspots, "
        f"{len(dataset.labeled_days)} days, grid {grid.n_rows}x{grid.n_cols}"
    )

    model, metrics, train_df, test_df = train(
        dataset,
        context_map,
        wind_dir_deg=args.wind,
        random_state=args.random_state,
        test_fraction=config.ML_TEST_FRACTION,
    )

    model_path = Path(args.model)
    metrics_path = Path(args.metrics)
    save_model(model, model_path)
    save_metrics(metrics, metrics_path)

    # The app loads this numpy copy, which keeps scikit-learn (and scipy) out of
    # the page-load import path.
    arrays_path = save_forest_arrays(model, model_path.with_suffix(".npz"))

    print(f"\nSaved model to {model_path}")
    print(f"Saved metrics to {metrics_path}")
    if arrays_path is not None:
        print(f"Saved numpy forest to {arrays_path}")
    print()
    for key in ("split_mode", "n_test_days", "n_train_rows", "n_test_rows", "n_test_positives"):
        print(f"  {key}: {metrics[key]}")
    for key in ("accuracy", "precision", "recall", "roc_auc", "average_precision"):
        print(f"  {key}: {metrics[key]:.3f}")

    importance = feature_importance_table(model)
    print("\nTop features:")
    print(importance.head(6).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
