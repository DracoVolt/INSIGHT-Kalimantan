# Project report: IGNIS-Sim Kalimantan

## Problem

Peatland wildfires in Central Kalimantan can threaten rural communities, release
large amounts of carbon, and are influenced by wind, fuel, and peat conditions.
This project builds a small, transparent simulation that shows how fire can spread
through a 4 km × 4 km grid near Palangkaraya / Sebangau / Kahayan, and how
civilians can respond when simulated fire approaches a rural area.

## Question

Can a simple physics Cellular Automaton together with a baseline machine-learning
model predict where fire is likely to move next, and can the simulation suggest
timely mitigation actions for nearby civilians?

## Methods

### Data
- OpenStreetMap features for the demo bounding box: water, rivers, settlements,
  land cover context.
- NASA FIRMS wildfire hotspots (MODIS/VIIRS) for observed fire presence.
- A simplified wind direction treated as a public variable.
- Grid cells of about 4 km × 4 km over a 2° lon × 2° lat bounding box.

### Physics Cellular Automaton
- Each cell has a state: healthy, igniting, burning, burned, or peat_risk.
- A burning cell can ignite neighboring cells with a probability that depends on:
  - a base spread probability,
  - alignment with the wind direction,
  - whether the neighbor is a peat-risk cell.
- Peat-risk cells represent the special behavior of peatland fires.

### Machine learning
- A baseline classifier predicts whether a cell had a FIRMS hotspot on a given day.
- Features are explainable: recent hotspot history, wind alignment, distance to
  water and settlements, peat flag, and land cover context.

### Civilian mitigation
- A small rule set triggers mitigation advice when the CA predicts fire near a
  settlement or rural cell.
- Advice includes preparation, alerting neighbors, perimeter damping, avoiding
  peat-drying actions, and early evacuation.

## Results

In the demo:
- The CA spreads fire across the grid in a wind-influenced direction.
- The ML model ranks cells by predicted fire presence probability.
- Mitigation advice appears when simulated fire nears populated or rural cells.

## Limitations

- The CA is a teaching model, not an operational fire spread model.
- Wind and weather are simplified for the demo.
- FIRMS and OSM data may be incomplete for the bounding box.
- The ML model is a baseline classifier meant to be explained, not tuned.
- Civilian-mitigation guidance is illustrative only.

## What civilians can do

- Prepare early: review evacuation routes and keep communication available.
- Alert neighbors when fire approaches.
- Avoid actions that dry out peat, which can worsen fire spread.
- If fire nears a settlement, evacuate early and contact local authorities.

## Significance

This project shows that a high-school-scale science project can combine public
geospatial data, a simple physics model, and a baseline ML model to explore
wildfire risk and community mitigation in a peatland region.
