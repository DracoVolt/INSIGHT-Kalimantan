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
    panel_rules = "" if panel_open else ".st-key-emergency_panel, .insight-emergency-fold-tab { display: none !important; }"
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
    .insight-fold-tab,
    .insight-emergency-fold-tab {{
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
    .insight-fold-tab,
    .insight-emergency-fold-tab {{
        transition: transform 110ms ease-out, background-color 110ms ease-out;
    }}
    button:active,
    [role="button"]:active,
    [data-testid="stBaseButton"]:active,
    [data-testid="stExpander"] summary:active,
    .insight-fold-tab:active,
    .insight-emergency-fold-tab:active {{
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
        transition: left .25s ease, right .25s ease;
    }}
    /* Bottom searchbar inside the CA timeline bar */
    .st-key-windy_timeline [data-testid="stTextInput"] {{
        margin: 0 !important;
        padding: 0 !important;
    }}
    .st-key-windy_timeline [data-baseweb="input"] {{
        background: rgba(255, 255, 255, 0.07) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 10px !important;
        height: 30px !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}
    .st-key-windy_timeline [data-baseweb="input"] input {{
        color: #e6eef6 !important;
        font-size: 11.5px !important;
        padding: 2px 10px !important;
    }}
    .st-key-windy_timeline [data-baseweb="input"] input::placeholder {{
        color: #8fa3b5 !important;
        font-size: 11px !important;
    }}
    .st-key-windy_timeline [data-baseweb="input"]:focus-within {{
        border-color: rgba(56, 189, 248, 0.65) !important;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.22) !important;
    }}
    .st-key-windy_timeline [data-testid="stCaptionContainer"] p {{
        font-size: 11px !important;
        line-height: 1.25 !important;
        margin: 0 !important;
        color: #9fb2c4 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }}
    .st-key-windy_timeline [data-testid="stCheckbox"] {{
        margin: 0 !important;
        padding: 0 !important;
    }}
    .st-key-windy_timeline [data-testid="stCheckbox"] label span {{
        font-size: 11px !important;
        color: #c0d3e5 !important;
    }}
    {panel_rules}

    /* --- Foldable left and right panels, with bookmark tabs -------- */
    /* The tabs are labels outside the panels; they toggle hidden checkboxes,
       so nothing needs JavaScript. On tablets and phones the panels start folded
       and the tabs are the only things on screen, leaving the map clear. */
    #insight-fold,
    #insight-emergency-fold {{
        position: absolute; width: 1px; height: 1px;
        opacity: 0; pointer-events: none;
    }}
    .insight-fold-tab,
    .insight-emergency-fold-tab {{
        position: fixed; top: 0; z-index: 1200;
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
        transition: left .25s ease, right .25s ease, background .2s ease;
    }}
    .insight-fold-tab {{ left: 26px; }}
    .insight-emergency-fold-tab {{ right: 26px; }}

    /* Touch has no hover: the browser fakes it on the first tap and leaves it
       stuck there, so hover styles exist only where a real pointer hovers. */
    @media (hover: hover) and (pointer: fine) {{
        .insight-fold-tab:hover,
        .insight-emergency-fold-tab:hover {{ background: rgba(24, 34, 46, 0.96); }}
    }}
    .insight-fold-tab .tab-fold,
    .insight-emergency-fold-tab .tab-fold {{ display: inline; }}
    .insight-fold-tab .tab-unfold,
    .insight-emergency-fold-tab .tab-unfold {{ display: none; }}
    .st-key-windy_controls,
    .st-key-emergency_panel {{
        transition: transform .25s ease, opacity .2s ease;
    }}

    /* Wide screens: open by default, the tabs fold them. */
    @media (min-width: 1181px) {{
        body:has(#insight-fold:checked) .st-key-windy_controls {{
            transform: translateX(calc(-100% - 30px));
            opacity: 0;
            pointer-events: none;
        }}
        body:has(#insight-fold:checked) .insight-fold-tab .tab-fold {{ display: none; }}
        body:has(#insight-fold:checked) .insight-fold-tab .tab-unfold {{ display: inline; }}
        body:has(#insight-fold:checked) .st-key-windy_timeline {{ left: 26px; }}

        body:has(#insight-emergency-fold:checked) .st-key-emergency_panel {{
            transform: translateX(calc(100% + 30px));
            opacity: 0;
            pointer-events: none;
        }}
        body:has(#insight-emergency-fold:checked) .insight-emergency-fold-tab .tab-fold {{ display: none; }}
        body:has(#insight-emergency-fold:checked) .insight-emergency-fold-tab .tab-unfold {{ display: inline; }}
        body:has(#insight-emergency-fold:checked) .st-key-windy_timeline {{ right: 26px; }}
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
    .emergency-panel-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 2px;
    }}
    .emergency-panel-header h3 {{
        margin: 0 !important;
        font-size: 1.02rem !important;
        display: inline-block;
    }}
    .emergency-close-btn {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border-radius: 7px;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #9fb2c4;
        font-size: 13px;
        font-weight: 600;
        line-height: 1;
        cursor: pointer;
        user-select: none;
        -webkit-user-select: none;
        transition: all 0.15s ease;
    }}
    .emergency-close-btn:hover {{
        background: rgba(239, 68, 68, 0.25);
        border-color: rgba(239, 68, 68, 0.5);
        color: #fca5a5;
    }}
    .emergency-close-btn:active {{
        transform: scale(0.92);
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

    /* Tablets and phones: floating panels start folded behind their bookmark tabs. */
    @media (max-width: 1180px) {{
        .st-key-windy_timeline {{ left: 14px; right: 14px; }}
        .st-key-windy_layers {{ padding: 22px 24px 150px; }}

        .insight-fold-tab {{ left: 14px; }}
        .insight-emergency-fold-tab {{ right: 14px; }}

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
        .insight-fold-tab .tab-fold {{ display: none; }}
        .insight-fold-tab .tab-unfold {{ display: inline; }}
        body:has(#insight-fold:checked) .insight-fold-tab .tab-fold {{ display: inline; }}
        body:has(#insight-fold:checked) .insight-fold-tab .tab-unfold {{ display: none; }}

        body:not(:has(#insight-emergency-fold:checked)) .st-key-emergency_panel {{
            transform: translateX(calc(100% + 30px));
            opacity: 0;
            pointer-events: none;
        }}
        .st-key-emergency_panel {{
            position: fixed !important;
            right: 14px !important;
            top: 14px !important;
            width: min(330px, 80vw) !important;
            max-height: 72vh !important;
            max-height: 72dvh !important;
            z-index: 1000 !important;
        }}
        .insight-emergency-fold-tab .tab-fold {{ display: none; }}
        .insight-emergency-fold-tab .tab-unfold {{ display: inline; }}
        body:has(#insight-emergency-fold:checked) .insight-emergency-fold-tab .tab-fold {{ display: inline; }}
        body:has(#insight-emergency-fold:checked) .insight-emergency-fold-tab .tab-unfold {{ display: none; }}
        body:has(#insight-emergency-fold:checked) .st-key-emergency_panel {{
            transform: none !important;
            opacity: 1 !important;
            pointer-events: auto !important;
        }}
    }}
    @media (max-width: 760px) {{
        .st-key-windy_map iframe[title] {{
            height: 100vh !important;
            height: 100dvh !important;
        }}
        .insight-fold-tab {{ left: 14px; }}
        .insight-emergency-fold-tab {{ right: 14px; }}
    }}

    /* --- Pull to Refresh indicator ------------------------------ */
    .insight-ptr {{
        position: fixed;
        top: 0;
        left: 50%;
        transform: translate(-50%, -100%);
        z-index: 2500;
        pointer-events: none;
        transition: transform 0.22s cubic-bezier(0.18, 0.89, 0.32, 1.28), opacity 0.2s ease;
        opacity: 0;
    }}
    .insight-ptr.ptr-active {{
        opacity: 1;
        pointer-events: auto;
    }}
    .insight-ptr.ptr-refreshing {{
        opacity: 1;
        transform: translate(-50%, 18px) !important;
        pointer-events: auto;
    }}
    .insight-ptr-pill {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 7px 18px;
        border-radius: 999px;
        background: rgba(8, 13, 18, 0.92);
        backdrop-filter: blur(16px) saturate(160%);
        -webkit-backdrop-filter: blur(16px) saturate(160%);
        border: 1px solid rgba(255, 255, 255, 0.16);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6), 0 0 14px rgba(56, 189, 248, 0.2);
        color: #e6eef6;
        font: 600 12px/1.2 system-ui, -apple-system, sans-serif;
        letter-spacing: 0.04em;
        cursor: pointer;
        user-select: none;
        -webkit-user-select: none;
        touch-action: none;
        transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.1s ease;
    }}
    .insight-ptr-pill:active {{
        transform: scale(0.97);
    }}
    .insight-ptr-icon {{
        width: 14px;
        height: 14px;
        color: #38bdf8;
        transition: transform 0.2s ease-out, color 0.2s ease;
        display: inline-block;
        vertical-align: middle;
    }}
    .insight-ptr-spinner {{
        width: 14px;
        height: 14px;
        color: #38bdf8;
        display: none;
        vertical-align: middle;
    }}
    .ptr-ready .insight-ptr-icon {{
        transform: rotate(180deg);
        color: #4ade80;
    }}
    .ptr-ready .insight-ptr-pill {{
        border-color: rgba(74, 222, 128, 0.5);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6), 0 0 16px rgba(74, 222, 128, 0.35);
    }}
    .ptr-refreshing .insight-ptr-icon {{
        display: none;
    }}
    .ptr-refreshing .insight-ptr-spinner {{
        display: inline-block;
        animation: insight-ptr-spin 0.85s linear infinite;
        color: #38bdf8;
    }}
    @keyframes insight-ptr-spin {{
        from {{ transform: rotate(0deg); }}
        to {{ transform: rotate(360deg); }}
    }}
    </style>
    """


def _fold_handle_html() -> str:
    """Bookmark tabs (and hidden checkboxes) that fold the left and right panels."""
    return (
        "<input type='checkbox' id='insight-fold' aria-label='Fold the controls panel'/>"
        "<label class='insight-fold-tab' for='insight-fold'>"
        "<span class='tab-fold'>&#10005; Close</span>"
        "<span class='tab-unfold'>&#9776; Controls</span>"
        "</label>"
        "<input type='checkbox' id='insight-emergency-fold' aria-label='Fold the emergency panel'/>"
        "<label class='insight-emergency-fold-tab' for='insight-emergency-fold'>"
        "<span class='tab-fold'>&#10005; Close</span>"
        "<span class='tab-unfold'>&#9888; Emergency</span>"
        "</label>"
    )


def _pull_to_refresh_html() -> str:
    """Pull to refresh indicator pill HTML markup."""
    return """
    <div id="insight-ptr" class="insight-ptr" role="status" aria-live="polite">
        <div class="insight-ptr-pill" title="Click or pull down to refresh simulation">
            <svg class="insight-ptr-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <svg class="insight-ptr-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
            </svg>
            <span id="insight-ptr-text" class="insight-ptr-text">Pull to refresh</span>
        </div>
    </div>
    """


def _pull_to_refresh_js() -> str:
    """Client-side touch and mouse gesture listener for pull-to-refresh."""
    return """
    <script>
    (function initPullToRefresh() {
        var win = window.parent || window;
        var doc = win.document;

        if (win.__insight_ptr_initialized) return;
        win.__insight_ptr_initialized = true;

        var startY = 0;
        var startX = 0;
        var isPulling = false;
        var canPull = false;
        var isRefreshing = false;
        var isMouseDown = false;

        function getPtr() {
            return doc.getElementById('insight-ptr');
        }
        function getText() {
            return doc.getElementById('insight-ptr-text');
        }

        function triggerRefresh() {
            if (isRefreshing) return;
            isRefreshing = true;

            var ptr = getPtr();
            var txt = getText();
            if (ptr) {
                ptr.classList.remove('ptr-ready', 'ptr-active');
                ptr.classList.add('ptr-refreshing');
                ptr.style.transform = 'translate(-50%, 18px)';
            }
            if (txt) {
                txt.textContent = 'Refreshing simulation...';
            }

            setTimeout(function() {
                var buttons = doc.querySelectorAll('button');
                var runBtn = null;
                for (var i = 0; i < buttons.length; i++) {
                    var label = (buttons[i].innerText || buttons[i].textContent || '').trim().toLowerCase();
                    if (label.indexOf('run simulation') !== -1) {
                        runBtn = buttons[i];
                        break;
                    }
                }
                if (runBtn) {
                    runBtn.click();
                    setTimeout(function() {
                        resetPtr();
                    }, 2500);
                } else {
                    win.location.reload();
                }
            }, 300);
        }

        function resetPtr() {
            isRefreshing = false;
            isPulling = false;
            canPull = false;
            isMouseDown = false;
            var ptr = getPtr();
            var txt = getText();
            if (ptr) {
                ptr.classList.remove('ptr-active', 'ptr-ready', 'ptr-refreshing');
                ptr.style.transform = 'translate(-50%, -100%)';
            }
            if (txt) {
                txt.textContent = 'Pull to refresh';
            }
        }

        // Touch events
        win.addEventListener('touchstart', function(e) {
            if (isRefreshing || e.touches.length !== 1) return;
            var touch = e.touches[0];
            startY = touch.clientY;
            startX = touch.clientX;

            var target = e.target;
            var scrollParent = target.closest ? target.closest('.st-key-windy_controls, .st-key-emergency_panel, [data-testid="stMain"]') : null;
            var atTop = (!scrollParent || scrollParent.scrollTop <= 0);

            var isMap = target.closest && target.closest('.leaflet-container, iframe');
            if (isMap && touch.clientY > 80) {
                canPull = false;
                return;
            }

            if (atTop && touch.clientY <= 140) {
                canPull = true;
                isPulling = false;
            } else {
                canPull = false;
            }
        }, { passive: true });

        win.addEventListener('touchmove', function(e) {
            if (!canPull || isRefreshing || e.touches.length !== 1) return;
            var touch = e.touches[0];
            var dy = touch.clientY - startY;
            var dx = Math.abs(touch.clientX - startX);

            if (dy > 10 && dy > dx * 1.1) {
                isPulling = true;
                var pull = Math.min(Math.pow(dy, 0.82) * 1.8, 85);
                var ptr = getPtr();
                var txt = getText();

                if (ptr) {
                    ptr.classList.add('ptr-active');
                    ptr.style.transform = 'translate(-50%, ' + (pull - 42) + 'px)';
                    if (pull >= 54) {
                        ptr.classList.add('ptr-ready');
                        if (txt) txt.textContent = 'Release to refresh';
                    } else {
                        ptr.classList.remove('ptr-ready');
                        if (txt) txt.textContent = 'Pull to refresh';
                    }
                }
            }
        }, { passive: true });

        win.addEventListener('touchend', function(e) {
            if (!canPull || !isPulling || isRefreshing) {
                canPull = false;
                isPulling = false;
                return;
            }
            var ptr = getPtr();
            if (ptr && ptr.classList.contains('ptr-ready')) {
                triggerRefresh();
            } else {
                resetPtr();
            }
        }, { passive: true });

        // Desktop mouse drag support
        win.addEventListener('mousedown', function(e) {
            if (isRefreshing || e.button !== 0) return;
            if (e.clientY <= 60 || (e.target && e.target.closest && e.target.closest('.insight-fold-tab, .insight-ptr-pill'))) {
                isMouseDown = true;
                startY = e.clientY;
                startX = e.clientX;
                canPull = true;
                isPulling = false;
            }
        });

        win.addEventListener('mousemove', function(e) {
            if (!isMouseDown || !canPull || isRefreshing) return;
            var dy = e.clientY - startY;
            var dx = Math.abs(e.clientX - startX);

            if (dy > 10 && dy > dx * 1.1) {
                isPulling = true;
                var pull = Math.min(Math.pow(dy, 0.82) * 1.8, 85);
                var ptr = getPtr();
                var txt = getText();
                if (ptr) {
                    ptr.classList.add('ptr-active');
                    ptr.style.transform = 'translate(-50%, ' + (pull - 42) + 'px)';
                    if (pull >= 54) {
                        ptr.classList.add('ptr-ready');
                        if (txt) txt.textContent = 'Release to refresh';
                    } else {
                        ptr.classList.remove('ptr-ready');
                        if (txt) txt.textContent = 'Pull to refresh';
                    }
                }
            }
        });

        win.addEventListener('mouseup', function(e) {
            if (!isMouseDown) return;
            isMouseDown = false;
            if (!canPull || !isPulling || isRefreshing) {
                canPull = false;
                isPulling = false;
                return;
            }
            var ptr = getPtr();
            if (ptr && ptr.classList.contains('ptr-ready')) {
                triggerRefresh();
            } else {
                resetPtr();
            }
        });

        // Direct click on pill to refresh
        doc.addEventListener('click', function(e) {
            var pill = e.target.closest ? e.target.closest('.insight-ptr-pill') : null;
            if (pill) {
                triggerRefresh();
            }
        });
    })();
    </script>
    """


def inject_layout_css(panel_open: bool = True) -> None:
    """Write the shell CSS, fold handle and pull-to-refresh into the page."""
    import streamlit as st

    st.markdown(_css(panel_open), unsafe_allow_html=True)
    st.markdown(_fold_handle_html(), unsafe_allow_html=True)
    st.markdown(_pull_to_refresh_html(), unsafe_allow_html=True)
