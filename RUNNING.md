# How to run INSIGHT (the website/app)

INSIGHT is a **Streamlit** app. Run it with `streamlit run`, not `python -m app.main`.

## TL;DR (Windows, from the project root)

```powershell
# 1. Install dependencies (once)
python -m pip install -r requirements.txt -r requirements-dev.txt

# 2. Start the app
python -m streamlit run app/main.py
```

Then open **http://localhost:8501** in your browser.

> Python 3.10+ is required. This machine currently has Python 3.14.7 with all
> dependencies already installed, so step 1 is a no-op here.

## Run with a virtual environment (recommended)

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m streamlit run app/main.py
```

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/streamlit run app/main.py
```

Always run from the **project root** (the folder containing `app/` and `src/`),
because the code imports `src.*` and `app.*`.

## Why some documented commands don't work

- `python -m app.main` (README and `make app`) only executes the script in
  "bare mode" and exits. It never starts a web server. It prints:
  `Warning: to view this Streamlit app on a browser, run it with ... streamlit run`.
  Use `streamlit run app/main.py` instead.
- The README/Makefile use Unix paths (`python3`, `.venv/bin/...`, `make`).
  On Windows those don't exist. Use `python` and `.venv\Scripts\...`.
- `cp env.example .env` fails because `env.example` is git-ignored and absent.
  You don't need it: the code never loads a `.env` file.

## First start is slow (this is normal)

On a cold start the app downloads OpenStreetMap + iNaturalist data and then
caches it:

- `data/raw/osm_snapshot.json` (~16 MB)
- `data/cache/context_map.npz`
- `data/cache/bio_layers.json`

This can take roughly 1–3 minutes with a working internet connection. The
terminal may sit on "Initializing simulation..." for a while. Later starts reuse
the cache and come up in seconds. If the network is blocked, the app falls back
to offline stubs and still runs.

The trained risk model is already committed (`models/risk_rf.npz`), so no
training step is needed to view the site.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ModuleNotFoundError: streamlit` | `python -m pip install -r requirements-dev.txt` |
| `missing ScriptRunContext` warnings | You ran `python -m app.main`. Use `streamlit run app/main.py`. |
| Port 8501 already in use | `python -m streamlit run app/main.py --server.port 8502` |
| Page is blank / spinner forever | First run is downloading data; watch the terminal. To force a refresh, stop the app and delete `data/cache/`, then start again. |
| Browser doesn't open | `.streamlit/config.toml` sets `headless = true`; open http://localhost:8501 manually. |
| Don't want it exposed on the LAN | Add `--server.address 127.0.0.1`. |

## Deploying (Streamlit Community Cloud)

- Main module: `app/main.py`, branch `master`.
- Cloud installs **`requirements.txt`**, not `requirements-dev.txt`. It now
  includes `streamlit`, `folium`, `streamlit-folium` and `pillow`.
- `app/main.py` adds the repo root to `sys.path` before importing `src`/`app`.
  Cloud runs the `streamlit` executable, which otherwise only adds `app/` to
  the path and fails with `ModuleNotFoundError: No module named 'src'`.
- The cloud container has no `data/cache`, so the first load downloads OSM and
  iNaturalist data (or falls back to the offline stubs) and can take a few
  minutes. Later loads reuse it until the container restarts.

## Quick checks

```powershell
python -m pytest tests/ -q          # 69 tests should pass
curl.exe http://localhost:8501/_stcore/health   # returns: ok
```
