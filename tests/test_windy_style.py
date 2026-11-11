"""Unit tests for the Windy-style shell and pull-to-refresh feature."""

from __future__ import annotations

from app._windy_style import _css, _fold_handle_html, _pull_to_refresh_html, _pull_to_refresh_js


def test_css_contains_ptr_styles():
    css = _css(panel_open=True)
    assert ".insight-ptr" in css
    assert "insight-ptr-spin" in css
    assert "ptr-refreshing" in css
    assert "ptr-ready" in css


def test_pull_to_refresh_html_markup():
    html = _pull_to_refresh_html()
    assert 'id="insight-ptr"' in html
    assert 'class="insight-ptr-pill"' in html
    assert 'insight-ptr-icon' in html
    assert 'insight-ptr-spinner' in html
    assert "Pull to refresh" in html


def test_pull_to_refresh_js_logic():
    js = _pull_to_refresh_js()
    assert "initPullToRefresh" in js
    assert "touchstart" in js
    assert "touchmove" in js
    assert "touchend" in js
    assert "triggerRefresh" in js
    assert "run simulation" in js.lower()
