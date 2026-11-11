"""Unit tests for the Windy-style shell and pull-to-refresh feature."""

from __future__ import annotations

from app._windy_style import _css, _fold_handle_html, _pull_to_refresh_html, _pull_to_refresh_js


def test_fold_handles_include_left_and_right():
    html = _fold_handle_html()
    assert "insight-fold" in html
    assert "insight-fold-tab" in html
    assert "Controls" in html
    assert "insight-emergency-fold" in html
    assert "insight-emergency-fold-tab" in html
    assert "Emergency" in html


def test_css_contains_emergency_fold_styles():
    css = _css(panel_open=True)
    assert ".insight-emergency-fold-tab" in css
    assert "#insight-emergency-fold" in css
    assert ".st-key-emergency_panel" in css


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
