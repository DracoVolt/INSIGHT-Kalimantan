# Methods

## Overview

INSIGHT Kalimantan has three connected parts:

1. A grid over the demo bounding box.
2. A physics Cellular Automaton (CA) that moves fire through the grid.
3. A baseline machine-learning model that predicts which cells are most likely to
   have fire.

The grid also carries context from OpenStreetMap: water, settlements, and
peat-like areas.

## The grid

The bounding box is divided into equal square cells of about 4 km × 4 km. Each
cell has an index `(row, col)` and a center longitude/latitude.

The grid size is chosen so the project is small enough to run quickly and explain
clearly.

## The Cellular Automaton

The CA is the physics part of the project.

State per cell:
- `healthy`: not burning and not at special risk.
- `igniting`: about to burn.
- `burning`: actively spreading fire.
- `burned`: fire has passed.
- `peat_risk`: a peatland cell that behaves differently.

Update rule:
- Burning and igniting cells become `burned` after one step.
- A burning cell can ignite each neighboring cell with a probability:
  - base spread probability,
  - plus extra spread when the neighbor is downwind,
  - plus extra spread when the neighbor is peat-risk.

Wind direction is a public input variable, so the same setup can be shown with
different wind directions.

## Machine learning

The ML part predicts a simple yes/no question: did a FIRMS hotspot appear in this
cell on this day?

Features:
- recent hotspot history in the cell (1, 3 and 7 days, plus the 7-day count),
- distance to the nearest hotspot on the previous day,
- wind alignment of the cell,
- distance to the nearest water cell,
- distance to the nearest settlement cell,
- cell row and column,
- peat risk flag.

The baseline model is a random forest. The project holds out the last two FIRMS
days instead of splitting rows at random — otherwise the same cell appears on
both sides of the split and the metrics flatter the model — and reports
accuracy, precision, recall, ROC-AUC and PR-AUC so it can be discussed honestly.

## How the parts connect

- The ML model can inform which cells are likely to ignite.
- The CA shows how fire can spread from those cells under a given wind direction.
- The mitigation module watches the CA and ML outputs and suggests civilian
  actions when fire nears a settlement or rural cell.

## Why this is a science project, not a tool

The goal is explanation. Each part is kept simple so students can describe:

- what data was used,
- how the CA rule works,
- what the model predicts,
- where the model is weak,
- how civilians might respond.

## Limitations to mention

- Simplified physics.
- Simplified wind.
- Possible data gaps for the bounding box.
- Baseline-only ML model.
- Illustrative mitigation advice only.
