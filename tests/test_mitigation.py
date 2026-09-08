"""Tests for the civilian-mitigation logic."""

from __future__ import annotations

import numpy as np
import pytest

from src.mitigation import (
    MitigationContext,
    RiskLevel,
    assess_risk,
    actions_for,
    format_actions_for_display,
)


def test_assess_risk_no_fire_is_none():
    ctx = MitigationContext(
        cell_row=0,
        cell_col=0,
        is_settlement=True,
        is_rural=False,
        distance_to_nearest_burning_cell=None,
        distance_to_nearest_igniting_cell=None,
        ca_state="healthy",
        predicted_risk=0.0,
        wind_dir_deg=0.0,
    )
    assert assess_risk(ctx) == RiskLevel.NONE


def test_assess_risk_burning_within_one_is_high():
    ctx = MitigationContext(
        cell_row=0,
        cell_col=0,
        is_settlement=True,
        is_rural=False,
        distance_to_nearest_burning_cell=1.0,
        distance_to_nearest_igniting_cell=None,
        ca_state="healthy",
        predicted_risk=0.0,
        wind_dir_deg=0.0,
    )
    assert assess_risk(ctx) == RiskLevel.HIGH


def test_assess_risk_igniting_within_two_is_high():
    ctx = MitigationContext(
        cell_row=0,
        cell_col=0,
        is_settlement=True,
        is_rural=False,
        distance_to_nearest_burning_cell=None,
        distance_to_nearest_igniting_cell=2.0,
        ca_state="healthy",
        predicted_risk=0.0,
        wind_dir_deg=0.0,
    )
    assert assess_risk(ctx) == RiskLevel.HIGH


def test_assess_risk_medium_when_burning_within_two():
    ctx = MitigationContext(
        cell_row=0,
        cell_col=0,
        is_settlement=True,
        is_rural=False,
        distance_to_nearest_burning_cell=2.0,
        distance_to_nearest_igniting_cell=None,
        ca_state="healthy",
        predicted_risk=0.0,
        wind_dir_deg=0.0,
    )
    assert assess_risk(ctx) == RiskLevel.MEDIUM


def test_assess_risk_high_predicted_risk():
    ctx = MitigationContext(
        cell_row=0,
        cell_col=0,
        is_settlement=False,
        is_rural=True,
        distance_to_nearest_burning_cell=None,
        distance_to_nearest_igniting_cell=None,
        ca_state="healthy",
        predicted_risk=0.6,
        wind_dir_deg=0.0,
    )
    assert assess_risk(ctx) == RiskLevel.HIGH


def test_actions_for_none_is_empty():
    ctx = MitigationContext(
        cell_row=0,
        cell_col=0,
        is_settlement=True,
        is_rural=False,
        distance_to_nearest_burning_cell=None,
        distance_to_nearest_igniting_cell=None,
        ca_state="healthy",
        predicted_risk=0.0,
        wind_dir_deg=0.0,
    )
    assert actions_for(ctx) == []


def test_format_actions_are_dicts():
    actions = format_actions_for_display([])
    assert isinstance(actions, list)
    for a in actions:
        assert isinstance(a, dict)
        assert "title" in a
        assert "description" in a
        assert "timing" in a
        assert "icon" in a


def test_mitigation_context_defaults():
    ctx = MitigationContext(
        cell_row=1,
        cell_col=2,
        is_settlement=True,
        is_rural=False,
        distance_to_nearest_burning_cell=None,
        distance_to_nearest_igniting_cell=None,
        ca_state="healthy",
        predicted_risk=0.0,
        wind_dir_deg=90.0,
    )
    assert ctx.cell_row == 1
    assert ctx.cell_col == 2
    assert ctx.is_settlement is True
    assert ctx.is_rural is False
