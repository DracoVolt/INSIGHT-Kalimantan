<img width="1597" height="808" alt="Layers view" src="https://github.com/user-attachments/assets/b090a111-b2ee-4ae6-b8aa-cab07dbea804" />
<img width="1598" height="809" alt="Second page" src="https://github.com/user-attachments/assets/79035d4c-f027-42f9-8df4-cd8777b2c488" />
<img width="1599" height="813" alt="First page" src="https://github.com/user-attachments/assets/b9bbade1-5053-4cd7-be78-117e690e3e9d" />

<div align="center">
  <img width="200" alt="INSIGHT Logo" src="https://github.com/user-attachments/assets/9add5bc6-11cf-44a1-88e6-03ee13a922c5" />

  <h1>INSIGHT — Kalimantan Wildfire Simulation</h1>

  <p>
    An interactive wildfire spread simulator and civilian mitigation guide<br/>
    for Central Kalimantan's peatland forests, built as a high-school science project.
  </p>

  <p>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+" /></a>
    <a href="https://streamlit.io"><img src="https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit" /></a>
    <a href="https://scikit-learn.org"><img src="https://img.shields.io/badge/scikit--learn-RandomForest-F7931E?logo=scikit-learn&logoColor=white" alt="scikit-learn" /></a>
    <img src="https://img.shields.io/badge/ROC--AUC-0.883-4CAF50" alt="ROC-AUC 0.883" />
    <a href="LICENSE"><img src="https://img.shields.io/github/license/DracoVolt/INSIGHT-Kalimantan" alt="License" /></a>
  </p>
</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Live Demo](#live-demo)
- [Quick Start](#quick-start)
- [Running the App](#running-the-app)
- [Training the Risk Model](#training-the-risk-model)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
  - [Cellular Automaton (CA)](#cellular-automaton-ca)
  - [Machine Learning Risk Model](#machine-learning-risk-model)
  - [Civilian Mitigation Guidance](#civilian-mitigation-guidance)
  - [Biodiversity Layer](#biodiversity-layer)
- [Data Sources](#data-sources)
- [Model Performance](#model-performance)
- [Configuration](#configuration)
- [Tests](#tests)
- [Limitations](#limitations)
- [License](#license)

---

## Overview

**INSIGHT** is a science-fair-scale prototype that simulates peatland wildfire spread across Central Kalimantan and provides step-by-step civilian mitigation guidance when simulated fire approaches rural areas or settlements.

The demo area covers approximately **222 km × 222 km** around **Palangkaraya / Sebangau / Kahayan** — the heart of Kalimantan's peat swamp forest — at a grid resolution of roughly **4 km × 4 km per cell**.

| What it is | What it is not |
|---|---|
| A transparent, explainable science demo | An operational fire management tool |
| A teaching model with real geospatial data | A production-grade fire spread forecast |
| A full-stack Streamlit app with interactive maps | Emergency advice of any kind |

---

## Features

- 🔥 **Physics-based Cellular Automaton** — wind-driven fire spread across a real geographic grid, seeded from NASA FIRMS hotspot data
- 🤖 **Random Forest risk model** — predicts per-cell ignition likelihood from OSM features, peat flags, wind alignment, and hotspot history; scores ROC-AUC **0.883** on a temporal hold-out
- 🗺️ **Interactive Folium maps** — fire risk raster overlay, flora & fauna biodiversity layer, Kalimantan-wide coarse risk view, and a full OSM basemap
- 👥 **Civilian mitigation guidance** — rule-based LOW / MEDIUM / HIGH alerts for settlement and rural cells, with specific timed actions at each risk level
- 🌿 **Biodiversity layer** — iNaturalist observations for Orangutan, Proboscis monkey, Rafflesia, and Nepenthes overlaid on the fire map
- 🧭 **User location input** — enter your lat/lon to receive personalised mitigation advice and a nearby-cell summary
- ⚡ **Fast cold start** — the trained forest is stored as a dependency-free NumPy archive (`risk_rf.npz`); scikit-learn is not imported at page-load time

---

## Live Demo

> Deploy to **Streamlit Community Cloud** in one click:
> 1. Fork this repo
> 2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
> 3. Set main module to `app/main.py`, branch `master`
> 4. Click **Deploy** — `requirements.txt` is installed automatically

The first cloud load downloads OpenStreetMap + iNaturalist data (≈ 1–3 min). Later loads use the cached snapshot.

---

## Quick Start

**Requires Python 3.10+.**

```bash
# 1. Clone the repo
git clone https://github.com/DracoVolt/INSIGHT-Kalimantan.git
cd INSIGHT-Kalimantan

# 2. Create a virtual environment
python -m venv .venv

# 3. Install dependencies
# macOS / Linux
.venv/bin/pip install -r requirements.txt

# Windows PowerShell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 4. Run the app
# macOS / Linux
.venv/bin/streamlit run app/main.py

# Windows PowerShell
.\.venv\Scripts\python.exe -m streamlit run app/main.py
```

Then open **http://localhost:8501** in your browser.

> **Note:** The trained model (`models/risk_rf.npz`) is already committed — no training step is needed to view the app.

---

## Running the App

Always run from the **project root** (the directory containing `app/` and `src/`):

```bash
python -m streamlit run app/main.py
```

### First-run behaviour

On a cold start, the app downloads and caches:

| File | Size | What it is |
|---|---|---|
| `data/raw/osm_snapshot.json` | ~16 MB | OpenStreetMap extract for the demo bbox |
| `data/cache/context_map.npz` | small | Pre-computed OSM cell masks |
| `data/cache/bio_layers.json` | small | iNaturalist observation cache |

This takes roughly **1–3 minutes** with a working internet connection. Later starts reuse the cache and load in seconds. If the network is unavailable, the app falls back to offline stubs and still runs.

### Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: streamlit` | `pip install -r requirements.txt` |
| `missing ScriptRunContext` warnings | You ran `python -m app.main`. Use `streamlit run app/main.py` instead. |
| Port 8501 already in use | `python -m streamlit run app/main.py --server.port 8502` |
| Page is blank / spinner forever | First run downloads data; watch the terminal. Delete `data/cache/` to force a refresh. |
| Browser doesn't open automatically | `.streamlit/config.toml` sets `headless = true`; open http://localhost:8501 manually. |

---

## Training the Risk Model

The risk map is produced by a **Random Forest** trained on real NASA FIRMS data, not a hand-written formula. A pre-trained model is committed to this repo, but you can retrain it on a fresh FIRMS export:

1. Download a 7-day NASA FIRMS MODIS/VIIRS CSV from [firms.modaps.eosdis.nasa.gov](https://firms.modaps.eosdis.nasa.gov/)
2. Run the training script:

```bash
python -m src.train --firms data/raw/MODIS_C6_1_Global_7d.csv
```

The script:
- Filters the global CSV to the demo bounding box (writing `data/raw/firms_hotspots.csv` for CA seeding)
- Builds OSM-derived features and performs a **temporal train/test split** (last 20% of days as test)
- Evaluates on the held-out days and prints metrics
- Writes `models/risk_rf.joblib` + `models/risk_rf_metrics.json`
- Also writes `models/risk_rf.npz` — a flat NumPy copy of the forest used by the app at inference time (avoids importing scikit-learn on page load, saving ~15 s)

---

## Project Structure

```
INSIGHT-Kalimantan/
│
├── app/                        # Streamlit application
│   ├── main.py                 # App entry point (1 300 lines, full UI)
│   ├── ca_simulator.py         # Simulation state management for the UI
│   └── __init__.py
│
├── src/                        # Core library (importable independently)
│   ├── config.py               # All constants & bounding-box config
│   ├── ca.py                   # Cellular Automaton engine
│   ├── ml.py                   # Random Forest model + NumpyForest inference
│   ├── train.py                # CLI training script (python -m src.train)
│   ├── features.py             # Feature engineering for the ML model
│   ├── fire_data.py            # FIRMS hotspot loading & cell grid
│   ├── osm.py                  # OpenStreetMap / Overpass integration
│   ├── osm_stub.py             # Offline stub for OSM data
│   ├── land_mask.py            # Land/water mask for the Kalimantan map
│   ├── mitigation.py           # Civilian mitigation rule engine
│   ├── bio_v2.py               # iNaturalist API v2 client
│   ├── bio_loader.py           # Loads & caches biodiversity layers
│   ├── bio_stub_fixture.json   # Offline fallback observation data
│   ├── icons.py                # SVG icon helpers
│   └── __init__.py
│
├── data/
│   ├── raw/
│   │   └── firms_hotspots.csv  # Bundled 7-day MODIS export (1 770 hotspots)
│   └── README.md
│
├── models/
│   ├── risk_rf.joblib          # Trained Random Forest (scikit-learn)
│   ├── risk_rf.npz             # Dependency-free NumPy copy (used at runtime)
│   └── risk_rf_metrics.json    # Evaluation metrics from training
│
├── assets/
│   ├── geo/
│   │   └── kalimantan_land.geojson   # Kalimantan land polygon
│   └── icons/
│       ├── orangutan.svg
│       ├── proboscis-monkey.svg
│       ├── rafflesia.svg
│       ├── nepenthes.svg
│       └── default.svg
│
├── notebooks/
│   ├── 00_quickstart.ipynb
│   ├── 01_explore_bounding_box.ipynb
│   ├── 02_osm_and_fire_data.ipynb
│   └── 03_ca_prototype.ipynb
│
├── tests/                      # 69 unit tests (pytest)
│   ├── test_ca.py
│   ├── test_features.py
│   ├── test_ml_wiring.py
│   ├── test_mitigation.py
│   ├── test_land_mask.py
│   ├── test_icons.py
│   ├── test_smoke.py
│   └── ...
│
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Dev/test dependencies
├── pyproject.toml
├── Makefile
├── RUNNING.md                  # Detailed run instructions
├── DATA-SOURCES.md             # Data provenance and licenses
└── LICENSE
```

---

## How It Works

The simulation has two connected parts that share the same geographic grid.

### Cellular Automaton (CA)

```
State machine per cell:
  healthy ──► igniting ──► burning ──► burned
  peat_risk ──► igniting ──► burning ──► burned
```

Each cell on a **~4 km × 4 km grid** can be `healthy`, `igniting`, `burning`, `burned`, or `peat_risk`. At every time step:

1. All currently `burning` / `igniting` cells transition to `burned`
2. Each burning cell probabilistically ignites its **8-neighborhood** (Moore) neighbors

The ignition probability for a given src → dst edge is:

$$P = P_{\text{base}} + \alpha \cdot \text{wind\_alignment} + \beta \cdot \text{peat\_flag}$$

| Parameter | Default | Meaning |
|---|---|---|
| `P_base` | 0.15 | Base spread probability |
| `α` (wind strength) | 0.25 | Extra probability when neighbor lies downwind |
| `β` (peat influence) | 0.20 | Extra probability when neighbor is peat-risk land |

Wind alignment is computed from the meteorological convention (direction fire blows *from*), so a wind from the east pushes the fire westward. Rivers and water bodies from OSM act as natural firebreaks — those cells are marked non-burnable.

### Machine Learning Risk Model

A **Random Forest** (200 trees, max depth 8) trained on MODIS fire hotspot data predicts the probability of fire presence for each cell-day.

**Features:**
| Feature | Description |
|---|---|
| `peat_risk_flag` | OSM-derived peat land flag |
| `distance_to_nearest_water_cell` | Proximity to rivers/lakes (cells) |
| `distance_to_nearest_settlement_cell` | Proximity to villages/towns (cells) |
| `wind_alignment` | How much the cell lies downwind |
| `has_hotspot_last_1_day` | Binary: hotspot in the last 1 day |
| `has_hotspot_last_3_days` | Binary: hotspot in the last 3 days |
| `has_hotspot_last_7_days` | Binary: hotspot in the last 7 days |
| `hotspot_count_last_7_days` | Count of hotspots in 7-day window |
| `distance_to_nearest_hotspot_cell` | Proximity to the nearest recent hotspot |
| `cell_row`, `cell_col` | Grid position |

The ML risk map seeds and modulates the CA. When no trained model is present the app falls back to a physics heuristic (wind + peat + settlement/water distances) and says so in the sidebar.

### Civilian Mitigation Guidance

When the CA predicts fire approaching a rural or settlement cell, the app classifies the risk and shows timed action cards:

| Risk level | Trigger | Example actions |
|---|---|---|
| 🟡 **LOW** | Predicted risk > 0.2 | Prepare evacuation route, clear dry debris |
| 🟠 **MEDIUM** | Igniting cell within 3 cells | Alert neighbors, wet the perimeter, protect peat areas |
| 🔴 **HIGH** | Burning cell within 1 cell, or risk > 0.5 | Evacuate early, contact authorities, secure livestock |

Users can enter their own latitude/longitude to receive personalised advice for their location.

> ⚠️ **These are demonstration actions for a science project. They are not emergency advice.**

### Biodiversity Layer

The app fetches research-grade observations from the **iNaturalist API** for four flagship Kalimantan taxa and overlays them on the fire map. The convex hull of each taxon's observation points is drawn as a dashed polygon to show the species' range relative to the simulated fire path.

| Taxon | Marker color |
|---|---|
| Orangutan | Violet `#7b3ff2` |
| Proboscis monkey | Cyan `#00c2d1` |
| Rafflesia arnoldii | Magenta `#e91ec4` |
| Nepenthes (pitcher plants) | Lime `#b5e61d` |

An offline JSON fixture (`src/bio_stub_fixture.json`) is used as fallback when the API is unavailable.

---

## Data Sources

| Source | Used for | License |
|---|---|---|
| [OpenStreetMap](https://www.openstreetmap.org/) via [Overpass API](https://overpass-api.de/) | Land cover, water, roads, settlements | ODbL |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) (MODIS/VIIRS) | Fire hotspot labels and CA seeding | NASA data use terms |
| [iNaturalist](https://www.inaturalist.org/) API v2 | Flora & fauna observation layer | CC0 / CC-BY / CC-BY-NC per observer |
| Kalimantan GeoJSON (`assets/geo/`) | Land mask for the Kalimantan-wide map | Derived from OSM |

See [`DATA-SOURCES.md`](DATA-SOURCES.md) for full details, download steps, and license notes.

**Demo bounding box:** `(112.5°E, 3.5°S) → (114.5°E, 1.5°S)` — Central Kalimantan around Palangkaraya, Sebangau, and the Kahayan peatland forest.

---

## Model Performance

Trained on the bundled 7-day MODIS export (**1,770 hotspots** in the demo box, **26,912 cell-days**, **3.24% positive rate**) with a **temporal split** (last 2 days as test set):

| Metric | Value |
|---|---|
| **ROC-AUC** | **0.883** |
| **PR-AUC** | **0.283** |
| Accuracy | 0.975 |
| Precision | 0.443 |
| Recall | 0.166 |
| Test rows | 6,728 |
| Test positives | 163 |

A PR-AUC of 0.283 over a 3.2% base rate means the **top-ranked cells are roughly 9× more likely to burn than average**. This is a genuine signal, not overfitting — the split is temporal, not random.

---

## Configuration

All project constants live in [`src/config.py`](src/config.py). Key values:

```python
# Bounding box (Central Kalimantan)
_MIN_LON, _MIN_LAT = 112.5, -3.5
_MAX_LON, _MAX_LAT = 114.5, -1.5

# Grid resolution (~4 km per cell)
_GRID_SPACING_DEG = 0.035

# CA parameters
CA_SPREAD_BASE            = 0.15   # base ignition probability
CA_WIND_ALIGNMENT_STRENGTH = 0.25  # wind bonus
CA_PEAT_INFLUENCE          = 0.20  # peat bonus

# Default wind direction (meteorological: degrees FROM)
DEFAULT_WIND_DIR_DEG = 90.0        # from the east

# ML
ML_MODEL_TYPE    = "random_forest"
ML_TEST_FRACTION = 0.20
```

---

## Tests

```bash
# Install dev dependencies (pytest etc.)
pip install -r requirements-dev.txt

# Run all 69 tests
python -m pytest tests/ -q
```

Tests cover the CA step logic, feature engineering, ML wiring, mitigation rule engine, land mask, icons, and a smoke test of the full simulation pipeline.

---

## Limitations

This is a **1-month high-school science project prototype**. Known limitations:

- **Simplified physics:** the CA is a teaching model, not an operational fire spread model (e.g., no fuel moisture, no terrain slope, no ember transport)
- **Demo bounding box only:** the CA runs on a small 2° × 2° area; the Kalimantan-wide map is a fast heuristic, not the full model
- **Wind is static:** the default simulation uses a single wind direction for all steps; real fire spread varies hour by hour
- **ML baseline:** the Random Forest is intentionally simple (200 trees, depth 8) and trained on a small 7-day export
- **Civilian guidance is illustrative:** the mitigation actions are demonstration rules for a science project and are not vetted emergency advice
- **Data completeness:** OSM coverage in rural Central Kalimantan may be incomplete; peat masks are approximated from land-cover tags

---

## License

See [`LICENSE`](LICENSE) for the full text.

> **Note:** This project is a science-fair prototype. It is not an emergency response system. Do not use its outputs to make real fire management or evacuation decisions.
