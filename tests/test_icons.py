"""Tests for the user-editable flora/fauna map icons."""

from __future__ import annotations

import os

import pytest

from src.icons import bio_icon, icon_data_url, icon_path_for

TAXA = ("Orangutan", "Proboscis_monkey", "Rafflesia", "Nepenthes")


def test_every_taxon_has_an_icon_file():
    for key in TAXA:
        path = icon_path_for(key)
        assert path is not None, f"no icon resolved for {key}"
        assert os.path.exists(path), path


def test_unknown_taxon_falls_back_to_default():
    default = icon_path_for("default")
    assert default is not None
    assert icon_path_for("Sumatran_tiger") == default


def test_icon_is_embedded_as_data_uri():
    for key in TAXA:
        url = icon_data_url(key)
        assert url is not None and url.startswith("data:image/")


def test_custom_icon_builds_for_folium():
    pytest.importorskip("folium")
    assert bio_icon("Orangutan") is not None
