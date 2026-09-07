"""Top-level CA simulator facade.

This thin module re-exports the app-level simulator helpers so other packages can
import them without depending on `app` internals.
"""

from app.ca_simulator import (
    SimState,
    initialize_simulation,
    step_forward,
    state_distribution,
    mitigation_for,
    risk_at,
)

__all__ = [
    "SimState",
    "initialize_simulation",
    "step_forward",
    "state_distribution",
    "mitigation_for",
    "risk_at",
]
