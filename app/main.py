"""INSIGHT FULL REDO"""


from __future__ import annotations

import base64
import io
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    import pandas as pd
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except Exception:
    STREAMLIT_AVAILABLE = False

# Streamlit Community Cloud runs the ``streamlit`` executable, which puts only
# ``app/`` on sys.path. Add the repository root so ``import src`` and
# ``import app`` resolve there too, as well as under
# ``python -m streamlit run app/main.py``.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src import config
from src.bio_loader import BioLayer, load_all_bio_layers
from src.ca import CaGrid, CaParams, run_simulation, CellState
from src.fire_data import build_cell_grid, build_fire_dataset, load_firms_hotspots
from src.features import build_context_map, build_feature_table
from src.icons import icon_data_url, icon_folder
from src.land_mask import land_cell_mask
from src.ml import make_model, predict_risk_map
from src.mitigation import (
    build_mitigation_contexts,
    format_actions_for_display,
    loc_to_cell,
    cell_center_lat_lon,
    cells_within_radius,
)

from app.ca_simulator import (
    initialize_simulation,
    step_forward,
    state_distribution,
    mitigation_for,
    risk_at,
)

# ---------------------------------------------------------------------------
# Dot grid view (frame-stepped via the CA step slider).
# When you upload a custom dot later, drop the file path into DOT_IMAGE_PATH.
# ---------------------------------------------------------------------------
# Dot image path (set this to a local PNG/SVG/JPG to use a custom dot glyph).
DOT_IMAGE_PATH = None

APP_TITLE = getattr(config, "APP_TITLE", "INSIGHT Kalimantan")


def _build_simulation(wind_dir_deg: float, n_steps: int, use_hotspots: bool) -> Any:
    """Build one simulation state (plain function, wrapped in a cache below)."""
    return initialize_simulation(
        wind_dir_deg=wind_dir_deg,
        n_steps=n_steps,
        use_hotspots=use_hotspots,
        # OSM masks, the FIRMS dataset, the model and the iNaturalist points do
        # not depend on the wind, so moving the slider must not rebuild them.
        use_static_cache=True,
    )


# Initializing the demo touches the network (Overpass + iNaturalist) and can
# take minutes. Caching the built state keeps every later interaction (opening
# a sidebar expander, scrubbing the CA slider, toggling a map layer) instant;
# the "Run simulation" button clears the cache to force a fresh run.
_simulation = (
    st.cache_resource(show_spinner=False)(_build_simulation)
    if STREAMLIT_AVAILABLE
    else _build_simulation
)


# ---------------------------------------------------------------------------
# User location (demo feature)
# ---------------------------------------------------------------------------


def _user_location_input() -> Tuple[Optional[float], Optional[float]]:
    """Return (lat, lon) from the user's location control."""
    lat = st.number_input(
        "Your latitude (deg)",
        min_value=-90.0,
        max_value=90.0,
        value=None,
        format="%.4f",
        help="WGS84 latitude (e.g. -2.50 for Central Kalimantan).",
    )
    lon = st.number_input(
        "Your longitude (deg)",
        min_value=-180.0,
        max_value=180.0,
        value=None,
        format="%.4f",
        help="WGS84 longitude (e.g. 113.0 for Central Kalimantan).",
    )
    return (lat, lon)


def _user_location_popup(
    state: Any,
    user_row: int,
    user_col: int,
) -> None:
    """Render the prominent mitigation popup for the user's cell."""
    frame = state.frames[state.current_step]
    contexts = state.contexts

    center_lat, center_lon = cell_center_lat_lon(user_row, user_col)
    st.success(
        f"📍 You are near cell ({user_row}, {user_col}) "
        f"(center ~ {center_lat:.3f}, {center_lon:.3f})"
    )

    ctx = contexts.get((user_row, user_col))
    actions = mitigation_for(state, user_row, user_col)

    ca_state = frame.state_at(user_row, user_col).value
    risk = risk_at(state, user_row, user_col)

    st.markdown(
        f"**CA state:** {ca_state} · **predicted risk:** {risk:.2f} · "
        f"**wind:** {state.params.wind_dir_deg:.0f}°"
    )

    if not actions:
        st.info("No immediate mitigation guidance for this cell right now.")
        return

    top_risk = None
    if ctx is not None:
        from src.mitigation import assess_risk, RiskLevel
        top_risk = assess_risk(ctx)

    if top_risk == RiskLevel.HIGH:
        st.error("🚨 HIGH RISK — act now")
    elif top_risk == RiskLevel.MEDIUM:
        st.warning("⚠️ MEDIUM RISK — prepare now")
    elif top_risk == RiskLevel.LOW:
        st.info("ℹ️ LOW RISK — stay aware")

    st.markdown("#### Your mitigation actions")
    for a in actions:
        st.warning(f"{a['icon']} **{a['title']}** — {a['description']} ({a['timing']})")


def _nearby_summary(
    state: Any,
    user_row: int,
    user_col: int,
    radius_cells: int = 2,
) -> None:
    """Show a short list of the most urgent mitigation items in the user's area."""
    frame = state.frames[state.current_step]
    n_rows = frame.n_rows
    n_cols = frame.n_cols

    nearby = cells_within_radius(user_row, user_col, radius_cells, n_rows, n_cols)
    urgent: List[Tuple[int, int, List[Dict[str, str]]]] = []

    for (r, c) in nearby:
        actions = mitigation_for(state, r, c)
        if actions:
            urgent.append((r, c, actions))

    if not urgent:
        st.caption(
            f"No mitigation actions within {radius_cells} cells of you right now."
        )
        return

    st.markdown(f"#### Nearby cells ({len(urgent)} with guidance)")
    for (r, c), actions in urgent[:6]:
        st.markdown(f"- **cell ({r},{c})**: {', '.join(a['title'] for a in actions)}")


# ---------------------------------------------------------------------------
# Dot-grid helpers (replaces the tree-SVG view)
# ---------------------------------------------------------------------------

DOT_COLORS = {
    "healthy": "#2e7d32",
    "igniting": "#f9a825",
    "burning": "#d32f2f",
    "burned": "#6d4c41",
    "peat_risk": "#558b2f",
}

DOT_MARKS = {
    "healthy": "●",
    "igniting": "◐",
    "burning": "●",
    "burned": "○",
    "peat_risk": "◑",
}


def _dot_cell_html(row: int, col: int, state: str, dot_px: int = 10) -> str:
    title = f"({row},{col}) {state}"
    color = DOT_COLORS.get(state, "#888888")
    mark = DOT_MARKS.get(state, "?")
    inner = max(2, dot_px - 2)  # 1px border on each side makes up dot_px total
    return (
        f'<span title="{title}" style="display:inline-block;width:{inner}px;height:{inner}px;'
        f"background:{color};border:1px solid rgba(0,0,0,.25);"
        f"border-radius:50%;line-height:{dot_px}px;vertical-align:middle;text-align:center;"
        f'font-size:{max(4, inner - 2)}px;color:#000;padding:0;">{mark}</span>'
    )


def _render_dot_grid(
    frame: Any,
    params: Any,
    dot_image_path: Optional[str] = None,
) -> None:
    """Render a per-cell dot grid colored by CA state."""
    if not STREAMLIT_AVAILABLE:
        print("\nDot grid (text mode):")
        print(_dot_grid_text(frame))
        if dot_image_path is not None:
            print(f"(dot image configured: {dot_image_path})")
        return


    n_rows = frame.n_rows
    n_cols = frame.n_cols
    if n_rows <= 0 or n_cols <= 0:
        st.caption("No cells to display.")
        return

    if dot_image_path is not None and os.path.exists(dot_image_path):
        import base64
        with open(dot_image_path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        ext = os.path.splitext(dot_image_path)[1].lower()
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
        }.get(ext, "image/png")
        data_uri = f"data:{mime};base64,{b64}"

        border_colors = DOT_COLORS

        cells: List[str] = []
        for row in range(n_rows):
            row_cells: List[str] = []
            for col in range(n_cols):
                s = frame.state_at(row, col).value
                border = border_colors.get(s, "#888888")
                title = f"({row},{col}) {s}"
                row_cells.append(
                    f'<span title="{title}" style="display:inline-block;padding:1px;line-height:1">'
                    f'<img src="{data_uri}" width="10" height="10" '
                    f'style="display:block;border:1.5px solid {border};border-radius:50%;background:transparent"/>'
                    f"</span>"
                )
            cells.append("".join(row_cells))

        html = (
            "<div style='line-height:11px;font-size:11px'>"
            + "<br>".join(cells)
            + "</div>"
        )
        st.write(f"<div style='max-width:100%; overflow:auto'>{html}</div>", unsafe_allow_html=True)
        return


    # One image instead of 3,364 inline-styled spans: the old markup was ~700 KB
    # per rerun for a thumbnail inside a collapsed expander.
    dot_px = max(4, min(10, 500 // max(1, n_cols)))
    st.markdown(
        f"<img alt='Fire spread grid' style='width:100%;max-width:{n_cols * dot_px}px;"
        "image-rendering:pixelated;display:block' "
        f"src='{_dot_grid_uri(frame, dot_px=dot_px)}'/>",
        unsafe_allow_html=True,
    )


def _dot_grid_uri(frame: Any, dot_px: int = 10) -> str:
    """Paint the CA frame into a PNG data URI, one pixel per cell."""
    import numpy as np
    from PIL import Image

    palette = {name: (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)) for name, c in DOT_COLORS.items()}
    fallback = (136, 136, 136)
    n_rows, n_cols = frame.n_rows, frame.n_cols
    pixels = np.zeros((n_rows, n_cols, 4), dtype="uint8")
    for row in range(n_rows):
        for col in range(n_cols):
            state = frame.state_at(row, col).value
            pixels[row, col, :3] = palette.get(state, fallback)
            pixels[row, col, 3] = 255

    image = Image.fromarray(pixels, mode="RGBA")
    if dot_px > 1:
        image = image.resize((n_cols * dot_px, n_rows * dot_px), Image.NEAREST)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _dot_grid_text(frame: Any) -> str:
    """Text fallback for the dot grid when Streamlit is unavailable."""
    marker = {
        "healthy": ".",
        "igniting": "i",
        "burning": "@",
        "burned": "x",
        "peat_risk": "p",
    }
    out: List[str] = []
    for row in range(frame.n_rows):
        line: List[str] = []
        for col in range(frame.n_cols):
            s = frame.state_at(row, col).value
            line.append(marker.get(s, "?"))
        out.append("".join(line))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# In-arena CA sidebar (top-right panel)
# ---------------------------------------------------------------------------


def _render_ca_sidebar(state: Any, frame: Any, params: Any, step_idx: int) -> None:
    """Render the top-right in-arena sidebar with live CA data."""
    if not STREAMLIT_AVAILABLE:
        return

    title_txt = "CA state distribution"
    with st.container():
        st.markdown("**Live CA state**")
        st.caption(
            "Live per-step counts for the current simulation frame. "
            "Use the CA step slider below to scrub through time."
        )

        dist = state_distribution(frame)
        st.subheader("Cells by state")
        for label in [
            "healthy",
            "igniting",
            "burning",
            "burned",
            "peat_risk",
        ]:
            count = dist.get(label, 0)
            color = DOT_COLORS.get(label, "#888888")
            st.markdown(
                f'<span style="display:inline-block;width:10px;height:10px;'
                f"background:{color};border:1px solid rgba(0,0,0,.25);"
                f'border-radius:50%;line-height:1;vertical-align:middle;margin-right:6px;"></span>'
                f"**{label}**: {count}",
                unsafe_allow_html=True,
            )

        st.subheader("Simulation metadata")
        st.write(f"**Wind direction:** {params.wind_dir_deg:.0f}°")
        st.write(f"**CA spread base:** {params.spread_base:.2f}")
        st.write(f"**Wind alignment:** {params.wind_alignment_strength:.2f}")
        st.write(f"**Peat influence:** {params.peat_influence:.2f}")
        st.write(f"**Current step:** {step_idx} / {len(state.frames) - 1}")
        st.write(f"**Grid:** {frame.n_rows} rows × {frame.n_cols} cols")

        if state.risk_map is not None:
            st.subheader("Risk summary")
            rm = state.risk_map
            st.write(f"**Max predicted risk:** {float(rm.max()):.2f}")
            st.write(f"**Cells > 0.2 risk:** {int((rm > 0.2).sum())}")
            st.write(f"**Cells > 0.5 risk:** {int((rm > 0.5).sum())}")
            source = getattr(state, "risk_source", "heuristic baseline")
            st.write(f"**Risk source:** {source}")
            metrics = getattr(state, "risk_metrics", None) or {}
            if metrics.get("roc_auc") is not None:
                st.caption(
                    f"Test ROC-AUC {metrics['roc_auc']:.3f} · "
                    f"PR-AUC {metrics.get('average_precision', float('nan')):.3f}"
                )
        else:
            st.subheader("Risk summary")
            st.write("Risk map not computed.")

        st.subheader("Biodiversity layer (iNaturalist)")
        st.caption(
            "Kalimantan flora/fauna distribution from iNaturalist observations "
            "(offline stub first, then live API)."
        )
        for key in state.bio_layers:
            layer = state.bio_layers[key]
            st.markdown(
                f"**{layer.query}** — {layer.n} obs "
                f"(sample {layer.sample(3)[:2]})"
            )


# ---------------------------------------------------------------------------
# Risk map (folium with Indonesia zoom cap)
# ---------------------------------------------------------------------------

# Regional pan cap shared by every map (folium max_bounds). Every map uses
# OpenStreetMap tiles, and this envelope is wide enough that OSM covers the
# full view everywhere inside the cap.
# The north edge is 7.5 N (not 6 N) so the whole Kalimantan bbox (up to
# 7.3 N) and every flora/fauna observation stay reachable — the old 6 N cap
# cut off northern Kalimantan.
# Folium max_bounds wants [[south_lat, west_lon], [north_lat, east_lon]].
INDONESIA_BOUNDS = (
    (-11.0, 94.0),
    (7.5, 142.0),
)


def _convex_hull_latlon(points: Any) -> Any:
    """Return a convex hull polygon for a list of (lat, lon) points.

    Uses a small Andrew's monotone chain implementation so we do not depend on
    scipy. Returns a list of [lat, lon] vertices, or None if not enough points.
    """
    pts = sorted({(lon, lat) for (lat, lon) in points})  # sort by lon, then lat
    if len(pts) < 3:
        return None

    def cross(o: Any, a: Any, b: Any) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: Any = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: Any = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        return None
    return [[lat, lon] for (lon, lat) in hull]


# ---------------------------------------------------------------------------
# Risk layers
# ---------------------------------------------------------------------------
# The model returns a 58 x 58 grid: 3,364 cells. Drawing one Leaflet marker per
# cell meant ~1.6 MB of map HTML and ~4 s of server time for every render, for a
# surface the eye reads as one shaded field. Windy paints its layers as a single
# raster, so INSIGHT does the same: the grid becomes a small PNG that Leaflet
# stretches over the box.

# (normalised value, RGB, alpha) — green through amber to dark red.
RISK_RAMP: Tuple[Tuple[float, Tuple[int, int, int], float], ...] = (
    (0.00, (30, 132, 84), 0.00),
    (0.05, (30, 132, 84), 0.16),
    (0.20, (250, 204, 21), 0.36),
    (0.35, (249, 115, 22), 0.54),
    (0.50, (220, 38, 38), 0.70),
    (0.80, (127, 29, 29), 0.82),
)
RISK_FLOOR = 0.01


def _risk_field_uri(
    risk: Any,
    mask: Any = None,
    vmin: float = 0.0,
    vmax: float = 0.8,
    scale: int = 4,
) -> str:
    """Paint a risk grid into a PNG data URI (one raster layer, not N markers)."""
    import numpy as np
    from PIL import Image

    grid = np.asarray(risk, dtype=np.float64)
    if grid.ndim != 2 or grid.size == 0:
        raise ValueError("risk grid must be a non-empty 2-D array")

    span = max(float(vmax) - float(vmin), 1e-6)
    norm = np.clip((grid - float(vmin)) / span, 0.0, 1.0)

    values = np.array([stop[0] for stop in RISK_RAMP], dtype=np.float64)
    reds = np.array([stop[1][0] for stop in RISK_RAMP], dtype=np.float64)
    greens = np.array([stop[1][1] for stop in RISK_RAMP], dtype=np.float64)
    blues = np.array([stop[1][2] for stop in RISK_RAMP], dtype=np.float64)
    alphas = np.array([stop[2] for stop in RISK_RAMP], dtype=np.float64)

    rgb = np.stack(
        [np.interp(norm, values, channel) for channel in (reds, greens, blues)], axis=-1
    )
    alpha = np.interp(norm, values, alphas)
    floor = (RISK_FLOOR - float(vmin)) / span
    alpha = np.where(norm > floor, alpha, 0.0)
    if mask is not None:
        alpha = alpha * np.asarray(mask, dtype=np.float64)

    rgba = np.dstack([rgb, np.clip(alpha, 0.0, 1.0) * 255.0])
    image = Image.fromarray(np.round(rgba).astype("uint8"), mode="RGBA")
    if scale > 1:
        # Smooth the cells into a field the way a raster weather layer looks;
        # the browser then stretches the result over the bounding box.
        image = image.resize((grid.shape[1] * scale, grid.shape[0] * scale), Image.BILINEAR)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


# Rendering is pure and cheap (~10 ms), but Streamlit reruns the whole script on
# every widget change; the cache keeps a slider drag from re-encoding the PNG.
_risk_field_uri_cached = (
    st.cache_data(show_spinner=False, max_entries=24)(_risk_field_uri)
    if STREAMLIT_AVAILABLE
    else _risk_field_uri
)


def _risk_legend_html() -> str:
    """Small in-map legend for the risk raster (Windy keeps one on the map)."""
    stops = ", ".join(
        f"rgba({r}, {g}, {b}, {max(a, 0.15):.2f}) {v * 100:.0f}%"
        for (v, (r, g, b), a) in RISK_RAMP
    )
    return (
        "<div class='insight-legend'>"
        "<span>Fire risk</span>"
        f"<i style='background:linear-gradient(90deg, {stops})'></i>"
        "<em>0</em><em>80%</em>"
        "</div>"
        "<style>"
        ".insight-legend{position:fixed;left:16px;bottom:22px;z-index:900;"
        "display:flex;align-items:center;gap:8px;padding:6px 12px;border-radius:10px;"
        "background:rgba(8,13,18,.8);color:#e6eef6;font:500 11px/1.2 system-ui,sans-serif;"
        "backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.12)}"
        ".insight-legend i{width:120px;height:8px;border-radius:4px;display:block}"
        ".insight-legend em{font-style:normal;color:#9fb2c4;font-size:10px}"
        "</style>"
    )


# ---------------------------------------------------------------------------
# Flora & fauna points
# ---------------------------------------------------------------------------
# A Folium marker per observation cost ~2 KB each (the icon is inlined into
# every one) and ~5 ms of Python each: ~1,350 observations made a 2.8 MB map and
# ran for seconds. One GeoJSON collection per taxon carries the same points in
# ~100 bytes each, and Leaflet draws them as circles.

def _bio_feature_collection(layer: Any) -> Dict[str, Any]:
    """Wrap one taxon's observations as GeoJSON points."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(float(lon), 4), round(float(lat), 4)],
                },
                "properties": {
                    "taxon": layer.query,
                    "lat": round(float(lat), 4),
                    "lon": round(float(lon), 4),
                },
            }
            for (lat, lon) in layer.points
        ],
    }


def _add_bio_points(
    m: Any,
    bio_layers: Any,
    colors: Optional[Dict[str, str]] = None,
) -> None:
    """Add every flora/fauna observation as one compact GeoJSON layer."""
    import folium

    colors = colors or {}
    for key, layer in bio_layers.items():
        if not layer.points:
            continue
        color = colors.get(key, "#888888")
        folium.GeoJson(
            _bio_feature_collection(layer),
            name=layer.query,
            marker=folium.CircleMarker(
                radius=5,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                color="#0b0f14",
                weight=0.6,
            ),
            popup=folium.GeoJsonPopup(fields=["taxon", "lat", "lon"], labels=True),
            tooltip=folium.GeoJsonTooltip(fields=["taxon"]),
        ).add_to(m)


def _bio_legend_html(
    bio_layers: Any,
    colors: Optional[Dict[str, str]] = None,
    bottom: int = 22,
) -> str:
    """Legend with one icon per taxon (the icons live here, not per marker)."""
    colors = colors or {}
    rows: List[str] = []
    for key, layer in bio_layers.items():
        icon = icon_data_url(key)
        swatch = (
            f"<img src='{icon}' alt='' width='18' height='18'/>"
            if icon
            else (
                "<i style='display:inline-block;width:10px;height:10px;border-radius:50%;"
                f"background:{colors.get(key, '#888888')}'></i>"
            )
        )
        rows.append(
            "<div class='insight-bio-row'>"
            f"{swatch}<span>{layer.query}</span><em>{layer.n}</em></div>"
        )
    if not rows:
        return ""
    return (
        f"<div class='insight-bio-legend' style='bottom:{int(bottom)}px'>"
        "<b>Flora &amp; fauna</b>"
        + "".join(rows)
        + "</div>"
        "<style>"
        ".insight-bio-legend{position:fixed;left:16px;z-index:900;min-width:168px;"
        "padding:7px 11px;border-radius:10px;background:rgba(8,13,18,.82);color:#e6eef6;"
        "font:500 11px/1.35 system-ui,sans-serif;backdrop-filter:blur(10px);"
        "border:1px solid rgba(255,255,255,.12)}"
        ".insight-bio-legend b{display:block;font-size:10px;letter-spacing:.06em;"
        "text-transform:uppercase;color:#9fb2c4;margin-bottom:4px}"
        ".insight-bio-row{display:flex;align-items:center;gap:7px;padding:1px 0}"
        ".insight-bio-row span{flex:1;white-space:nowrap}"
        ".insight-bio-row em{font-style:normal;color:#9fb2c4}"
        "</style>"
    )


def _new_osm_map(
    location: List[float],
    zoom_start: int,
    max_bounds: Any = None,
    full_height: bool = False,
) -> Any:
    """Create a Folium map whose only basemap is OpenStreetMap.

    One explicit tile layer (instead of Folium's implicit CartoDB default)
    guarantees OSM paints the entire map on every map in the app, with retina
    tiles when the browser supports them.
    """
    import folium

    m = folium.Map(
        location=location,
        zoom_start=zoom_start,
        max_bounds=max_bounds,
        control_scale=True,
        prefer_canvas=True,
        tiles=None,
        # Windy has no zoom buttons: the top-left corner belongs to the
        # floating control panel. Scroll/pinch zoom still works.
        zoom_control=False,
    )
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="OpenStreetMap",
        attr=(
            '&copy; <a href="https://www.openstreetmap.org/copyright">'
            "OpenStreetMap</a> contributors"
        ),
        detect_retina=True,
        max_zoom=19,
        max_native_zoom=19,
        overlay=False,
        control=True,
    ).add_to(m)

    if full_height:
        # The shell stretches the iframe to the viewport; let the map itself
        # fill that iframe instead of keeping Leaflet's inline pixel height.
        # This is a separate document, so it needs its own mobile baseline:
        # dvh so the map tracks the phone's URL bar, and no tap flash or
        # pull-to-refresh over the tiles.
        m.get_root().header.add_child(
            folium.Element(
                "<style>html, body { height: 100vh; height: 100dvh; "
                "margin: 0; overscroll-behavior: none; "
                "-webkit-tap-highlight-color: transparent; "
                "-webkit-text-size-adjust: 100%; } "
                ".folium-map, .leaflet-container { height: 100vh !important; "
                "height: 100dvh !important; width: 100% !important; } "
                ".leaflet-bottom.leaflet-right { left: 0; right: auto; } "
                "</style>"
            )
        )
        # Re-measure once the iframe has its final size (Leaflet listens for
        # the resize event and calls invalidateSize).
        folium.Element(
            "<script>setTimeout(function(){"
            "window.dispatchEvent(new Event('resize'));"
            "}, 700);</script>"
        ).add_to(m.get_root().html)
    return m


def _render_kalimantan_risk_map(
    kal_risk: Any,
    kal_bbox: Any,
    bio_layers: Any = None,
) -> None:
    """Render a Kalimantan-wide coarse risk map with an optional bio overlay."""
    try:
        import folium
        from streamlit_folium import st_folium
    except Exception as exc:
        st.warning(f"Kalimantan risk map could not render via folium: {exc}.")
        return

    min_lon, min_lat, max_lon, max_lat = kal_bbox
    n_rows, n_cols = kal_risk.shape
    center_lat = (min_lat + max_lat) / 2.0
    center_lon = (min_lon + max_lon) / 2.0
    (south_lat, west_lon), (north_lat, east_lon) = INDONESIA_BOUNDS

    m = _new_osm_map(
        [center_lat, center_lon],
        6,
        max_bounds=[[south_lat, west_lon], [north_lat, east_lon]],
    )

    # --- Kalimantan-wide fire-risk field ---
    # Only cells whose centre falls on land are painted: the rectangle also
    # covers the Java Sea, the Karimata Strait and the South China Sea, where a
    # "risk" value would be meaningless visual noise.
    on_land = land_cell_mask(
        (min_lon, min_lat, max_lon, max_lat), n_rows, n_cols,
    )
    folium.raster_layers.ImageOverlay(
        image=_risk_field_uri_cached(
            kal_risk, on_land, vmin=0.20, vmax=0.55
        ),
        bounds=[[min_lat, min_lon], [max_lat, max_lon]],
        opacity=0.85,
        name="Fire risk — Kalimantan (ML heuristic)",
        alt="Kalimantan-wide fire-risk field (physics baseline)",
    ).add_to(m)

    # --- Flora & fauna overlay: TRIANGLES, Kalimantan-only, distinct palette ---
    if bio_layers is not None:
        bio_colors = {
            "Orangutan": "#7b3ff2",        # violet
            "Proboscis_monkey": "#00c2d1",  # cyan
            "Rafflesia": "#e91ec4",        # magenta
            "Nepenthes": "#b5e61d",        # lime
        }
        bio_group = folium.FeatureGroup(name="Flora & fauna — Kalimantan only", show=True)
        for key, layer in bio_layers.items():
            color = bio_colors.get(key, "#555555")
            pts = [(lat, lon) for (lat, lon) in layer.points]
            if not pts:
                continue
            # Subsample long point lists so the map stays fast.
            if len(pts) > 250:
                stride = len(pts) // 250 + 1
                pts = pts[::stride]
            hull = _convex_hull_latlon(pts)
            if hull and len(hull) >= 3:
                folium.Polygon(
                    locations=hull,
                    color=color,
                    weight=2,
                    dash_pattern="6, 4",
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.10,
                    popup=f"{layer.query} — distribution area ({layer.n} obs, Kalimantan only)",
                ).add_to(bio_group)
        bio_group.add_to(m)
        _add_bio_points(m, bio_layers, colors=bio_colors)
        m.get_root().html.add_child(
            folium.Element(_bio_legend_html(bio_layers, bio_colors))
        )

    folium.LayerControl(collapsed=False, position="bottomright").add_to(m)
    st_folium(m, use_container_width=True, height=700)


def _render_risk_map_folium(
    risk: Any,
    bbox: Tuple[float, float, float, float],
    bio_layers: Any = None,
) -> None:
    """Render the ML risk map as a folium map with an Indonesia zoom cap."""
    min_lon, min_lat, max_lon, max_lat = bbox
    try:
        import folium
        from streamlit_folium import st_folium
    except Exception as exc:
        st.warning(
            f"Risk map could not render via folium: {exc}. Falling back to st.map."
        )
        d = config.grid_spacing_deg()
        n_rows, n_cols = risk.shape
        st.map(
            pd.DataFrame(
                {
                    "lat": [max_lat - (row + 0.5) * d for row in range(n_rows) for _ in range(n_cols)],
                    "lon": [min_lon + (col + 0.5) * d for _ in range(n_rows) for col in range(n_cols)],
                }
            )
        )
        return

    (south_lat, west_lon), (north_lat, east_lon) = INDONESIA_BOUNDS
    center_lat = (min_lat + max_lat) / 2.0
    center_lon = (min_lon + max_lon) / 2.0

    # OpenStreetMap everywhere: the default Folium basemap is CartoDB, which
    # would leave this map on a different tile set than the others.
    m = _new_osm_map(
        [center_lat, center_lon],
        7,
        max_bounds=[[south_lat, west_lon], [north_lat, east_lon]],
        full_height=True,
    )
    # Windy-style hero: frame the demo box so the model's cells fill the map
    # instead of floating in a Borneo-wide view. Padding keeps the box clear of
    # the floating panels on wide screens.
    m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]], padding=(30, 30))

    # One raster instead of 3,364 markers: same surface, ~10 KB of map HTML.
    folium.raster_layers.ImageOverlay(
        image=_risk_field_uri_cached(risk, None, vmin=0.0, vmax=0.8),
        bounds=[[min_lat, min_lon], [max_lat, max_lon]],
        opacity=0.9,
        name="Fire risk (ML)",
        alt="Predicted fire risk per cell",
    ).add_to(m)
    m.get_root().html.add_child(folium.Element(_risk_legend_html()))

    # Optional combined view: overlay flora/fauna areas on the same map.
    if bio_layers is not None:
        bio_colors = {
            "Orangutan": "#1f77b4",
            "Proboscis_monkey": "#ff7f0e",
            "Rafflesia": "#2ca02c",
            "Nepenthes": "#d62728",
        }
        bio_group = folium.FeatureGroup(name="Flora & fauna areas", show=True)
        for key, layer in bio_layers.items():
            color = bio_colors.get(key, "#888888")
            pts = [(lat, lon) for (lat, lon) in layer.points]
            if len(pts) == 0:
                continue
            # Convex-hull style area: use a buffered hull approximation.
            # Folium has no hull primitive, so draw the hull polygon when the
            # scipy-free hull helper provides one, otherwise draw a semi-transparent
            # circle per observation cluster.
            hull = _convex_hull_latlon(pts)
            if hull and len(hull) >= 3:
                folium.Polygon(
                    locations=hull,
                    color=color,
                    weight=2,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.15,
                    popup=f"{layer.query} — distribution area ({layer.n} obs)",
                ).add_to(bio_group)
        bio_group.add_to(m)
        _add_bio_points(m, bio_layers, colors=bio_colors)
        # Above the risk legend so the two do not overlap.
        m.get_root().html.add_child(
            folium.Element(_bio_legend_html(bio_layers, bio_colors, bottom=66))
        )

    # No Leaflet layer control here: the floating side panels would cover it,
    # and the flora/fauna overlay is toggled from the control panel instead.
    st_folium(m, use_container_width=True, height=640)


# ---------------------------------------------------------------------------
# Biodiversity (iNaturalist) map layer in Kalimantan
# ---------------------------------------------------------------------------


def _render_bio_map(state: Any) -> None:
    """Render a second map layer showing Kalimantan flora/fauna distribution."""
    if not STREAMLIT_AVAILABLE:
        print("\nBiodiversity layer (text mode):")
        for key, layer in state.bio_layers.items():
            print(f"{key}: {layer.n} obs, sample {layer.sample(3)}")
        return

    try:
        import folium
        from streamlit_folium import st_folium
    except Exception as exc:
        st.warning(
            f"Biodiversity map could not render via folium: {exc}. "
            "Showing observation counts instead."
        )
        for key, layer in state.bio_layers.items():
            st.markdown(f"**{layer.query}** — {layer.n} observations")
        return

    min_lon, min_lat, max_lon, max_lat = config.bounding_box()
    center_lat = (min_lat + max_lat) / 2.0
    center_lon = (min_lon + max_lon) / 2.0

    bio_colors = {
        "Orangutan": "#1f77b4",
        "Proboscis_monkey": "#ff7f0e",
        "Rafflesia": "#2ca02c",
        "Nepenthes": "#d62728",
    }

    (south_lat, west_lon), (north_lat, east_lon) = INDONESIA_BOUNDS
    m = _new_osm_map(
        [center_lat, center_lon],
        8,
        max_bounds=[[south_lat, west_lon], [north_lat, east_lon]],
    )

    _add_bio_points(m, state.bio_layers, colors=bio_colors)
    m.get_root().html.add_child(
        folium.Element(_bio_legend_html(state.bio_layers, bio_colors))
    )

    st_folium(m, use_container_width=True, height=520)


# ---------------------------------------------------------------------------
# App title + bounding box info
# ---------------------------------------------------------------------------


def write_app_title() -> None:
    title = APP_TITLE or "INSIGHT Kalimantan"
    if STREAMLIT_AVAILABLE:
        st.title(title)
    else:
        print(f"\n{title}\n")


def show_bounding_box_info() -> None:
    bbox = config.bounding_box()
    info = {
        "Bounding box": f"{bbox[0]:.2f}, {bbox[1]:.2f} → {bbox[2]:.2f}, {bbox[3]:.2f}",
        "Approx size": "2° lon × 2° lat (demo)",
        "Grid": f"{config.grid_spacing_deg():.3f}° per cell",
        "Wind dir": f"{config.default_wind_direction_deg():.0f}°",
        "CA spread base": f"{config.CA_SPREAD_BASE:.2f}",
    }
    if STREAMLIT_AVAILABLE:
        st.info(
            "\n".join(f"- **{k}**: {v}" for k, v in info.items())
        )
    else:
        print("\n".join(f"- {k}: {v}" for k, v in info.items()))


# ---------------------------------------------------------------------------
# Layout: maps on the left, optional second sidebar on the right
# ---------------------------------------------------------------------------

# How many mitigation entries the right sidebar renders (highest risk first).
# There can be ~1000 context cells, which made the old in-page list enormous.
EMERGENCY_TILE_LIMIT = 30

def _inject_layout_css(panel_open: bool = True) -> None:
    """Windy-style shell: a full-bleed map with floating glass panels."""
    if not STREAMLIT_AVAILABLE:
        return
    from app._windy_style import inject_layout_css

    inject_layout_css(panel_open=panel_open)


# ---------------------------------------------------------------------------
# Main Streamlit view
# ---------------------------------------------------------------------------


def run_streamlit() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🔥",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Folding the controls panel is pure CSS (the bookmark tab toggles a hidden
    # checkbox), so it needs no session state and no rerun. The emergency panel
    # is still switched by its toggle in the controls panel.
    _inject_layout_css(panel_open=True)

    # Windy-style left panel: every control floats over the map instead of
    # taking layout space, so the map itself is the page.
    controls = st.container(key="windy_controls")
    with controls:
        st.markdown(
            "<div class='windy-brand'><b>INSIGHT</b>"
            "<span>Kalimantan fire &amp; habitat monitor</span></div>",
            unsafe_allow_html=True,
        )
        wind_dir = st.slider(
            "Wind direction (deg)",
            min_value=0,
            max_value=360,
            value=int(config.default_wind_direction_deg()),
            step=5,
            help="Meteorological convention: 0 = wind FROM north.",
        )
        use_hotspots = st.checkbox("Seed from FIRMS hotspots", value=True)
        n_steps = st.slider("CA steps", min_value=1, max_value=20, value=12, step=1)
        run_button = st.button("Run simulation", use_container_width=True)
        show_emergency_panel = st.toggle(
            "Emergency panel",
            value=True,
            help=(
                "Show your location, nearby hotspots and mitigation guidance in "
                "the floating panel on the right."
            ),
            key="show_emergency_panel",
        )
        show_bio_overlay = st.checkbox(
            "Flora & fauna layer on the map",
            value=False,
            help=(
                "Adds the iNaturalist observations as dots (one colour per taxon, "
                "Kalimantan only) plus a legend with the icons from assets/icons/. "
                "Each dot opens the taxon and its coordinates."
            ),
            key="show_bio_overlay",
        )
        with st.expander("Area, data & icons"):
            show_bounding_box_info()
            st.caption(
                "Marker images live in the folder below; keep the taxon name in the "
                "filename (PNG, WEBP, JPG or SVG) and rerun the app. Sources: "
                "OpenStreetMap, NASA FIRMS, iNaturalist, Natural Earth."
            )
            st.code(str(icon_folder()))

    # Windy-style time scrubber, pinned along the bottom edge.
    timeline = st.container(key="windy_timeline")

    if run_button and STREAMLIT_AVAILABLE:
        _simulation.clear()

    state: Optional[Any] = None
    with st.spinner("Initializing simulation..."):
        try:
            state = _simulation(float(wind_dir), int(n_steps), bool(use_hotspots))
        except Exception as exc:
            st.error(f"Simulation initialization failed: {exc}")
            state = None

    if state is None:
        st.warning("Could not initialize the simulation. Check data files and try again.")
        return

    with timeline:
        step_idx = st.slider(
            "CA step",
            min_value=0,
            max_value=len(state.frames) - 1,
            value=state.current_step,
            step=1,
            key="ca_step_slider",
            label_visibility="collapsed",
        )
        step_col, play_col = st.columns([3, 1])
        with step_col:
            st.caption(
                f"Step {step_idx} / {len(state.frames) - 1} · "
                f"wind {state.params.wind_dir_deg:.0f}°"
            )
        with play_col:
            auto_play = st.checkbox("Auto-play", value=False, key="auto_play")

    if auto_play:
        step_idx = int(min(len(state.frames) - 1, step_idx + 1))

    current_frame = state.frames[step_idx]

    # Panel content that needs the simulation state.
    with controls:
        _render_risk_provenance(state)
        with st.expander("CA dashboard"):
            _render_ca_sidebar(state, current_frame, state.params, step_idx)
        with st.expander("Fire spread grid"):
            st.caption("Each cell is a small dot coloured by its CA state.")
            _render_dot_grid(current_frame, state.params, dot_image_path=DOT_IMAGE_PATH)

    # The map renders before the emergency panel: on wide screens both panels
    # float, so order is irrelevant, but on phones the emergency panel drops
    # into the flow and would otherwise push the map a few thousand pixels
    # down the page. Map first, mitigation list under it, layers last.
    _render_map(state, show_bio_overlay=show_bio_overlay)

    # Emergency content floats on the right; when switched off it is not
    # rendered at all, so nothing frames the map.
    if show_emergency_panel:
        with st.container(key="emergency_panel"):
            _render_emergency_panel(state)

    _render_layers(state, show_bio_overlay=show_bio_overlay)

# ---------------------------------------------------------------------------
# Map area (left column): biodiversity + Kalimantan-wide risk map
# ---------------------------------------------------------------------------


def _render_risk_provenance(state: Any) -> None:
    """One caption line saying exactly what produced the risk surface."""
    source = getattr(state, "risk_source", "heuristic baseline")
    if source != "random forest":
        st.caption(f"Risk surface source: {source}.")
        return

    metrics = getattr(state, "risk_metrics", None) or {}
    bits = ["Random Forest"]
    if metrics.get("roc_auc") is not None:
        bits.append(f"ROC-AUC {metrics['roc_auc']:.3f}")
    if metrics.get("average_precision") is not None:
        bits.append(f"PR-AUC {metrics['average_precision']:.3f}")
    if getattr(state, "risk_conditioned_on", None):
        bits.append(f"hotspots through {state.risk_conditioned_on}")
    st.caption(" · ".join(bits))


def _render_map(state: Any, show_bio_overlay: bool = True) -> None:
    """The full-bleed risk map: the page itself on every screen size."""
    if state.risk_map is not None:
        with st.container(key="windy_map"):
            if float(state.risk_map.max()) <= 0.0:
                st.warning("Risk map is currently empty; try running the simulation.")
            else:
                _render_risk_map_folium(
                    state.risk_map,
                    config.bounding_box(),
                    bio_layers=(state.bio_layers if (show_bio_overlay and getattr(state, "bio_layers", None)) else None),
                )
    else:
        st.warning("Risk map unavailable.")


def _render_layers(state: Any, show_bio_overlay: bool = True) -> None:
    """Secondary layers (biodiversity, island overview) below the map."""
    with st.container(key="windy_layers"):
        st.markdown("#### Layers")
        with st.expander("Biodiversity distribution (Kalimantan flora/fauna)", expanded=True):
            st.caption(
                "iNaturalist observations filtered to Kalimantan only. "
                "Taxa shown: Bornean Orangutan, Proboscis monkey, Rafflesia, Nepenthes. "
                "Live API if available; offline stub otherwise."
            )
            _render_bio_map(state)

        # Island-wide overview: coarse physics surface, not the trained model.
        if getattr(state, "kalimantan_risk", None) is not None:
            with st.expander(
                "Kalimantan-wide overview (physics baseline, not the trained model)"
            ):
                bio = (
                    state.bio_layers
                    if (show_bio_overlay and getattr(state, "bio_layers", None))
                    else None
                )
                _render_kalimantan_risk_map(
                    state.kalimantan_risk,
                    state.kalimantan_bbox,
                    bio_layers=bio,
                )
                st.caption(
                    "Shaded field = coarse wind/peat heuristic over the whole of "
                    "Kalimantan (~16 km cells), drawn on land cells only. "
                    "The Random Forest above covers only "
                    "the 2° demo box, where its OSM and FIRMS features exist. "
                    "Dots = iNaturalist flora/fauna, Kalimantan only; the legend "
                    f"uses the icon images from {icon_folder()}."
                )

        st.caption("This is a science-fair prototype, not an emergency response system.")

def _render_emergency_panel(state: Any) -> None:
    """Right-hand emergency panel: location, nearby risk, mitigation tiles."""
    st.markdown("### 🚨 Emergency & mitigation")
    st.caption(
        f"Live guidance for CA step {state.current_step}. "
        "Prototype only — not an emergency response system."
    )

    st.markdown("#### Your location")
    st.caption(
        "Type a lat/lon near Central Kalimantan to simulate the per-user "
        "notification. Real GPS is out of scope for this web app."
    )

    lat, lon = _user_location_input()

    user_row: Optional[int] = None
    user_col: Optional[int] = None

    if lat is not None and lon is not None:
        try:
            user_row, user_col = loc_to_cell(lat, lon)
        except ValueError as exc:
            st.warning(str(exc))
            user_row = None
            user_col = None

    if user_row is not None and user_col is not None:
        _user_location_popup(state, user_row, user_col)
        _nearby_summary(state, user_row, user_col, radius_cells=2)

    st.markdown("#### Mitigation guidance")
    cells: List[Tuple[float, int, int, Any, List[Dict[str, str]]]] = []
    for (row, col), ctx in state.contexts.items():
        actions = mitigation_for(state, row, col)
        if actions:
            cells.append((float(ctx.predicted_risk), row, col, ctx, actions))

    if not cells:
        st.info("No settlement or rural cells are currently near the fire.")
    else:
        # Highest predicted risk first: the panel stays useful instead of
        # rendering hundreds of near-identical tiles in arbitrary order.
        cells.sort(key=lambda item: item[0], reverse=True)
        for _risk, row, col, ctx, actions in cells[:EMERGENCY_TILE_LIMIT]:
            title = "Settlement" if ctx.is_settlement else "Rural area"
            # One compact row per cell instead of a stack of alert cards, so
            # the sidebar stays readable.
            with st.expander(
                f"{title} · cell ({row}, {col}) · risk {ctx.predicted_risk:.2f}",
                expanded=False,
            ):
                st.caption(
                    f"CA state: {ctx.ca_state} · predicted risk: "
                    f"{ctx.predicted_risk:.2f} · wind: {ctx.wind_dir_deg:.0f}°"
                )
                for a in actions:
                    st.markdown(
                        f"{a['icon']} **{a['title']}** — {a['description']} "
                        f"*({a['timing']})*"
                    )
        if len(cells) > EMERGENCY_TILE_LIMIT:
            st.caption(
                f"Showing the {EMERGENCY_TILE_LIMIT} highest-risk cells of {len(cells)}. "
                "Raise EMERGENCY_TILE_LIMIT in app/main.py to show more."
            )

    with st.expander("Show CA explanation"):
        from src.ca import step_explanation
        st.write(step_explanation(state.params))


def fallback_run() -> None:
    """Run a minimal non-Streamlit summary of the project."""
    print("\n⚠️ Streamlit is not installed. Running a minimal console summary.\n")
    write_app_title()
    show_bounding_box_info()

    try:
        state = initialize_simulation(
            wind_dir_deg=config.default_wind_direction_deg(),
            n_steps=6,
            use_hotspots=False,
        )
        for i, frame in enumerate(state.frames):
            print(f"Step {i}: {state_distribution(frame)}")
        print("\nMitigation contexts:", len(state.contexts))
        for (row, col), ctx in list(state.contexts.items())[:5]:
            print(f"  cell ({row},{col}): risk={ctx.predicted_risk:.2f}, state={ctx.ca_state}")
    except Exception as exc:
        print(f"Console run failed: {exc}")


def main(argv: Optional[List[str]] = None) -> None:
    if STREAMLIT_AVAILABLE:
        run_streamlit()
    else:
        fallback_run()


if __name__ == "__main__":
    main(sys.argv[1:])
