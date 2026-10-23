# INSIGHT

Wildfire spread simulation and civilian-mitigation guidance for Central Kalimantan,
built as a high-school science project that combines:

- OpenStreetMap data (land cover, water, roads, settlements) for a demo bounding box
- NASA FIRMS wildfire hotspot data (MODIS/VIIRS)
- A physics-based Cellular Automaton (CA) that predicts fire spread using public
  variables such as wind direction
- A lightweight machine-learning model (scikit-learn) that predicts which cells are
  most likely to ignite next
- Simple civilian-mitigation guidance when simulated fire approaches rural areas

Demo bounding box: Central Kalimantan around Palangkaraya / Sebangau / Kahayan
peatland forest, about 2 degrees longitude by 2 degrees latitude, with a grid
resolution of about 4 km × 4 km per cell.

## What this is

A science-fair-scale prototype. The goal is not a production fire model; it is a
transparent, explainable demo that shows:

- how real geospatial and fire data can be loaded for the Palangkaraya area
- how a CA update rule can move fire through a grid using wind direction and
  fuel/peat information
- how a simple ML classifier can rank cells by ignition likelihood
- how civilians can respond when a simulated fire approaches a settlement or
  rural area

## Quick start

Requires Python 3.10+ and a working `pip`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp env.example .env
# edit .env with any API keys or paths you want to override
```

Then run the demo app:

```bash
.venv/bin/python -m app.main
```

If you prefer, you can also run a Streamlit app directly:

```bash
.venv/bin/streamlit run app/main.py
```

The first time you run the project, the data download scripts will attempt to fetch
OSM and FIRMS data for the configured bounding box. Those steps can also be run
manually from the notebooks in `notebooks/`.

## Train the risk model

The risk map is a trained Random Forest, not a hand-written formula. Download a
7-day NASA FIRMS export (https://firms.modaps.eosdis.nasa.gov/) and train:

```bash
.venv/bin/python -m src.train --firms data/raw/MODIS_C6_1_Global_7d.csv
```

Training filters the export to the demo box (writing `data/raw/firms_hotspots.csv`
for CA seeding), caches the OSM snapshot so training and inference share the same
masks, evaluates on the last 20% of days, and writes `models/risk_rf.joblib` plus
`models/risk_rf_metrics.json`. The app loads those files on start and conditions
its prediction on the most recent FIRMS day; if they are missing it falls back to
the heuristic baseline and says so in the sidebar.

`src.train` also writes `models/risk_rf.npz`, a plain-array copy of the forest.
The app scores cells from that copy, so a cold page load never imports
scikit-learn (~7 s of the first render); `risk_rf.joblib` stays the training
artifact and is only unpickled when the `.npz` is missing or older.

Trained on the bundled 7-day MODIS export (1,770 hotspots in the demo box over 8
days, 26,912 cell-days, 3.2% positive), the forest scores ROC-AUC 0.883 and
PR-AUC 0.283 on the two held-out final days. That is a genuine prediction, but a
modest one: PR-AUC 0.283 over a 0.032 base rate means the top-ranked cells are
roughly nine times likelier to burn than average, not that any single cell will.

## Repository layout

```
insight-kalimantan/
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── env.example
├── Makefile
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── README.md
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── osm.py
│   ├── fire_data.py
│   ├── features.py
│   ├── ca.py
│   ├── ml.py
│   ├── train.py
│   ├── land_mask.py
│   └── mitigation.py
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── ca_simulator.py
│
├── notebooks/
│   ├── 01_explore_bounding_box.ipynb
│   ├── 02_osm_and_fire_data.ipynb
│   └── 03_ca_prototype.ipynb
│
├── docs/
│   ├── project-report.md
│   ├── methods.md
│   └── civilian-mitigation.md
│
├── assets/
│   ├── icons/
│   └── geo/kalimantan_land.geojson
│
├── models/
│   ├── risk_rf.joblib
│   ├── risk_rf.npz
│   └── risk_rf_metrics.json
│
├── tests/
└── figures/
```

## Data sources

See `data/README.md` and `DATA-SOURCES.md` for the exact sources, licenses, and
download steps for:

- OpenStreetMap data for the bounding box (Overpass API or pre-downloaded extracts)
- NASA FIRMS hotspot data (MODIS/VIIRS)
- Peatland and hydrology context for the Kahayan / Sebangau area
- Wind direction information for the simulation and ML features

## Methods in brief

The simulation has two connected parts:

1. A Cellular Automaton over a 4 km × 4 km grid. Each cell can be
   `healthy`, `igniting`, `burning`, `burned`, or `peat_risk`. The update rule
   spreads fire to neighboring cells with a probability that depends on wind
   direction, fuel presence, and peatland risk.
2. A machine-learning classifier that predicts, for each cell and day, the
   likelihood of fire presence using features such as recent hotspots, wind
   direction, peat flag, distance to water/river/settlements, and OSM land cover.

The two parts are connected by using ML predictions to inform CA initialization or
seeding, and by using the CA state to decide when to show civilian-mitigation
advice.

## Civilian mitigation

See `docs/civilian-mitigation.md` for the rule set used in the demo. In short, when
the CA predicts fire approaching a rural or settlement cell, the app suggests a small
set of actions such as early evacuation, perimeter damping, avoiding peat drainage
actions that can worsen fire spread, alerting neighbors, and contacting local
authorities. These are demonstration actions for a science project, not emergency
advice.

## Limitations

This is a 1-month high-school science project prototype. Limitations include:

- Simplified physics: the CA is a teaching model, not an operational fire spread model
- Data quality and availability for the demo bounding box may be incomplete
- The ML model is a baseline classifier meant to be explained, not a tuned production
  system
- Wind and weather inputs are simplified for the demo
- The civilian-mitigation guidance is illustrative only

## Science-fair framing

Problem: peatland wildfires in Central Kalimantan can threaten rural communities and
are influenced by wind, fuel, and peat conditions.

Methods: OSM + fire data → grid → CA wind-driven spread + ML hotspot prediction →
mitigation timing.

Results: simulated fire spread, ranked high-risk cells, and suggested civilian
response timing for the demo area.

## License

See `LICENSE`.

## Note

This project is a science-fair prototype and is not an emergency response system.
