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
    /* --- Mobile platform baseline -------------------------------- */
    /* The lines in this block are the difference between "a website in a
       browser" and something that feels installed on a phone. */
    html {{
        /* No translucent gray flash over anything tappable. */
        -webkit-tap-highlight-color: transparent;
        /* No font inflation when the phone turns to landscape. */
        -webkit-text-size-adjust: 100%;
        /* Dragging the map past its edge must not pull-to-refresh the page. */
        overscroll-behavior: none;
        color-scheme: dark;
    }}
    body {{ overscroll-behavior: none; }}
    /* Controls, never content: a long-press on a button must not select its
       label or pop the copy callout, and the browser can fire click at once
       instead of waiting to see whether a double-tap zoom follows. */
    button,
    [role="button"],
    [data-testid="stBaseButton"],
    [data-testid="stExpander"] summary,
    .insight-fold-tab {{
        touch-action: manipulation;
        -webkit-user-select: none;
        user-select: none;
        -webkit-touch-callout: none;
    }}
    /* Press feedback on finger-down, not on release: a button that only
       reacts to click reads as lag even when the click is instant. */
    button,
    [role="button"],
    [data-testid="stBaseButton"],
    [data-testid="stExpander"] summary,
    .insight-fold-tab {{
        transition: transform 110ms ease-out, background-color 110ms ease-out;
    }}
    button:active,
    [role="button"]:active,
    [data-testid="stBaseButton"]:active,
    [data-testid="stExpander"] summary:active,
    .insight-fold-tab:active {{
        transform: scale(0.97);
    }}
    /* iOS zooms into any input below 16px on focus and never zooms back out.
       Streamlit sizes number inputs with a widget-scoped rule, so this one has
       to win outright — raising the size is the fix, banning zoom is not. */
    @media (pointer: coarse) {{
        input,
        textarea,
        select,
        [data-baseweb="input"] input {{ font-size: 16px !important; }}
    }}

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
    /* The scroll container is this section, not the document: keep its own
       bounce but never let a drag chain out into pull-to-refresh. */
    [data-testid="stMain"] {{ overscroll-behavior: contain; }}

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
        /* dvh tracks the visible area as the URL bar shows and hides; vh is
           the tallest case, so the panel would run under the toolbar. */
        max-height: calc(100vh - 132px);
        max-height: calc(100dvh - 132px);
        overflow-y: auto; overscroll-behavior: contain;
        overflow-anchor: none;
        scrollbar-width: thin;
        padding: 12px 14px 16px;
    }}
    .st-key-emergency_panel {{
        right: 14px; top: 14px; width: 330px;
        max-height: calc(100vh - 132px);
        max-height: calc(100dvh - 132px);
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

    /* --- Foldable left panel, with a bookmark tab ---------------- */
    /* The tab is a label outside the panel; it toggles the hidden checkbox, so
       nothing needs JavaScript. On tablets and phones the panel starts folded
       and the tab is the only thing left on screen, so you always know where
       the controls are. Browsers without :has() keep the old always-open
       behaviour. */
    #insight-fold {{
        position: absolute; width: 1px; height: 1px;
        opacity: 0; pointer-events: none;
    }}
    .insight-fold-tab {{
        position: fixed; left: 26px; top: 0; z-index: 1200;
        padding: 4px 13px 7px;
        border-radius: 0 0 13px 13px;
        background: rgba(8, 13, 18, 0.88);
        backdrop-filter: blur(16px) saturate(150%);
        -webkit-backdrop-filter: blur(16px) saturate(150%);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-top: 0;
        color: #e6eef6;
        font: 600 11px/1.1 system-ui, sans-serif;
        letter-spacing: .07em;
        text-transform: uppercase;
        cursor: pointer;
        user-select: none;
        -webkit-user-select: none;
        -webkit-tap-highlight-color: transparent;
        transition: left .25s ease, background .2s ease;
    }}
    /* Touch has no hover: the browser fakes it on the first tap and leaves it
       stuck there, so hover styles exist only where a real pointer hovers. */
    @media (hover: hover) and (pointer: fine) {{
        .insight-fold-tab:hover {{ background: rgba(24, 34, 46, 0.96); }}
    }}
    .insight-fold-tab .tab-fold {{ display: inline; }}
    .insight-fold-tab .tab-unfold {{ display: none; }}
    .st-key-windy_controls {{
        transition: transform .25s ease, opacity .2s ease;
    }}
    /* Wide screens: open by default, the tab folds it. */
    @media (min-width: 1181px) {{
        body:has(#insight-fold:checked) .st-key-windy_controls {{
            transform: translateX(calc(-100% - 30px));
            opacity: 0;
            pointer-events: none;
        }}
        body:has(#insight-fold:checked) .insight-fold-tab .tab-fold {{ display: none; }}
        body:has(#insight-fold:checked) .insight-fold-tab .tab-unfold {{ display: inline; }}
    }}

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
        height: 100dvh !important;
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

    /* Tablets and phones: a 312 px floating panel covers most of the screen,
       so it starts folded behind the bookmark tab. */
    @media (max-width: 1180px) {{
        .st-key-windy_timeline {{ left: 14px; right: 14px; }}
        .st-key-windy_layers {{ padding: 22px 24px 150px; }}
        body:not(:has(#insight-fold:checked)) .st-key-windy_controls {{
            transform: translateX(calc(-100% - 30px));
            opacity: 0;
            pointer-events: none;
        }}
        .st-key-windy_controls {{
            width: min(312px, 78vw);
            max-height: 70vh;
            max-height: 70dvh;
        }}
        /* The panel starts folded, so the tab offers the unfold action. */
        .insight-fold-tab .tab-fold {{ display: none; }}
        .insight-fold-tab .tab-unfold {{ display: inline; }}
        body:has(#insight-fold:checked) .insight-fold-tab .tab-fold {{ display: inline; }}
        body:has(#insight-fold:checked) .insight-fold-tab .tab-unfold {{ display: none; }}
    }}
    @media (max-width: 760px) {{
        .st-key-emergency_panel {{
            position: static; width: auto; max-height: none; margin: 12px;
        }}
        /* Same specificity as the full-bleed rule above, or that rule (also
           !important) would win and the phone map would still be full height,
           hiding the timeline behind it. */
        .st-key-windy_map iframe[title] {{
            height: 70vh !important;
            height: 70dvh !important;
        }}
        .insight-fold-tab {{ left: 14px; }}
    }}
    </style>
    """


def _fold_handle_html() -> str:
    """The bookmark tab (and its hidden checkbox) that folds the left panel."""
    return (
        "<input type='checkbox' id='insight-fold' aria-label='Fold the controls panel'/>"
        "<label class='insight-fold-tab' for='insight-fold'>"
        "<span class='tab-fold'>&#10005; Close</span>"
        "<span class='tab-unfold'>&#9776; Controls</span>"
        "</label>"
    )


def inject_layout_css(panel_open: bool = True) -> None:
    """Write the shell CSS and the fold handle into the page."""
    import streamlit as st

    st.markdown(_css(panel_open), unsafe_allow_html=True)
    st.markdown(_fold_handle_html(), unsafe_allow_html=True)
