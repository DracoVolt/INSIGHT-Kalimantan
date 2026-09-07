# Data

This directory holds the project's data pipeline artifacts.

## Layout

- `raw/` — original downloads (OSM snapshot JSON, FIRMS CSV, wind files, etc.)
- `processed/` — cleaned feature tables, cell grids, and other derived artifacts

Do not commit large raw raster files unless the project needs them for the demo.
Prefer small CSVs and OSM extracts for this science-fair-scale project.

## Download order

1. Place a FIRMS hotspot CSV in `raw/firms_hotspots.csv` (or set `FIRMS_HOTSPOTS_FILE`
   in `.env`).
2. Run `python -m src.osm fetch` or the equivalent notebook to build an OSM snapshot
   in `raw/osm_snapshot.json`.
3. Run the notebooks in `notebooks/` to inspect and clean the data.

## Files

- `raw/osm_snapshot.json` — OSM features for the bounding box
- `raw/firms_hotspots.csv` — FIRMS hotspot CSV
- `processed/*.parquet` or `*.csv` — feature tables and cell grids produced by the
  pipeline

## Sources

See `../DATA-SOURCES.md` for links, licenses, and access notes.
