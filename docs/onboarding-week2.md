# INSIGHT Kalimantan — Week 2 Onboarding

**Project:** Wildfire mitigation simulation for Central Kalimantan (Palangkaraya / Sebangau / Kahayan peatland area).
**Audience:** High-school physics/science project. Feasible in ~1 month. Uses OSM + FIRMS data, a physics cellular-automaton (CA) fire-spread model, and a baseline ML classifier.
**Current status:** End-to-end Streamlit demo running locally. Correct Kalimantan bounding box (112.5°E, 3.5°S → 114.5°E, 1.5°S). 60/60 tests passing, and the risk map is a trained Random Forest conditioned on the latest FIRMS day.

---

## What's done

- **CA core** (`src/ca.py`): 8-neighbor Moore grid, wind-aligned spread probability, peat-risk influence, seeded either from FIRMS hotspots or a default center cell. Deterministic via `random_seed`.
- **ML pipeline** (`src/ml.py`, `src/features.py`): explainable feature table (distance to water/settlement, peat flag, hotspot history, wind alignment) and a scikit-learn classifier (random forest / logistic regression). Falls back to a transparent heuristic risk baseline when no trained model exists.
- **Mitigation logic** (`src/mitigation.py`): tiered civilian guidance (LOW / MEDIUM / HIGH) for settlement and rural cells near active fire. Risk level derived from nearest burning/igniting distance and predicted risk.
- **App** (`app/main.py`): Controls sidebar (wind direction, FIRMS toggle, CA steps), fire-spread panel, risk map, mitigation guidance list, CA explanation expander, and a **Your location** popup demo (lat/lon → cell → popup + nearby-cells summary).
- **Location helpers** (`src/mitigation.py`): `loc_to_cell`, `cell_center_lat_lon`, `cells_within_radius` — importable for the app.
- **Offline OSM stub** (`src/osm_stub.py`): `make_kalimantan_stub_snapshot()` seeds a handful of river, settlement, and peat features inside the box so the demo shows inland Indonesian content even without a live Overpass query.

---

## Day 1 (Week 2) — make the demo look Indonesian and inland-focused

### 1. Wire the offline stub into the context map build
Today `build_context_map()` is called with no snapshot, so the context map is all-blank (0 water / 0 settlement / 0 peat). That's why the risk map baseline looks flat and the mitigation panel is sparse.

**Goal:** when no live OSM snapshot is available, fall back to `make_kalimantan_stub_snapshot()` so the app immediately shows:
- water (Kahayan / Sebangau river points, a lake)
- 3 settlement cells (village/hamlet)
- 3 peat/wetland cells

One minimal change: in `app/ca_simulator.py`'s `initialize_simulation`, try to load a cached OSM snapshot (`osm_snapshot.json`) from `data/raw/`; if missing, use the stub. In `src/features.py`, `build_context_map` already accepts an optional snapshot — pass it through from the app layer.

### 2. Verify inland-only surface
After wiring the stub, confirm:
- `ctx.is_water.sum() > 0`
- `ctx.is_settlement.sum() > 0`
- `ctx.is_peat_risk.sum() > 0`
- the risk map panel and mitigation panel render populated content in the Preview tab

### 3. Confirm the Your-location popup
In the Preview tab, type a lat/lon inside the box (e.g. `-2.5, 113.0`) and confirm the popup card + nearby summary appear with real content. If the popup renders but says "No immediate mitigation guidance", that's fine for Day 1 — the point is that the wiring works.

**Acceptance:** Preview tab shows a populated Indonesian inland scenario with the popup working.

---

## Day 2 (Week 2) — zoom cap + tree-graphic cells (feasible scope)

### Zoom: cap the farthest-out zoom to Indonesia
**Question to resolve first (ask the user or decide):** which map layer is being used?

- If the risk map is the built-in `st.map(...)` (OpenStreetMap tiles via Folium under the hood), then "cap zoom to Indonesia" means: set the map's initial view and **max bounds** to Indonesia's rough lat/lon envelope, and/or set `max_zoom` so the user cannot zoom out past continental view. Streamlit's `st.map` exposes limited control; you may want to switch to an explicit `folium` map rendered via `st_folium` (from `streamlit-folium`) so you can set `max_bounds` and `max_zoom` precisely.

- If you want the *entire app* to feel Indonesia-scoped, also set `st.map`'s default center to the Kalimantan box and a zoom level that shows Indonesia (not the whole world).

**Recommendation for a high-school project:** use `streamlit-folium` (already a dev dependency candidate) and build the map once with `folium.Map(location=..., zoom_start=..., max_bounds=Indonesia_bounds, max_zoom=...)`. This is the cleanest way to enforce "Indonesia is the farthest you can zoom out."

**Open question:** do you want the zoom cap on the risk map only, or on the whole app's map view? Decide and I'll implement.

### Tree-graphic cells with animation
**What's possible and what isn't:**

- **Streamlit-native animation of per-cell tree graphics:** not really. Streamlit reruns the whole script on each interaction; it's not a frame-based animation canvas. For smooth frame-by-frame CA animation you'd normally use something with a real render loop (matplotlib `FuncAnimation`, PyGame, a browser canvas/SVG app, or a Dash app with clientside callbacks).

- **What IS feasible in Streamlit and good for a high-school demo:**
  - Render each cell as a **tree glyph** using a custom `st.html` / SVG snippet, or a matplotlib scatter where each point is a tree icon (via `matplotlib` markers or an image marker). Then let the user step through CA frames with the existing "CA step" slider — each step re-renders the tree grid with updated colors (healthy green → igniting orange → burning red → burned brown). That's "animation" in the sense of frame-step visualization, which is exactly what a science-fair demo needs.
  - If you upload a tree image later, we can use it as a per-cell marker: healthy cells show the tree graphic, burning cells show an "on fire" variant, burned cells show a charred/stump variant.

- **Better fit for smooth animation:** if you want real animated spreading (auto-play frames, tweening), the right move is a small separate viewer — e.g. a matplotlib animation saved to `figures/`, or an HTML/SVG preview. That can be a later enhancement after the Streamlit demo is solid.

**Recommendation for Week 2:** implement **tree-glyph cell rendering in the Streamlit risk/fire map** with frame-stepping (the existing slider already gives you the "play" feel), using a simple color-coded tree icon per cell. Keep a placeholder for your uploaded tree image — e.g. a function `cell_leaf(asset_path=None)` that returns an SVG or image marker, defaulting to a simple drawn tree when no asset is uploaded yet.

**Open question:** do you want the tree graphic on the *risk map*, the *fire-spread view*, or both? And do you want frame auto-play (a "play" button that advances CA steps automatically) in addition to the slider?

---

## Project layout (already set up)

```
.
├─ app/
│  ├─ __init__.py
│  ├─ main.py            # Streamlit app entrypoint
│  └─ ca_simulator.py   # SimState / initialize_simulation / step_forward
├─ src/
│  ├─ __init__.py
│  ├─ config.py          # bounding box, grid spacing, CA/ML/mitigation params
│  ├─ ca.py             # CellState, CaGrid, CaParams, step, run_simulation
│  ├─ features.py       # ContextMap, build_context_map, feature table
│  ├─ fire_data.py      # Hotspot, CellGrid, FIRMS CSV load, FireDataset
│  ├─ fire_data_stub.py # fake data for tests/offline
│  ├─ ml.py             # make_model, train, predict_risk_map, save/load
│  ├─ ml_stub.py        # stub training on fake data
│  ├─ mitigation.py     # risk levels, actions, contexts, location helpers
│  ├─ osm.py            # Overpass fetch + parse
│  └─ osm_stub.py       # offline Kalimantan stub snapshot (NEW)
├─ tests/
│  ├─ test_ca.py
│  ├─ test_features.py
│  ├─ test_mitigation.py
│  └─ test_smoke.py
├─ docs/
│  ├─ project-report.md
│  ├─ methods.md
│  ├─ civilian-mitigation.md
│  └─ onboarding-week2.md   # this file
├─ data/
│  ├─ raw/              # .gitignored — put firms_hotspots.csv / osm_snapshot.json here
│  └─ processed/        # .gitignored
├─ figures/             # .gitignored
├─ .gitignore
├─ pyproject.toml
├─ requirements.txt
└─ README.md
```

---

## How to rerun the preview (port 8501)

From the project root:

```bash
# 1) confirm nothing broke
python3 -m pytest -q

# 2) launch detached (Windows PowerShell)
powershell -NoProfile -Command \
  "$p = (Start-Process -FilePath 'python3.exe' \
    -ArgumentList '-m','streamlit','run','app/main.py',\
      '--server.port','8501','--server.address','127.0.0.1','--server.headless','true' \
    -RedirectStandardOutput '.freebuff/preview-07503b07-df48-424e-b8b6-2cd54b7ad71c.log' \
    -RedirectStandardError '.freebuff/preview-07503b07-df48-424e-b8b6-2cd54b7ad71c.log.err' \
    -WindowStyle Hidden -PassThru).Id; \
   sleep 6; \
   Get-Process -Id $p -ErrorAction SilentlyContinue | Select-Object Id,ProcessName; \
   echo 'PID:' $p"
```

Then confirm health:

```bash
python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health').read().decode())"
```

If the old process is stale, kill it first:

```bash
powershell -NoProfile -Command "Stop-Process -Id <PID> -ErrorAction SilentlyContinue; sleep 2; echo killed"
```

**Note:** when `app/main.py` or `src/*.py` changes, Streamlit's auto-rerun may not pick up module changes if the process was started before the edit. If the Preview tab still shows old content after a file edit, kill and relaunch (the recipe above) — that's the reliable way.

---

## Open decisions to make before deeper work

1. **Inland-only + zoom cap:** confirm whether to implement this via `streamlit-folium` with `max_bounds`, or only on the existing `st.map`. If the latter, the zoom cap is limited; if the former, it's straightforward.
2. **Tree graphic:** when you upload the tree image, what format is it (PNG/SVG)? Do you want one tree icon reused per cell (colored by state), or separate healthy/burning/burned icons? And should it appear on the risk map, the fire-spread view, or a dedicated cell-grid viewer?
3. **Auto-play animation:** do you want a Play button that auto-advances CA steps on a timer, or is frame-stepping via the slider enough for Week 2?
4. **Real data:** by when do you want to attempt the real Overpass + FIRMS download path vs. keep the stub for the demo? (The stub is already good enough for a science-fair booth; real data is a Week 3+ enhancement.)

---

## Reality check for a 1-month high-school project

The current scaffold is already enough for a credible demo:
- transparent CA physics with wind
- an ML classifier that can be trained and explained
- civilian mitigation guidance
- a working Streamlit app with a location popup

Week 2's realistic goal is **make the demo look Indonesian and inland-focused, add the zoom cap, and add a tree-glyph cell view** — not to build a production GIS. The tree-graphic animation is best kept as frame-step visualization in Streamlit plus a separate matplotlib/HTML animation if you want smooth auto-play later.
