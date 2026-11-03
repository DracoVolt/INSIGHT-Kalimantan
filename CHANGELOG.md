# Changelog

All notable changes to **INSIGHT — Kalimantan Wildfire Simulation** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [v1.0.0] — 2026-11-03 · *First Public Release*

### 🎉 Highlights

- Full Streamlit app with Windy-style map-first interface
- Random Forest risk model trained on real NASA FIRMS data (ROC-AUC **0.883**)
- Physics-based Cellular Automaton with wind-driven fire spread
- Civilian mitigation guidance (LOW / MEDIUM / HIGH) per settlement cell
- iNaturalist biodiversity overlay for 4 endemic Kalimantan taxa

---

### Added

- **Core CA engine** (`src/ca.py`) — 5-state Moore-neighborhood automaton with wind alignment and peat influence
- **Random Forest pipeline** (`src/ml.py`, `src/train.py`) — temporal train/test split, NumPy-only inference copy (`risk_rf.npz`) to avoid scikit-learn import at page load
- **NASA FIRMS integration** (`src/fire_data.py`) — MODIS/VIIRS hotspot loading, cell-grid mapping, and CA seeding
- **OSM / Overpass integration** (`src/osm.py`) — land cover, water, roads, and settlement extraction for the demo bounding box
- **Feature engineering** (`src/features.py`) — peat flag, water/settlement distances, wind alignment, 1/3/7-day hotspot history
- **Civilian mitigation engine** (`src/mitigation.py`) — rule-based risk classification with timed action cards (prepare / alert / evacuate)
- **iNaturalist biodiversity layer** (`src/bio_v2.py`, `src/bio_loader.py`) — Orangutan, Proboscis monkey, Rafflesia, Nepenthes; offline stub fallback
- **Streamlit app** (`app/main.py`) — Windy-style map shell, CA step slider, risk raster overlay, user location input, live CA state sidebar
- **Kalimantan-wide risk map** — vectorized heuristic risk surface for the whole island rendered as a single raster overlay
- **Land mask** (`src/land_mask.py`) — masks ocean/sea cells from the Kalimantan-wide map using GeoJSON polygon
- **Dev Container** (`.devcontainer/devcontainer.json`) — one-click GitHub Codespaces setup
- **Bundled model** (`models/risk_rf.npz`, `models/risk_rf.joblib`) — pre-trained on 26 912 cell-days, 1 770 MODIS hotspots
- **69 unit tests** — covering CA logic, feature engineering, ML wiring, mitigation rules, land mask, and smoke tests
- **Notebooks** — quickstart, bounding-box exploration, OSM/fire data, CA prototype

### Changed

- Renamed project from *IGNIS-Sim* → **INSIGHT**
- Replaced CartoDB basemap with explicit **OpenStreetMap** tile layer across all Folium maps
- Refactored dot-grid view to a single PNG data URI (was ~700 KB of inline HTML spans; now < 10 KB)
- Moved flora/fauna markers from individual Folium markers to **GeoJSON layers** (cut map size from ~2.8 MB to < 200 KB)
- Cold-start time reduced from ~22 s → ~7 s by scoring with the NumPy forest copy instead of importing scikit-learn
- Water bodies from OSM now act as fire barriers (non-burnable cells) in the CA
- Peat mask from OSM now seeds CA `peat_risk` cells at initialization
- Map shell restyled for **mobile and tablet** (responsive layout, fold tabs, dvh viewport)

### Fixed

- CA `CellState` enum mismatch that caused import errors on app startup
- Streamlit Cloud startup failure (`ModuleNotFoundError: No module named 'src'`) — app now adds repo root to `sys.path` before any import
- Kalimantan bounding box corrected (north edge extended to 7.5°N to include all of Kalimantan)
- `data/cache/`, `.env`, and tool marker files excluded from the repository via `.gitignore`

---

## [0.1.0] — Initial scaffold

- Project skeleton: directory structure, configuration, placeholder modules
- CA prototype in Jupyter notebook (`notebooks/03_ca_prototype.ipynb`)
