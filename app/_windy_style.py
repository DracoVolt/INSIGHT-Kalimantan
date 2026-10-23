"""Windy-inspired visual shell for the INSIGHT demo.

Windy (windy.com) is map-first: the map is the page, and controls, legend and
timeline float over it in translucent panels. This module holds the CSS that
reproduces that shell in Streamlit — hiding the Streamlit chrome, pinning the
control / emergency / timeline containers over a full-bleed Folium map, and
drawing the panels as dark glass.

The panel DOM hooks are the keyed containers created in ``app.main``:
``windy_controls``, ``windy_timeline``, ``windy_map``, ``windy_layers`` and
``emergency_panel``.
"""

from __future__ import annotations


def _css(panel_open: bool) -> str:
    panel_rules = "" if panel_open else ".st-key-emergency_panel { display: none !important; }"
    return f"""
    <style>
    /* --- Streamlit chrome out of the way ------------------------- */
    header[data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    footer {{ display: none !important; }}
    .stApp, [data-testid="stAppViewContainer"], .main {{ background: #070c11; }}
    [data-testid="stMainBlockContainer"] {{
        padding: 0 !important;
        max-width: 100% !important;
    }}
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {{
        gap: 0 !important;
    }}

    /* --- Floating glass panels ----------------------------------- */
    .st-key-windy_controls,
    .st-key-windy_timeline,
    .st-key-emergency_panel {{
        position: fixed;
        z-index: 1000;
        background: rgba(8, 13, 18, 0.84);
        backdrop-filter: blur(16px) saturate(150%);
        -webkit-backdrop-filter: blur(16px) saturate(150%);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 16px;
        box-shadow: 0 18px 48px rgba(0, 0, 0, 0.55);
        color: #e6eef6;
    }}
    .st-key-windy_controls {{
        left: 14px; top: 14px; width: 312px;
        max-height: calc(100vh - 132px);
        overflow-y: auto; overscroll-behavior: contain;
        overflow-anchor: none;
        scrollbar-width: thin;
        padding: 12px 14px 16px;
    }}
    .st-key-emergency_panel {{
        right: 14px; top: 14px; width: 330px;
        max-height: calc(100vh - 132px);
        overflow-y: auto; overscroll-behavior: contain;
        overflow-anchor: none;
        scrollbar-width: thin;
        padding: 12px 16px 20px;
    }}
    /* Time scrubber: the bottom bar of the map, spanning the gap between the
       two side panels exactly like Windy's timeline. */
    .st-key-windy_timeline {{
        left: 340px; right: 360px; bottom: 14px;
        width: auto; transform: none;
        padding: 6px 18px 4px;
    }}
    {panel_rules}

    /* --- Compact typography inside the panels -------------------- */
    .st-key-windy_controls [data-testid="stVerticalBlock"],
    .st-key-windy_timeline [data-testid="stVerticalBlock"],
    .st-key-emergency_panel [data-testid="stVerticalBlock"] {{ gap: .45rem; }}
    .st-key-windy_controls label, .st-key-windy_timeline label {{
        font-size: .76rem !important; color: #9fb2c4 !important;
    }}
    .st-key-windy_controls h3, .st-key-emergency_panel h3 {{
        font-size: 1.02rem !important; margin: 0 0 .1rem 0 !important;
    }}
    .st-key-emergency_panel h4 {{
        font-size: .9rem !important; margin: .6rem 0 .1rem 0 !important;
    }}
    .st-key-windy_controls [data-testid="stExpander"] details,
    .st-key-emergency_panel [data-testid="stExpander"] details {{
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.03);
    }}

    /* --- Brand block --------------------------------------------- */
    .windy-brand {{ display: flex; flex-direction: column; gap: 1px; margin-bottom: 4px; }}
    .windy-brand b {{ font-size: 1.16rem; letter-spacing: .08em; color: #ffffff; }}
    .windy-brand span {{ font-size: .72rem; color: #8fa3b5; }}

    /* --- Full-bleed hero map ------------------------------------- */
    .st-key-windy_map iframe[title="streamlit_folium.st_folium"],
    .st-key-windy_map iframe[title="st_folium.st_folium"] {{
        width: 100% !important;
        height: 100vh !important;
        display: block;
        border: 0 !important;
    }}
    .leaflet-container {{ background: #dfe7ec; }}

    /* --- Secondary layers below the map -------------------------- */
    /* Below the hero the cards sit in the gap between the floating panels,
       so nothing is permanently hidden underneath them. */
    .st-key-windy_layers {{
        padding: 22px 352px 150px 336px;
        background: #070c11;
    }}
    .st-key-windy_layers [data-testid="stExpander"] details {{
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(255, 255, 255, 0.02);
    }}

    @media (max-width: 1180px) {{
        .st-key-windy_timeline {{ left: 14px; right: 14px; }}
        .st-key-windy_layers {{ padding: 22px 24px 150px; }}
    }}
    @media (max-width: 760px) {{
        .st-key-windy_controls, .st-key-emergency_panel {{
            position: static; width: auto; max-height: none; margin: 12px;
        }}
        .st-key-windy_map iframe {{ height: 70vh !important; }}
    }}
    </style>
    """


def inject_layout_css(panel_open: bool = True) -> None:
    """Write the shell CSS into the page (no-op outside Streamlit)."""
    import streamlit as st

    st.markdown(_css(panel_open), unsafe_allow_html=True)
