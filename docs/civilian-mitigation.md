# Civilian mitigation guidance

This document explains the rule set used in the demo to suggest civilian actions
when simulated fire approaches a rural area or settlement.

## Important disclaimer

This is a science-fair prototype. The mitigation guidance is illustrative only and
is not a substitute for local emergency advice, official warnings, or community
protocols.

## How risk is assessed

The demo looks at each settlement and rural cell and computes:
- distance to the nearest burning cell,
- distance to the nearest igniting cell,
- predicted fire risk from the ML model,
- current CA state of the cell.

Risk levels are:
- `none`: no nearby fire.
- `low`: fire is present in the region but not yet very close.
- `medium`: fire is approaching and may affect the area soon.
- `high`: fire is very close or already near the area.

## Actions by risk level

### Low risk
- Review evacuation routes and keep phones charged.
- Clear dry leaves and debris around homes if safe.

### Medium risk
- Alert neighbors to prepare and watch for smoke.
- Wet the perimeter if water is available and safe.
- Avoid actions that dry out peat, because dried peat can make fire spread worse.

### High risk
- Evacuate early, before roads become difficult.
- Contact local authorities or community leaders.
- If time allows, secure livestock and valuables before leaving.

## Why peat matters

The demo focuses on the Sebangau / Kahayan peatland forest area. Peat fires behave
differently from ordinary forest fires: drained or dry peat can burn for a long time
and can be hard to extinguish. That is why the demo includes a special peat-risk
flag and why the mitigation advice warns against actions that dry out peat.

## Using the demo

In the web app, mitigation advice appears for settlement and rural cells that are
near the simulated fire. The advice is meant to show the idea of timely community
response, not to prescribe exact actions for any real event.

## For the science fair

Be ready to explain:
- what triggers mitigation advice,
- why the advice changes with risk level,
- why peatland is treated specially,
- and that the advice is illustrative.
