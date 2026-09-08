"""IGNIS-Sim Kalimantan demo web app.

This is a Streamlit-based demo for the science project. It shows:

- the demo bounding box map (OSM context + fire hotspots if available),
- the CA simulation stepped forward in time with wind direction control,
- a per-cell risk map from the baseline ML model,
- civilian-mitigation guidance when fire approaches a settlement or rural cell.

If Streamlit is not installed, the app falls back to a simple script mode that
prints a summary to the console.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except Exception:
    STREAMLIT_AVAILABLE = False

from src import config
from src.ca import CaGrid, CaParams, run_simulation
from src.fire_data import build_cell_grid, build_fire_dataset, load_firms_hotspots
from src.features import build_context_map, build_feature_table
from src.ml import make_model, predict_risk_map
from src.mitigation import build_mitigation_contexts, format_actions_for_display
from app.ca_simulator import initialize_simulation, step_forward, state_distribution, mitigation_for, risk_at


APP_TITLE = config.__dict__.get("APP_TITLE", "IGNIS-Sim Kalimantan")


def write_app_title() -> None:
    title = APP_TITLE or "IGNIS-Sim Kalimantan"
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


def run_streamlit() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🔥", layout="wide")
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

    show_bounding_box_info()

    state: Optional[Any] = None
    if run_button or state is None:
        with st.spinner("Initializing simulation..."):
            try:
                state = initialize_simulation(
                    wind_dir_deg=float(wind_dir),
                    n_steps=n_steps,
                    use_hotspots=use_hotspots,
                )
            except Exception as exc:
                st.error(f"Simulation initialization failed: {exc}")
                state = None

    if state is None:
        st.warning("Could not initialize the simulation. Check data files and try again.")
        return

    step_idx = st.slider(
        "CA step",
        min_value=0,
        max_value=len(state.frames) - 1,
        value=state.current_step,
        step=1,
    )

    current_frame = state.frames[step_idx]

    left_col, right_col = st.columns(2)
    with left_col:
        st.subheader("Fire spread (CA)")
        dist = state_distribution(current_frame)
        st.write(dist)
        st.caption("Cell states: healthy, igniting, burning, burned, peat_risk.")

    with right_col:
        st.subheader("Risk map (ML)")
        if state.risk_map is not None:
            st.write("Predicted fire presence probability per cell.")
            st.map(
                pd.DataFrame(
                    {
                        "lat": [
                            config.bounding_box()[1]
                            + (row + 0.5) * config.grid_spacing_deg()
                            for row in range(current_frame.n_rows)
                        ],
                        "lon": [
                            config.bounding_box()[0]
                            + (col + 0.5) * config.grid_spacing_deg()
                            for col in range(current_frame.n_cols)
                        ],
                        "risk": [
                            risk_at(state, row, col)
                            for row in range(current_frame.n_rows)
                            for col in range(current_frame.n_cols)
                        ],
                    }
                )
            )
        else:
            st.warning("Risk map unavailable.")

    st.subheader("Mitigation guidance")
    contexts_present = bool(state.contexts)
    if not contexts_present:
        st.info("No settlement or rural cells are currently near the fire.")
    else:
        for (row, col), ctx in state.contexts.items():
            actions = mitigation_for(state, row, col)
            if not actions:
                continue
            title = "Settlement" if ctx.is_settlement else "Rural area"
            st.markdown(f"#### {title} at cell ({row}, {col})")
            st.write(
                f"CA state: **{ctx.ca_state}**, predicted risk: {ctx.predicted_risk:.2f}, "
                f"wind: {ctx.wind_dir_deg:.0f}°"
            )
            for a in actions:
                st.warning(f"{a['icon']} **{a['title']}** — {a['description']} ({a['timing']})")

    with st.expander("Show CA explanation"):
        from src.ca import step_explanation
        st.write(step_explanation(state.params))

    st.caption("This is a science-fair prototype, not an emergency response system.")


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
