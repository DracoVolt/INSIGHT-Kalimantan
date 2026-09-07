# Data sources

This document records the data sources used by IGNIS-Sim Kalimantan, where to get
them, and what license or terms apply.

The demo bounding box is:

- Min longitude: -2.6
- Min latitude: 2.4
- Max longitude: -0.6
- Max latitude: 4.4

That is a 2-degree-by-2-degree box in Central Kalimantan, anchored on the
Palangkaraya / Sebangau / Kahayan peatland forest area.

## 1. OpenStreetMap data

Used for: land cover, water bodies, rivers, roads, settlements, boundaries.

Source: OpenStreetMap via the Overpass API or pre-downloaded extracts.

- Overpass API: https://overpass-api.de/
- Overpass Turbo (browser query tool): https://overpass-turbo.eu/
- Geofabrik Indonesia extract (if you prefer a pre-downloaded file):
  https://download.geofabrik.de/asia/indonesia.html

License: OpenStreetMap data is generally available under the Open Database License
(ODbL). See: https://www.openstreetmap.org/copyright

Notes for this project:

- Use a small Overpass query limited to the demo bounding box so the query is fast.
- For a science project, the OSM-derived land cover and settlement context is enough
  even if the extract is not perfect.

## 2. NASA FIRMS wildfire hotspots

Used for: observed fire hotspots that become labels or context for the ML model.

Source: NASA FIRMS (Fire Information for Resource Management System), MODIS and/or
VIIRS active fire data.

- FIRMS portal: https://firms.modaps.eosdis.nasa.gov/
- FIRMS API docs: https://firms.modaps.eosdis.nasa.gov/api/
- MODIS/VIIRS CSV downloads are available from the FIRMS download interface.

Note: FIRMS access may require a NASA Earthdata login for some download paths. If
you already have a CSV from FIRMS, place it in `data/raw/` and name it
`firms_hotspots.csv` (or set `FIRMS_HOTSPOTS_FILE` in `.env`).

License / terms: NASA FIRMS data has its own data use terms; check the FIRMS site
for the current terms before using it in a public project.

## 3. Peatland and hydrology context

Used for: peat risk flag, river mask, and the "peatland forest" story for
Sebangau / Kahayan.

Public options to look for:

- Wetlands International peatland data (if available for Kalimantan)
- Global peatland mapping datasets if accessible
- Hydrology/river context from OSM or public hydrography data

Because peat data availability varies by region and by access, this project does
not assume a single fixed public peat raster. If you find a usable Kalimantan peat
dataset, add it to `data/raw/` and record it here.

## 4. Wind / weather data

Used for: the CA spread direction and as a feature for the ML model.

For a 1-month high-school project, the demo uses a simplified static wind field by
default, controlled by `WIND_DIR_DEG` in `.env`.

If you want a more realistic wind source later, possible public options include:

- ERA5 reanalysis via the Copernicus Climate Data Store
- Other global or regional reanalysis products with public access

Any real wind source should be documented here with its access method, resolution,
and license.

## 5. Additional context

Optional context data you may want to look for:

- Administrative boundaries for Kalimantan (OSM or public boundary datasets)
- Roads and populated places (OSM)
- Recent land-use change context (if available)

## Data placement

After downloading, place files in:

- `data/raw/` for original downloads
- `data/processed/` for cleaned feature tables and cell grids produced by the
  pipeline

Do not commit large raw raster files unless the project needs them for the demo.
Prefer small CSVs and OSM extracts for this science-fair-scale project.
