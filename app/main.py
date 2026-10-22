"""INSIGHT FULL REDO"""


from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    import pandas as pd
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except Exception:
    STREAMLIT_AVAILABLE = False

from src import config
from src.bio_loader import BioLayer, load_all_bio_layers
from src.ca import CaGrid, CaParams, run_simulation, CellState
from src.fire_data import build_cell_grid, build_fire_dataset, load_firms_hotspots
from src.features import build_context_map, build_feature_table
from src.icons import bio_icon, icon_folder
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


    cells: List[str] = []
    # Scale dots so the full grid (n_cols dots across) fits the widened
    # sidebar (~500px of usable width) without horizontal scrolling.
    dot_px = max(4, min(10, 500 // max(1, n_cols)))
    for row in range(n_rows):
        row_cells: List[str] = []
        for col in range(n_cols):
            s = frame.state_at(row, col).value
            row_cells.append(_dot_cell_html(row, col, s, dot_px=dot_px))
        cells.append("".join(row_cells))

    html = (
        f"<div style='line-height:{dot_px}px;font-size:{dot_px}px'>"
        + "<br>".join(cells)
        + "</div>"
    )
    st.write(f"<div style='max-width:100%; overflow:auto'>{html}</div>", unsafe_allow_html=True)


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
    with st.sidebar:
        st.title("🔥 CA Dashboard")
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


def _new_osm_map(location: List[float], zoom_start: int, max_bounds: Any = None) -> Any:
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
    d_lat = (max_lat - min_lat) / n_rows
    d_lon = (max_lon - min_lon) / n_cols
    center_lat = (min_lat + max_lat) / 2.0
    center_lon = (min_lon + max_lon) / 2.0
    (south_lat, west_lon), (north_lat, east_lon) = INDONESIA_BOUNDS

    m = _new_osm_map(
        [center_lat, center_lon],
        6,
        max_bounds=[[south_lat, west_lon], [north_lat, east_lon]],
    )

    # --- Kalimantan-wide fire-risk dots (circles) ---
    # Only cells whose centre falls on land get a circle: the rectangle also
    # covers the Java Sea, the Karimata Strait and the South China Sea, where a
    # "risk" dot would be meaningless visual noise.
    on_land = land_cell_mask(
        (min_lon, min_lat, max_lon, max_lat), n_rows, n_cols,
    )
    risk_group = folium.FeatureGroup(name="Fire risk — Kalimantan (ML heuristic)", show=True)
    for row in range(n_rows):
        for col in range(n_cols):
            if not on_land[row, col]:
                continue
            risk = float(kal_risk[row, col])
            # Row 0 is the northern edge (row index increases southward).
            lat = max_lat - (row + 0.5) * d_lat
            lon = min_lon + (col + 0.5) * d_lon
            color = (
                "darkred" if risk > 0.45
                else "red" if risk > 0.35
                else "orange" if risk > 0.25
                else "beige"
            )
            folium.CircleMarker(
                location=[lat, lon],
                radius=max(2, min(7, int(risk * 18) + 2)),
                fill=True,
                fill_color=color,
                fill_opacity=0.6,
                color=None,
                weight=0,
            ).add_to(risk_group)
    risk_group.add_to(m)

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
            for (lat, lon) in pts:
                marker_icon = bio_icon(key, size=30)
                if marker_icon is not None:
                    # Custom icon from assets/icons/ (user-replaceable).
                    folium.Marker(
                        location=[lat, lon],
                        icon=marker_icon,
                        popup=f"{layer.query}<br>({lat:.3f}, {lon:.3f})",
                    ).add_to(bio_group)
                else:
                    # No icon file: keep the plain triangle fallback.
                    folium.RegularPolygonMarker(
                        location=[lat, lon],
                        number_of_sides=3,
                        rotation=0,
                        radius=6,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.85,
                        color=color,
                        weight=1,
                        popup=f"▲ {layer.query}<br>({lat:.3f}, {lon:.3f})",
                    ).add_to(bio_group)
        bio_group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    st_folium(m, use_container_width=True, height=700)


def _render_risk_map_folium(
    risk_df: Any,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    bio_layers: Any = None,
) -> None:
    """Render the ML risk map as a folium map with an Indonesia zoom cap."""
    try:
        import folium
        from streamlit_folium import st_folium
    except Exception as exc:
        st.warning(
            f"Risk map could not render via folium: {exc}. Falling back to st.map."
        )
        st.map(risk_df)
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
    )

    step = 0.02
    risk_layer = folium.FeatureGroup(name="Fire risk (ML)", show=True)
    for (lat, lon, risk) in zip(
        risk_df["lat"].tolist(),
        risk_df["lon"].tolist(),
        risk_df["risk"].tolist(),
    ):
        color = (
            "red" if risk > 0.5
            else "orange" if risk > 0.2
            else "green"
        )
        folium.CircleMarker(
            location=[lat, lon],
            radius=max(3, min(9, int(risk * 30) + 3)),
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            color="black",
            weight=0.6,
        ).add_to(risk_layer)
    risk_layer.add_to(m)

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
            for (lat, lon) in pts:
                marker_icon = bio_icon(key, size=28)
                if marker_icon is not None:
                    folium.Marker(
                        location=[lat, lon],
                        icon=marker_icon,
                        popup=f"{layer.query}<br>({lat:.3f}, {lon:.3f})",
                    ).add_to(bio_group)
                else:
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=5,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.55,
                        color=color,
                        weight=0.8,
                        popup=f"{layer.query}<br>({lat:.3f}, {lon:.3f})",
                    ).add_to(bio_group)
        bio_group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
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

    for key, layer in state.bio_layers.items():
        color = bio_colors.get(key, "#888888")
        for (lat, lon) in layer.points:
            marker_icon = bio_icon(key, size=30)
            if marker_icon is not None:
                folium.Marker(
                    location=[lat, lon],
                    icon=marker_icon,
                    popup=f"{layer.query}<br>({lat:.3f}, {lon:.3f})",
                ).add_to(m)
            else:
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=6,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.75,
                    color="black",
                    weight=0.8,
                    popup=f"{layer.query}<br>({lat:.3f}, {lon:.3f})",
                ).add_to(m)

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

# Relative widths of [map column, emergency sidebar].
MAP_COLUMN_WEIGHT = 2.4
EMERGENCY_COLUMN_WEIGHT = 1.0


def _inject_layout_css(panel_open: bool) -> None:
    """Style the page so the maps fill their column edge-to-edge.

    The emergency content is a *real* second column (see ``run_streamlit``),
    not a floating overlay, so the OSM tiles underneath are never covered.
    """
    if not STREAMLIT_AVAILABLE:
        return

    panel_css = ""
    if panel_open:
        panel_css = """
        /* Second sidebar: stays in view while the maps scroll, scrolls itself. */
        .st-key-emergency_panel {
            position: sticky;
            top: 3.5rem;
            max-height: calc(100vh - 4.5rem);
            overflow-y: auto;
            overscroll-behavior: contain;
            padding: .4rem .9rem 2rem .9rem;
            border-left: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: .5rem;
        }
        .st-key-emergency_panel h3 { font-size: 1.15rem; margin: 0 0 .25rem 0; }
        .st-key-emergency_panel h4 { font-size: .98rem; margin: .7rem 0 .15rem 0; }
        .st-key-emergency_panel [data-testid="stVerticalBlock"] { gap: .4rem; }
        .st-key-emergency_panel [data-testid="stExpander"] { margin-bottom: .25rem; }
        @media (max-width: 900px) {
            .st-key-emergency_panel {
                position: static;
                max-height: none;
                border-left: none;
                border-top: 1px solid rgba(128, 128, 128, 0.25);
                padding: 1rem 0 2rem 0;
            }
        }
        """

    st.markdown(
        f"""
        <style>
        .block-container {{
            padding-left: 1.25rem !important;
            padding-right: 1.25rem !important;
            max-width: none !important;
        }}
        [data-testid="stSidebar"] {{
            width: 36rem !important;
            min-width: 36rem !important;
        }}
        /* Let every Folium/Leaflet iframe use its whole column and leave no
           unpainted gutter around the OSM tiles. */
        iframe[title="streamlit_folium.st_folium"],
        iframe[title="st_folium.st_folium"] {{
            width: 100% !important;
            display: block;
        }}
        .leaflet-container {{ background: #f2efe9; }}
        {panel_css}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main Streamlit view
# ---------------------------------------------------------------------------


def run_streamlit() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🔥",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    write_app_title()

    st.sidebar.title("Controls")
    wind_dir = st.sidebar.slider(
        "Wind direction (deg)",
        min_value=0,
        max_value=360,
        value=int(config.default_wind_direction_deg()),
        step=5,
        help="Meteorological convention: 0 = wind FROM north.",
    )
    use_hotspots = st.sidebar.checkbox("Use FIRMS hotspots for seeding", value=True)
    n_steps = st.sidebar.slider("CA steps", min_value=1, max_value=20, value=12, step=1)
    run_button = st.sidebar.button("Run simulation")

    st.sidebar.divider()
    show_emergency_panel = st.sidebar.toggle(
        "Emergency sidebar (right)",
        value=True,
        help=(
            "Show your location, nearby hotspots and mitigation guidance in a "
            "second sidebar on the right. The maps resize to fit beside it, so "
            "no map tile is hidden underneath."
        ),
        key="show_emergency_panel",
    )
    with st.sidebar.expander("Custom flora & fauna icons"):
        st.caption(
            "Replace the marker images in the folder below, then rerun the app "
            "(press R). Keep the taxon name in the filename; PNG, WEBP, JPG and "
            "SVG are supported."
        )
        st.code(str(icon_folder()))

    # Give the maps the full width when the second sidebar is switched off.
    _inject_layout_css(panel_open=show_emergency_panel)

    show_bounding_box_info()

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

    # Map column + optional second sidebar. Using real columns (instead of a
    # floating panel) means the OSM tiles always fill the whole visible area.
    if show_emergency_panel:
        map_column, panel_column = st.columns(
            [MAP_COLUMN_WEIGHT, EMERGENCY_COLUMN_WEIGHT], gap="medium"
        )
    else:
        map_column = st.container()
        panel_column = None

    with map_column:
        step_idx = st.slider(
            "CA step",
            min_value=0,
            max_value=len(state.frames) - 1,
            value=state.current_step,
            step=1,
            key="ca_step_slider",
        )

        auto_play = st.checkbox(
            "Auto-play dot grid",
            value=False,
            help=(
                "When enabled, the dot grid advances one CA step every ~1.0s. "
                "This is a demo convenience; it is not a real-time fire spread animation."
            ),
            key="auto_play",
        )

    if auto_play:
        step_idx = int(min(len(state.frames) - 1, step_idx + 1))

    current_frame = state.frames[step_idx]

    # CA panel lives in the collapsible Streamlit sidebar: use the « button at
    # the top of the sidebar to close it. The main area is then entirely maps,
    # which take roughly 80% of the screen with the sidebar open and ~100%
    # when it is collapsed.
    with st.sidebar:
        _render_ca_sidebar(state, current_frame, state.params, step_idx)
        st.divider()
        with st.expander("Fire spread (dot grid)", expanded=True):
            st.caption(
                "Each cell is a small dot colored by its CA state. "
                "Close this sidebar to let the maps fill the screen."
            )
            _render_dot_grid(current_frame, state.params, dot_image_path=DOT_IMAGE_PATH)

    # Emergency content lives in its own column, beside (not on top of) the
    # maps, and scrolls independently of the page. It renders before the maps
    # so the sidebar is populated while the map layers are being built.
    if panel_column is not None:
        with panel_column:
            with st.container(key="emergency_panel"):
                _render_emergency_panel(state)

    with map_column:
        _render_map_area(state, current_frame)


# ---------------------------------------------------------------------------
# Map area (left column): biodiversity + Kalimantan-wide risk map
# ---------------------------------------------------------------------------


def _render_risk_provenance(state: Any) -> None:
    """One caption line saying exactly what produced the risk surface."""
    source = getattr(state, "risk_source", "heuristic baseline")
    if source == "random forest":
        metrics = getattr(state, "risk_metrics", None) or {}
        bits = ["Random Forest trained on NASA FIRMS hotspots"]
        if metrics.get("roc_auc") is not None:
            bits.append(f"temporal-split test ROC-AUC {metrics['roc_auc']:.3f}")
        if metrics.get("average_precision") is not None:
            bits.append(f"PR-AUC {metrics['average_precision']:.3f}")
        if getattr(state, "risk_conditioned_on", None):
            bits.append(f"conditioned on hotspots through {state.risk_conditioned_on}")
        st.caption(
            "Per-cell probability of a FIRMS hotspot on the day after "
            f"{state.risk_conditioned_on or 'the last observed day'} · "
            + " · ".join(bits)
        )
    else:
        st.caption(f"Risk surface source: {source}.")


def _render_map_area(state: Any, current_frame: Any) -> None:
    """Render both maps so they fill the map column edge-to-edge."""
    st.subheader("Biodiversity distribution (Kalimantan flora/fauna)")
    st.caption(
        "Second map layer: iNaturalist observations filtered to Kalimantan only. "
        "Taxa shown: Bornean Orangutan, Proboscis monkey, Rafflesia, Nepenthes. "
        "Live API if available; offline stub otherwise."
    )
    _render_bio_map(state)

    # Risk map (full width below the biodiversity map)
    st.divider()
    if getattr(state, "risk_source", "") == "random forest":
        st.subheader("Risk map (Random Forest prediction)")
    else:
        st.subheader("Risk map (physics heuristic)")
    _render_risk_provenance(state)

    show_bio_overlay = st.checkbox(
        "Overlay flora & fauna icons on the maps",
        value=True,
        help=(
            "Fire risk is drawn as circles; flora/fauna are Kalimantan-only, "
            "shown as custom icons from assets/icons/ with dashed hull "
            "polygons. Toggle each layer via the layer control."
        ),
    )

    if state.risk_map is not None:
        rows = current_frame.n_rows
        cols = current_frame.n_cols
        min_lon, min_lat, max_lon, max_lat = config.bounding_box()
        d_lon = config.grid_spacing_deg()
        d_lat = config.grid_spacing_deg()
        risk_df = pd.DataFrame(
            {
                "lat": [
                    max_lat - (row + 0.5) * d_lat
                    for row in range(rows)
                    for _col in range(cols)
                ],
                "lon": [
                    min_lon + (col + 0.5) * d_lon
                    for _row in range(rows)
                    for col in range(cols)
                ],
                "risk": [
                    risk_at(state, row, col)
                    for row in range(rows)
                    for col in range(cols)
                ],
            }
        )
        if risk_df["risk"].max() <= 0.0:
            st.warning("Risk map is currently empty; try running the simulation.")
        else:
            _render_risk_map_folium(
                risk_df,
                min_lon,
                min_lat,
                max_lon,
                max_lat,
                bio_layers=(state.bio_layers if (show_bio_overlay and getattr(state, "bio_layers", None)) else None),
            )
    else:
        st.warning("Risk map unavailable.")

    # Island-wide overview: coarse physics surface, not the trained model.
    if getattr(state, "kalimantan_risk", None) is not None:
        with st.expander("Kalimantan-wide overview (physics baseline, not the trained model)"):
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
                "Circles = coarse wind/peat heuristic over the whole of "
                "Kalimantan (~16 km cells), drawn on land cells only. "
                "The Random Forest above covers only "
                "the 2° demo box, where its OSM and FIRMS features exist. "
                "Icons = iNaturalist flora/fauna, Kalimantan only "
                f"(swap the images in {icon_folder()})."
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
