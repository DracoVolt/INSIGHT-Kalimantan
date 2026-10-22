# INSIGHT — Physics & ML Formula Reference Sheet

Project: INSIGHT (Integrated Surface Ignition & Flora Fauna Mapping Hazard Tracker)
Demo area: Central Kalimantan — Palangka Raya / Sebangau / Kahayan peatlands
Bounding box: 112.5°–114.5° E, 1.5°–3.5° S (~2° × 2°, ≈ 222 km × 222 km)
Grid spacing: 0.035° ≈ 4 km per cell (8-neighbor Moore neighborhood)

All formulas below match the values in `src/config.py` and the logic in
`src/ca.py`, so every number in this sheet can be traced back to code.

---

## 1. Cell size (geodesy)

Meters per degree of longitude shrinks with latitude:

    m_per_deg_lon = 111,000 × cos(|φ_mid|)

    φ_mid = (min_lat + max_lat) / 2 = 2.5° S
    m_per_deg_lat ≈ 111,000 m
    m_per_deg_lon ≈ 111,000 × cos(2.5°) ≈ 110,895 m

    Cell size (N–S) = 0.035° × 111,000    ≈ 3.9 km
    Cell size (E–W) = 0.035° × 110,895    ≈ 3.9 km

---

## 2. Wind alignment factor, W(θ)  — ∈ [0, 1]

For each burning cell S and neighbor N, compute the compass bearing of the
step S → N (row increases southward, col increases eastward):

    bearing(S→N) = atan2(Δcol, −Δrow), mapped to [0°, 360°)
    (0° = north, 90° = east)

Then measure how close that bearing is to the wind direction θ_wind
(meteorological convention: 0° = wind FROM north):

    diff = |bearing − θ_wind|, wrapped: if diff > 180°, diff = 360° − diff

    W(θ) = max(0, min(1, 1 − diff / 180))

Interpretation:
- W = 1 → neighbor lies exactly downwind (fire is blown toward it)
- W = 0.5 → neighbor lies perpendicular to the wind
- W = 0 → neighbor lies exactly upwind

---

## 3. Spread probability (CA transition rule)

A burning cell S ignites a burnable neighbor N with probability:

    P(S→N) = P_base + k_wind · W(θ) + k_peat · 𝟙[N is peat-risk]

with demo constants:

    P_base  = 0.15   (base ignition probability per step)
    k_wind  = 0.25   (wind alignment strength)
    k_peat  = 0.20   (peat flammability bonus, applied only to peat cells)

    P(S→N) is clamped to [0, 1]

Range of outcomes per neighbor, per step:

    Minimum (upwind, non-peat):  0.15
    Maximum (dead-downwind, peat): 0.15 + 0.25 + 0.20 = 0.60

So a peat cell directly downwind is 4× more likely to catch fire per step
than an upwind non-peat cell — wind and peat type together shape the
anisotropic fire front.

### Wind-weighted directional asymmetry

Because W varies linearly with angular difference, the front advances fastest
downwind. For a fixed step time Δt, the expected spread velocity in a direction
φ relative to the wind is approximately:

    v(φ) ∝ P_base + k_wind · max(0, 1 − |φ| / 180°)

This is the discrete analogue of a Huygens-type wavefront: each burning cell
is a point source, and the next front is the envelope of successful ignitions.

---

## 4. CA state update rules (one step, t → t+1)

Each cell holds one state: healthy, igniting, burning, burned, peat_risk.

    Rule 1 (burnout):    igniting, burning  →  burned
    Rule 2 (ignition):   healthy/peat_risk neighbor N of a burning cell S
                         becomes igniting with probability P(S→N) (Section 3)
    Rule 3 (fuel):       burned cells are not burnable — fire cannot re-enter
    Rule 4 (water):      water/inland-filtered cells are excluded from the
                         burnable surface entirely (inland-only grid)

Ignition draws are independent Bernoulli trials:

    N_ignites | burning neighbors ~ Binomial(n_burning_neighbors, max P)

Burning intensity is tracked as a monotone counter per cell:

    I(t+1) = I(t) + 1  for cells that burn out this step
    I = 0.5 for freshly igniting cells

---

## 5. Heat-transfer intuition (why the model is physical)

The CA abstracts the three classical heat-transfer modes into the spread
probability:

    Convection → captured by the wind term k_wind · W(θ):
                 hot plume tilts downwind, pre-heating fuel ahead of the front.

    Radiation  → captured by P_base: every burning neighbor radiates ~ σT⁴
                 (Stefan–Boltzmann) to nearby fuel regardless of direction.

    Conduction → negligible at 4 km cell scale; folded into P_base.

Peat bonus k_peat models higher fuel load and lower moisture of peat soils:
dry organic matter lowers the ignition energy required, so the same heat flux
produces a higher ignition probability.

---

## 6. Machine Learning layer (risk map → CA seeding)

A Random Forest classifier is trained on public spatial features per cell:

    Features: distance to nearest FIRMS hotspot (7-day history),
              distance to rivers / roads / settlements (OpenStreetMap),
              land-cover type (OSM tags), peat-risk flag

    Target:   whether the cell contained a confirmed hotspot

    Output:   r(cell) ∈ [0, 1] — predicted wildfire risk per cell

High-risk cells (r above threshold) are used to seed the CA with BURNING
cells, so the physics simulation starts from a statistically informed fire
map rather than arbitrary points. The pipeline is a hybrid:

    data → ML risk map → CA seeding → CA spread frames → mitigation alerts

---

## 7. Mitigation alert distance rule

A settlement cell triggers a mitigation popup when:

    d_grid(burning cell, settlement) ≤ R_alert = 2 cells   (~8 km)
    (with a wider "nearby rural area" radius R_rural = 3 cells ≈ 12 km)

Popups are filtered to the user's GPS position so only nearby settlements
raise alerts.

---

## 8. Symbol table

| Symbol   | Meaning                                        | Value / range   |
|----------|------------------------------------------------|-----------------|
| P_base   | Base spread probability per step               | 0.15            |
| k_wind   | Wind alignment strength                        | 0.25            |
| k_peat   | Peat flammability bonus                        | 0.20            |
| W(θ)     | Wind alignment factor                          | [0, 1]          |
| θ_wind   | Wind direction (meteorological, FROM)          | demo default 90°|
| r(cell)  | ML-predicted wildfire risk                     | [0, 1]          |
| Δ        | Grid spacing                                   | 0.035° ≈ 4 km   |
| R_alert  | Settlement alert radius                        | 2 cells ≈ 8 km  |

> Note: INSIGHT's CA is a teaching-grade model — transparent, re-runnable
> from one config file — not an operational fire spread model like Rothermel's.
> All parameters are demo-tuned, not field-calibrated.
