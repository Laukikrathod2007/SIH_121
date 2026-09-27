# SIH26121 — eRTMAC-NWIS
# MODULE 5 FINAL SPECIFICATION
## Physics-Based Real-Time Drilling Digital Twin + Live Telemetry + Predictive Risk Analytics + ML Training Methodology

**Problem Statement:** SIH26121  
**Organization:** Oil India Limited (OIL)  
**System:** eRTMAC-NWIS — Nearby Wells Intelligence System  
**Module:** 5 — Predictive Drilling Risk Analytics  
**Companion:** Module 4 — Geological, Drilling & Reservoir Correlation  

---

## 0. Document Status

This is the **final Module 5 implementation handoff**.

It defines:

- the purpose of Module 5,
- the live drilling simulator,
- the reduced-order physics engine,
- live telemetry architecture,
- sensor modelling,
- fault/scenario modelling,
- data sources,
- preprocessing,
- feature engineering,
- ML training,
- model validation,
- risk fusion,
- confidence and provenance,
- integration with Module 4,
- integration with Module 6,
- API contracts,
- database schema,
- frontend behaviour,
- testing,
- deployment,
- calibration,
- limitations,
- and a step-by-step implementation roadmap.

### Relationship to Module 4

The existing:

`SIH26121_Module_4_Research_and_Implementation_Plan.md`

remains the **Module 4 baseline**.

Do not replace Module 4 with this document.

Module 4 is responsible for:

```text
MD
 ↓
TVDSS
 ↓
formation identification
 ↓
stratigraphic ξ
 ↓
equivalent horizon in offset wells
 ↓
historical drilling evidence
```

Module 5 consumes that output and answers:

```text
What is happening in the current well?
What is abnormal?
What hazards are developing?
How strong is the evidence?
What does historical correlated behaviour say?
```

Module 6 then consumes Module 5 risk states and turns them into alerts/recommendations.

---

# 1. THE CORE IDEA

Module 5 is not a dashboard full of random moving gauges.

It is a **reduced-order, physics-informed real-time drilling digital twin**.

The digital twin maintains an internal simulated well state.

That state is transformed into sensor observations.

Those observations become telemetry.

Telemetry is processed into engineering features.

Features are combined with Module 4 geological context and historical offset evidence.

The final output is hazard-specific risk with evidence and confidence.

The core chain is:

```text
FORMATION + WELL + OPERATOR INPUTS
                |
                v
       PHYSICS STATE SOLVER
                |
                v
          SENSOR MODEL
                |
                v
        LIVE TELEMETRY BUS
                |
                v
       FEATURE EXTRACTION
                |
        +-------+--------+
        |                |
        v                v
 STATISTICAL         PHYSICS / RULE
 ANOMALY MODELS       CHECKS
        |                |
        +-------+--------+
                |
                v
       MODULE 4 CONTEXT
   formation + TVDSS + ξ +
   correlated offset history
                |
                v
        HAZARD ENGINES
                |
        +-------+--------+---------+---------+
        |                |         |         |
        v                v         v         v
       LC               SP       KICK   TORQUE/DRAG
                |
                v
            CEMENT
                |
                v
          RISK FUSION
                |
       +--------+---------+
       |                  |
       v                  v
   RISK STATE         CONFIDENCE
       |                  |
       +--------+---------+
                |
                v
            MODULE 6
                |
                v
            MODULE 7
```

---

# 2. WHAT MODULE 5 MUST NOT BE

The following is explicitly prohibited as the core implementation:

```python
flow_out = random.uniform(...)
torque = random.uniform(...)
rop = random.uniform(...)
risk = random.uniform(...)
```

or:

```python
if scenario == "loss":
    flow_out -= 300
```

or:

```python
risk = random.choice([0.2, 0.4, 0.8])
```

Those mechanisms can create visual movement but do not create a causal drilling model.

The simulator must instead modify **physical/engineering parameters**, and telemetry must emerge from the resulting state.

For example:

```text
BHP > fracture pressure
        |
        v
formation leakoff starts
        |
        v
Q_loss increases
        |
        v
return flow falls
        |
        v
pit volume falls
        |
        v
flow imbalance becomes abnormal
        |
        v
Module 5 raises Lost Circulation risk
```

That is the required design philosophy.

---

# 3. WHY WE NEED OUR OWN PHYSICS ENGINE

The availability of public OIL drilling data is not guaranteed.

The production problem requires OIL-controlled information such as DDRs, WCRs, mud reports, Drillwatch data and eventually real-time telemetry, but the development prototype cannot assume that all OIL historical records are openly downloadable.

Therefore we need two complementary development assets:

### A. Real public data

Used to learn what real drilling telemetry looks like.

Candidate sources include:

- Equinor Volve,
- FORCE 2020 / NCS datasets,
- other legitimate public drilling datasets.

### B. Our own physics-generated data

Used to create controlled labelled cases:

- normal drilling,
- lost circulation,
- kick / overpressure,
- stuck pipe,
- stick-slip,
- washout,
- poor hole cleaning,
- sensor failures.

The simulator gives us ground truth because the injected scenario is known.

---

# 4. DATA PROVENANCE POLICY

Every dataset and record must carry a provenance class.

## 4.1 OBSERVED

Measured/generated by a real operational system.

Examples:

```text
Volve WITSML telemetry
Volve well logs
Volve reports
future authorized OIL telemetry
future authorized OIL DDR/WCR data
```

## 4.2 SYNTHETIC

Generated by our simulator.

Examples:

```text
NWIS_PHYSICS_SIMULATOR
NORMAL
LOST_CIRCULATION
KICK
STUCK_PIPE
STICK_SLIP
WASHOUT
```

## 4.3 INFERRED

Derived from source material or neighbouring data.

Examples:

```text
formation inferred from DDR remarks
formation top imputed from neighbouring wells
historical risk class derived from textual evidence
```

Every dataset must preserve:

```text
source
source_id
source_type
provenance_class
processing_version
timestamp
```

Never call synthetic data "OIL data".

Never call public Volve data "Upper Assam data".

Never claim an OIL-trained model until OIL data has actually been authorized, received, processed and used for training.

---

# 5. PUBLIC DEVELOPMENT DATA

## 5.1 Volve

Equinor has officially released the Volve field dataset for research, study and development. The release contains approximately 40,000 files and includes subsurface and operating data.

Volve is particularly useful because the ecosystem includes time/depth-oriented drilling information, well information and reports, making it valuable for testing an integrated data pipeline.

Official source:

https://www.equinor.com/energy/volve-data-sharing

Use Volve for:

```text
telemetry pipeline testing
real drilling distributions
time-series preprocessing
well segmentation
feature engineering
normal-operation modelling
pipeline validation
```

Do not use Volve to claim geological equivalence with Upper Assam.

---

## 5.2 FORCE 2020 / NCS

Use legitimate FORCE/NCS public well datasets where licensing permits.

Potential uses:

```text
well logs
formation/lithology context
well depth relationships
well-to-well similarity
rock-property features
geological model development
```

The main purpose is to complement telemetry datasets with better geological/log context.

---

# 6. OIL / DGH DATA LATER

The production system should support authorized OIL/NDR data when provided.

Potential production inputs:

```text
DDR
WCR
Daily mud reports
Deviation surveys
Drillwatch
MWD/LWD
mud logging
formation tops
casing
cementing
well tests
formation pressure
historical NPT
real-time eRTMAC telemetry
```

Production workflow:

```text
authorized OIL data
        |
        v
ingestion
        |
        v
normalization
        |
        v
Module 1 extraction
        |
        v
Module 4 correlation
        |
        v
Module 5 calibration/training
```

---

# 7. WITSML TARGET INTERFACE

WITSML is the key interoperability concept for the telemetry layer.

Energistics documentation describes WITSML as a standard for exchanging well and well-related operational data, including drilling and mud-logging information.

WITSML Log objects can represent measurements indexed by time or depth, and drilling channels can include values such as:

```text
ROP
RPM
WOB
pressure
temperature
```

Trajectory data represents directional survey stations and can include:

```text
MD
inclination
azimuth
TVD
north/south displacement
east/west displacement
```

Official references:

https://docs.energistics.org/WITSML/WITSML_TOPICS/WITSML-000-002-0-C-sv2000.html

https://docs.energistics.org/WITSML/WITSML_TOPICS/WITSML-000-048-0-C-sv2000.html

https://docs.energistics.org/WITSML/WITSML_TOPICS/WITSML-000-039-0-C-sv2000.html

https://docs.energistics.org/WITSML/WITSML_TOPICS/WITSML-000-030-0-C-sv2000.html

The key architectural idea is:

```text
SIMULATOR TELEMETRY
        |
        +---- same internal canonical schema ----+
                                                 |
REAL WITSML TELEMETRY --------------------------+
                                                 |
                                                 v
                                           MODULE 5
```

Module 5 should not know whether its upstream source is:

```text
SIMULATOR
Volve
OIL WITSML
another approved telemetry adapter
```

---

# 8. PHYSICS ENGINE OBJECTIVE

The physics engine is a reduced-order solver.

It should model enough physics to produce:

```text
realistic relationships
causal telemetry
fault signatures
parameter sensitivity
operator-response behaviour
```

It does NOT need to reproduce a commercial high-fidelity drilling simulator.

The main subsystems are:

```text
1. formation model
2. trajectory / geometry
3. drilling mechanics
4. hydraulics
5. pressure interaction
6. drillstring mechanics
7. cuttings / hole cleaning
8. fault/scenario engine
9. sensor model
10. telemetry transport
```

---

# 9. GLOBAL SIMULATION STATE

The simulator maintains an internal state object.

Example:

```python
state = {
    "time": 0.0,

    "md": 3200.0,
    "tvdss": 2986.0,

    "formation": "Barail Lower Sand",

    "rpm": 110.0,
    "wob": 85.0,
    "rop": 14.2,

    "torque": 18.3,
    "hookload": 105.0,

    "flow_in": 2100.0,
    "flow_out": 2090.0,

    "standpipe_pressure": 155.0,
    "annular_pressure": 48.0,

    "pit_volume": 80.0,
    "mud_weight": 1.31,
    "ecd": 1.38,

    "mse": 0.0,
    "d_exponent": 0.0,

    "cuttings_concentration": 0.0,

    "borehole_pressure": 0.0,

    "stick_slip_index": 0.0
}
```

The state is the simulator's internal ground truth.

The sensor layer does not expose this directly.

---

# 10. TIME REPRESENTATION

Use simulation time independently from wall-clock time.

```text
simulation_time
wall_clock_time
```

The simulator should support:

```text
1x speed
2x speed
5x speed
10x speed
```

for demonstrations.

Example:

```text
10 simulated minutes
=
60 real seconds
```

when running at 10x.

Do not modify physical equations when changing playback speed.

Only the scheduler changes.

---

# 11. SIMULATION TIMESTEPS

Recommended V1:

```text
physics timestep:        50–100 ms
physics update rate:     10–20 Hz

telemetry rate:          5–10 Hz

database persistence:    1–2 Hz or batched

frontend rendering:      approximately 5–10 Hz
```

The physics solver can run at 20 Hz while the browser receives 5–10 Hz.

This avoids overloading the frontend.

---

# 12. FORMATION MODEL

The geology model describes the underground environment.

Minimum V1 representation:

```json
{
  "formations": [
    {
      "name": "Tipam Sandstone",
      "top_tvdss": 1400,
      "base_tvdss": 2200,
      "rock_density_gcc": 2.25,
      "ucs_mpa": 35,
      "youngs_modulus_gpa": 8,
      "poisson_ratio": 0.25,
      "porosity": 0.18,
      "permeability_md": 120,
      "pore_pressure_gcc": 1.00,
      "fracture_gradient_gcc": 1.55,
      "friction_coefficient": 0.25,
      "leakoff_coefficient": 0.02
    }
  ]
}
```

These values are demo parameters unless supported by a real source.

---

# 13. FORMATION PROPERTIES

Each formation can include:

```text
top_tvdss
base_tvdss
thickness

rock_density
UCS
Young's modulus
Poisson ratio

porosity
permeability

pore pressure
fracture gradient

friction coefficient
leakoff coefficient
drillability coefficient
```

The active formation is found using:

```text
current TVDSS
```

and not only MD.

---

# 14. MODULE 4 CONNECTION

Module 5 must consume Module 4's:

```text
current formation
current TVDSS
current xi
relevant offset wells
Omega / offset relevance
historical NPT events
historical evidence
formation confidence
correlation confidence
```

Example contract:

```json
{
  "active_well_id": "NHK-412",
  "md": 3200.0,
  "tvdss": 2986.0,
  "formation": "Barail Lower Sand",
  "xi": 0.105,
  "correlation_confidence": 0.91,
  "offsets": [
    {
      "well_id": "NHK-089",
      "omega": 0.87,
      "equivalent_tvdss": 3228,
      "events": [
        {
          "type": "LOST_CIRCULATION",
          "severity": 4
        }
      ]
    }
  ]
}
```

Module 5 does not recompute the geological correlation differently.

It consumes the authoritative correlation service.

---

# 15. TRAJECTORY MODEL

The simulator uses:

```text
MD
inclination
azimuth
```

to establish the well path.

The trajectory model should be compatible with Module 4's minimum-curvature implementation.

Maintain:

```text
MD
TVD
TVDSS
North
East
inclination
azimuth
dogleg severity
```

---

# 16. DEPTH EVOLUTION

The fundamental relationship is:

```text
dMD/dt = ROP
```

So:

```python
state.md += state.rop * dt
```

Then:

```text
MD
 ↓
trajectory
 ↓
TVDSS
 ↓
formation
 ↓
formation properties
```

This means the bit physically progresses into new geological intervals.

---

# 17. ROP MODEL

ROP = Rate of Penetration.

Use a reduced-order model:

```text
ROP =
alpha(formation, bit)
*
RPM
*
(WOB / Db)^b
*
formation_factor
*
dysfunction_factor
```

Where:

```text
alpha
b
```

are calibratable parameters.

Add physical saturation so ROP does not grow infinitely with WOB/RPM.

Behaviour should be:

```text
WOB ↑ -> ROP generally ↑
RPM ↑ -> ROP generally ↑
rock strength ↑ -> ROP generally ↓
```

The model should support field-specific calibration later.

---

# 18. DRILLING MECHANICS

The mechanics layer couples:

```text
WOB
RPM
rock strength
bit condition
ROP
torque
MSE
```

The key principle is:

```text
formation state
      |
      v
rock-cutting requirement
      |
      +--> ROP
      +--> torque
      +--> MSE
```

No gauge should be independent when there is a physical reason for coupling.

---

# 19. MSE

MSE = Mechanical Specific Energy.

A simplified formulation:

```text
MSE =
WOB / Ab
+
(T * omega) / (Ab * ROP)
```

where:

```text
Ab = bit area
T = torque
omega = angular velocity
ROP = rate of penetration
```

MSE should be used to detect:

```text
inefficient drilling
formation changes
bit dysfunction
abnormal mechanical energy
```

MSE is not itself a hazard label.

---

# 20. HYDRAULICS MODEL

Hydraulic path:

```text
pump
  |
  v
drillpipe
  |
  v
BHA
  |
  v
bit nozzles
  |
  v
annulus
  |
  v
surface returns
```

Required outputs:

```text
flow velocity
hydrostatic pressure
friction losses
bit pressure drop
standpipe pressure
annular pressure
bottomhole pressure
ECD
```

---

# 21. FLOW VELOCITY

For flow through area A:

```text
v = Q / A
```

Simplified annular area:

```text
A_annulus =
(pi / 4) * (Dh^2 - Dp^2)
```

Then:

```text
v_annulus =
Q / A_annulus
```

Use consistent units internally.

---

# 22. HYDROSTATIC PRESSURE

Approximate:

```text
Ph = rho * g * h
```

where:

```text
rho = mud density
g = gravity
h = vertical depth
```

Use TVD/TVDSS-aware geometry, not raw MD as the vertical height.

---

# 23. FRICTIONAL PRESSURE LOSS

V1 approximation:

```text
deltaP_f =
f * (L / Dh) * (rho * v^2 / 2)
```

where:

```text
f = friction factor
L = flow length
Dh = hydraulic diameter
rho = fluid density
v = flow velocity
```

V2 can support:

```text
Bingham
Power-law
Herschel-Bulkley
temperature correction
transient hydraulics
```

---

# 24. STANDPIPE PRESSURE

Approximate:

```text
SPP =
deltaP_pipe
+
deltaP_BHA
+
deltaP_bit
```

with:

```text
deltaP_bit = K * Q^2
```

Therefore:

```text
pump rate ↑
    |
    v
velocity ↑
    |
    v
friction ↑
    |
    v
SPP ↑
```

---

# 25. BOTTOMHOLE PRESSURE

A reduced-order approximation:

```text
BHP =
hydrostatic pressure
+
annular friction
+
surface pressure contribution
```

Use a consistent pressure datum.

This BHP is the key variable connecting hydraulics to formation pressure.

---

# 26. ECD

ECD = Equivalent Circulating Density.

Conceptually:

```text
ECD converts the effective circulating pressure
at depth into an equivalent density.
```

Approximation:

```text
rho_ECD =
P_effective_bottomhole / (g * TVD)
```

The implementation must document the exact pressure datum and unit conversion.

---

# 27. PORE PRESSURE

The formation model provides:

```text
P_pore(depth)
```

For V1, this can be a piecewise depth/formation function.

Example:

```text
Tipam:
    normal / depleted profile

Barail:
    near-normal / elevated profile

Kopili:
    potentially overpressured profile
```

Do not hard-code real field claims without a credible source.

---

# 28. FRACTURE PRESSURE

The formation model similarly provides:

```text
P_fracture(depth)
```

The simulator then calculates:

```text
PP_margin = BHP - P_pore

FG_margin = P_fracture - BHP
```

Interpretation:

```text
BHP below Pore Pressure
    -> influx / underbalance condition

BHP near Pore Pressure
    -> reduced kick margin

BHP near Fracture Pressure
    -> reduced loss margin

BHP above Fracture Pressure
    -> loss initiation is possible
```

These are model states, not automatic operational instructions.

---

# 29. LOST CIRCULATION PHYSICS

Do not manually reduce flow-out.

Use a formation acceptance/loss process.

Reduced-order formulation:

```text
if BHP > P_fracture:

    Q_loss =
        C_loss
        *
        (BHP - P_fracture)^n

else:

    Q_loss = 0
```

Then:

```text
Q_return =
Q_in
-
Q_loss
+
Q_influx
```

This produces the expected chain:

```text
BHP > fracture pressure
        |
        v
formation loss
        |
        v
Q_loss increases
        |
        +--> flow-out falls
        +--> pit volume falls
        +--> negative flow imbalance
```

---

# 30. KICK / FORMATION INFLUX PHYSICS

For a reduced-order influx model:

```text
if P_pore > BHP:

    Q_influx =
        PI
        *
        (P_pore - BHP)

else:

    Q_influx = 0
```

where:

```text
PI = effective formation influx coefficient
```

Then:

```text
Pore pressure > BHP
        |
        v
formation fluid enters
        |
        +--> flow-out rises
        +--> pit volume rises
        +--> pressure behaviour changes
```

---

# 31. PIT / FLUID BALANCE

Use:

```text
dVpit/dt =
Q_in
+
Q_influx
-
Q_out
-
Q_loss
```

This becomes one of the most important telemetry equations.

### Loss:

```text
Q_loss > 0
=> Vpit falls
```

### Kick:

```text
Q_influx > 0
=> Vpit rises
```

This provides a physically causal pit-volume signal.

---

# 32. DRILLSTRING MODEL

Represent the drillstring as segments:

```text
surface
 |
 +-- drill pipe
 +-- drill pipe
 +-- HWDP
 +-- drill collars
 +-- BHA
 +-- bit
```

Each segment can have:

```text
length
OD
ID
mass
density
axial stiffness
torsional stiffness
friction coefficient
```

V1 may use a lumped approximation.

V2 should use segmented mechanics.

---

# 33. TORQUE

Torque should respond to:

```text
WOB
rock strength
bit-rock interaction
RPM
friction
drillstring torsion
```

The relationship is coupled to:

```text
MSE
ROP
rock properties
```

Do not generate torque separately from these quantities.

---

# 34. TORQUE & DRAG

V1 friction:

```text
F_friction = mu * N
```

Torque contribution:

```text
T_friction = F_friction * r
```

where:

```text
mu = friction coefficient
N = normal contact force
r = effective radius
```

Accumulate along the drillstring.

---

# 35. TORSIONAL DYNAMICS

Use a reduced-order spring-damper model:

```text
I * theta_ddot
+
c * theta_dot
+
k * theta
=
T_surface - T_bit
```

where:

```text
I = rotational inertia
c = damping
k = torsional stiffness
theta = twist angle
```

Add nonlinear static/dynamic bit friction to create stick-slip behaviour.

---

# 36. STICK-SLIP

Desired simulated response:

```text
surface RPM roughly constant
       |
       v
bit slows down
       |
       v
torsional energy accumulates
       |
       v
bit breaks loose
       |
       v
bit accelerates
       |
       v
RPM oscillates
```

Telemetry should therefore show:

```text
bit RPM oscillation
torque oscillation
possible surface RPM response
```

rather than a manually animated sine wave.

---

# 37. HOLE CLEANING

Approximate cuttings generation:

```text
cuttings_generation
    ~
bit_area * ROP
```

Apply formation / porosity corrections.

Then estimate:

```text
annular solids concentration
```

Conceptual chain:

```text
ROP ↑
  |
  v
cuttings generation ↑
  |
  v
if annular transport is insufficient
  |
  v
cuttings concentration ↑
  |
  v
drag ↑
  |
  v
torque ↑
  |
  v
stuck-pipe risk ↑
```

---

# 38. FAULT ENGINE

Faults are parameter perturbations.

Supported scenarios:

```text
NORMAL
LOST_CIRCULATION
KICK_OVERPRESSURE
STUCK_PIPE
STICK_SLIP
WASHOUT
POOR_HOLE_CLEANING
SENSOR_FAULT
```

A scenario contains:

```text
scenario_id
start_condition
duration
target_interval
parameter_multipliers
severity
ground_truth_label
```

---

# 39. SCENARIO EXAMPLE — LOST CIRCULATION

```json
{
  "scenario": "LOST_CIRCULATION",
  "start_depth_tvdss": 3230,
  "parameters": {
    "leakoff_multiplier": 4.0
  }
}
```

Do not change flow-out directly.

Instead:

```text
leakoff coefficient increases
        |
        v
BHP exceeds fracture margin
        |
        v
Q_loss develops
        |
        v
flow-out changes
        |
        v
pit balance changes
```

---

# 40. SCENARIO EXAMPLE — KICK

```json
{
  "scenario": "KICK_OVERPRESSURE",
  "start_depth_tvdss": 3060,
  "parameters": {
    "pore_pressure_multiplier": 1.12,
    "influx_coefficient_multiplier": 3.0
  }
}
```

Result:

```text
Ppore > BHP
        |
        v
Qinflux > 0
        |
        v
pit gain
        |
        v
flow imbalance
        |
        v
kick features
```

---

# 41. SCENARIO EXAMPLE — STUCK PIPE

```json
{
  "scenario": "STUCK_PIPE",
  "start_depth_tvdss": 3120,
  "parameters": {
    "friction_multiplier": 2.5,
    "cuttings_buildup_multiplier": 2.0
  }
}
```

Result:

```text
friction ↑
+
cuttings accumulation ↑
        |
        v
drag ↑
        |
        v
torque ↑
        |
        v
overpull ↑
        |
        v
ROP ↓
```

---

# 42. SCENARIO EXAMPLE — STICK-SLIP

```json
{
  "scenario": "STICK_SLIP",
  "start_depth_tvdss": 3180,
  "parameters": {
    "torsional_damping_multiplier": 0.5,
    "static_bit_friction_multiplier": 1.5
  }
}
```

Result:

```text
torsional energy accumulation
        |
        v
periodic release
        |
        v
RPM oscillation
+
torque oscillation
```

---

# 43. SCENARIO EXAMPLE — WASHOUT

A washout should modify a hydraulic restriction.

Example state effect:

```text
effective flow area changes
or
hydraulic leakage path opens
```

Then derive:

```text
SPP response
flow response
pressure distribution
```

The scenario should be physically coupled to telemetry.

---

# 44. SENSOR MODEL

The physics state is the internal truth.

The telemetry layer observes it.

Use:

```text
measurement =
scale * true_value(t - delay)
+
bias
+
noise
```

Optional terms:

```text
drift
quantization
dropout
outlier
saturation
```

Each sensor configuration includes:

```text
sampling_frequency
latency
noise_sigma
bias
drift_rate
min
max
resolution
dropout_rate
```

---

# 45. SENSOR QUALITY

Every telemetry sample should have:

```text
value
unit
timestamp
quality
source
```

Example:

```json
{
  "channel": "flow_out",
  "value": 1982.0,
  "unit": "L/min",
  "timestamp": "2026-09-28T01:00:02.200+05:30",
  "quality": 0.97,
  "source": "NWIS_SIMULATOR"
}
```

---

# 46. TELEMETRY CHANNELS

Minimum V1:

| Channel | Unit | Type |
|---|---|---|
| MD | m | depth |
| TVDSS | m | depth |
| ROP | m/hr | drilling |
| RPM | rpm | drilling |
| WOB | kN | drilling |
| Torque | kN·m | drilling |
| Hookload | kN | mechanical |
| Flow In | L/min | hydraulic |
| Flow Out | L/min | hydraulic |
| Standpipe Pressure | bar | hydraulic |
| Annular Pressure | bar | hydraulic |
| Pit Volume | m³ | fluid balance |
| Mud Weight | g/cc | fluid |
| ECD | g/cc | pressure |
| MSE | MPa | derived |
| d-exponent | dimensionless | derived |
| Inclination | deg | trajectory |
| Azimuth | deg | trajectory |
| Temperature | °C | environment/fluid |

---

# 47. TELEMETRY ENVELOPE

Canonical message:

```json
{
  "well_id": "NHK-SIM-001",
  "wellbore_id": "NHK-SIM-001-A",
  "sequence": 123456,
  "timestamp": "2026-09-28T01:00:02.200Z",
  "simulation_time": 1422.2,

  "depth": {
    "md_m": 3218.4,
    "tvdss_m": 3012.8
  },

  "formation": {
    "name": "Tipam Sandstone",
    "xi": 0.63
  },

  "channels": {
    "rpm": 110.2,
    "wob_kn": 85.4,
    "rop_mph": 14.1,
    "torque_knm": 18.3,
    "hookload_kn": 105.2,
    "flow_in_lpm": 2100.0,
    "flow_out_lpm": 2089.0,
    "standpipe_pressure_bar": 155.3,
    "annular_pressure_bar": 48.2,
    "pit_volume_m3": 80.2,
    "mud_weight_gcc": 1.31,
    "ecd_gcc": 1.36
  },

  "quality": {
    "overall": 0.97
  },

  "provenance": {
    "source": "NWIS_SIMULATOR",
    "class": "SYNTHETIC"
  }
}
```

---

# 48. TELEMETRY BUS

```text
PHYSICS ENGINE
      |
      v
TELEMETRY ADAPTER
      |
      v
MESSAGE BUS
      |
  +---+---+------------------+
  |       |                  |
  v       v                  v
WebSocket Historian        Module 5
  |                          |
  v                          v
Dashboard                Risk Engine
```

For MVP:

```text
FastAPI
WebSocket
Redis Streams or simple event queue
PostgreSQL/Timescale-compatible storage if available
```

The simulator should not be tightly coupled to the frontend.

---

# 49. TIME / DEPTH INDEXING

Telemetry has two important axes:

```text
time
depth
```

Some channels are naturally time-indexed.

Some are depth-indexed.

The canonical record must preserve both whenever possible:

```text
timestamp
MD
TVDSS
```

This is critical for synchronizing:

```text
surface sensors
downhole sensors
trajectory
formation intervals
events
```

---

# 50. RESAMPLING

Historical datasets will have mixed sampling intervals.

Example:

```text
RPM: 1 Hz
ROP: 5 Hz
WOB: 10 Hz
pit: 0.5 Hz
```

Choose canonical analysis intervals.

V1 recommendation:

```text
1-second feature grid
```

Store raw data separately.

Pipeline:

```text
raw telemetry
    |
    v
timestamp normalization
    |
    v
resample / aggregate
    |
    v
aligned feature frame
```

For each channel define the correct aggregation:

```text
mean
median
min
max
last value
sum
integral
```

Do not blindly average counters or event quantities.

---

# 51. UNIT NORMALIZATION

Internally use a single canonical unit system.

Recommended:

```text
distance: m
time: s
pressure: Pa internally / bar at API boundary
flow: m3/s internally / L/min at display boundary
density: kg/m3 internally / g/cc at display boundary
force: N internally / kN at UI
torque: N.m internally / kN.m at UI
ROP: m/s internally / m/hr at UI
RPM: rev/min
angle: degrees for UI; radians in mathematical functions
```

Convert at ingestion and output boundaries.

Never mix g/cc and kg/m3 without explicit conversion.

---

# 52. DATA CLEANING — CORE PIPELINE

```text
RAW
 |
 v
schema validation
 |
 v
timestamp normalization
 |
 v
unit normalization
 |
 v
duplicate removal
 |
 v
range validation
 |
 v
missing-value handling
 |
 v
outlier treatment
 |
 v
sensor-quality tagging
 |
 v
resampling
 |
 v
depth alignment
 |
 v
feature derivation
 |
 v
label generation
 |
 v
training dataset
```

Never silently overwrite raw data.

Maintain:

```text
raw
cleaned
derived
```

as separate logical layers.

---

# 53. TIMESTAMP PREPROCESSING

Steps:

```text
1. parse all timestamps
2. convert to UTC internally
3. preserve original timezone metadata
4. sort
5. remove impossible timestamps
6. detect clock resets
7. calculate time delta
8. detect duplicate sequence numbers
```

Never train on unsorted telemetry.

---

# 54. DUPLICATE HANDLING

Duplicate record rules:

```text
same well
same timestamp
same channel
same sequence
```

Possible actions:

```text
prefer highest quality
prefer latest update
merge if explicitly documented
```

Never randomly select duplicates.

---

# 55. RANGE VALIDATION

Every channel gets engineering sanity ranges.

Example only:

```text
RPM >= 0
WOB >= 0
ROP >= 0
pit volume >= 0
mud weight > 0
flow rates >= 0
```

Upper limits must be dataset-specific and configurable.

If a value is outside a plausible range:

```text
do not automatically delete it
```

Instead:

```text
flag quality = BAD
```

because the outlier itself may be diagnostically meaningful.

---

# 56. MISSING DATA

Missing telemetry must be handled according to channel semantics.

Options:

```text
forward fill
linear interpolation
short-gap interpolation
rolling median
model-based imputation
missing indicator
```

For safety-relevant channels:

```text
long gaps should remain missing
```

Do not manufacture false certainty.

Every imputed value should carry:

```text
is_imputed = true
imputation_method
imputation_distance
```

---

# 57. OUTLIER HANDLING

Use a layered method:

```text
engineering bounds
+
rate-of-change checks
+
rolling statistics
+
domain-specific persistence
```

Do not remove all spikes.

A spike may be the hazard.

Instead create:

```text
raw_value
clean_value
outlier_flag
```

This allows Module 5 to use both:

```text
measurement
+
data-quality context
```

---

# 58. DEPTH ALIGNMENT

Historical events may be stored in:

```text
MD
TVD
TVDSS
```

The canonical representation for correlation should use Module 4's normalized coordinate system.

Pipeline:

```text
historical MD
    |
    v
trajectory
    |
    v
TVDSS
    |
    v
formation
    |
    v
xi
```

This prevents raw-depth comparison from becoming the final model input.

---

# 59. TIME-DEPTH SYNCHRONIZATION

Some drilling parameters are recorded at time.

Formation context is depth-derived.

Therefore:

```text
timestamp
       +
MD
       +
TVDSS
       +
formation
       +
xi
```

must be available at the model feature timestamp.

The preprocessing engine should maintain:

```text
current depth
depth derivative
current formation
current xi
distance to formation boundary
```

---

# 60. FEATURE ENGINE — PRINCIPLE

Raw telemetry becomes engineering features.

The model should learn from:

```text
raw channels
+
rolling statistics
+
rates of change
+
physical margins
+
historical context
```

rather than only raw values.

---

# 61. FLOW FEATURES

Calculate:

```text
delta_flow =
flow_out - flow_in

absolute_flow_imbalance =
abs(flow_out - flow_in)

rolling_mean_delta_flow
rolling_std_delta_flow
flow_imbalance_duration
flow_imbalance_slope
flow_out_slope
flow_in_slope
```

---

# 62. PIT FEATURES

```text
pit_volume
pit_volume_slope
pit_volume_acceleration
rolling_pit_change
pit_gain
pit_loss
time_since_last_pit_change
```

---

# 63. PRESSURE FEATURES

```text
SPP
SPP_slope
annular_pressure
annular_pressure_slope
BHP
ECD

PP_margin
FG_margin

distance_to_pore_pressure
distance_to_fracture_pressure
```

---

# 64. TORQUE FEATURES

```text
torque
rolling_torque_mean
rolling_torque_std
torque_slope
torque_spike_count
torque_oscillation_amplitude
torque_frequency_features
```

---

# 65. RPM FEATURES

```text
RPM
RPM_mean
RPM_std
RPM_slope
bit_RPM
surface_RPM
RPM_difference
RPM_oscillation
```

---

# 66. WOB / HOOKLOAD FEATURES

```text
WOB
WOB_mean
WOB_slope
hookload
hookload_slope
overpull
overpull_slope
```

---

# 67. ROP FEATURES

```text
ROP
ROP_mean
ROP_std
ROP_slope
ROP_change
ROP_drilling_break_score
```

A drilling break is a derived anomaly, not an automatic kick label.

---

# 68. MSE FEATURES

```text
MSE
MSE_rolling_mean
MSE_rolling_std
MSE_baseline
MSE_deviation
MSE_zscore
```

---

# 69. D-EXPONENT FEATURES

Where sufficient data exists:

```text
d_exponent
d_exponent_baseline
d_exponent_deviation
d_exponent_slope
```

Treat this as an engineering-derived feature.

Do not claim that d-exponent alone proves overpressure.

---

# 70. HOLE-CLEANING FEATURES

```text
cuttings_generation_rate
annular_velocity
cuttings_concentration
cuttings_bed_estimate
transport_margin
```

---

# 71. GEOLOGICAL FEATURES FROM MODULE 4

```text
formation
formation_id
xi

distance_to_formation_top
distance_to_formation_base

correlation_confidence
formation_confidence

number_of_relevant_offsets
```

---

# 72. HISTORICAL EVIDENCE FEATURES

From Module 4:

```text
historical_LC_count
historical_SP_count
historical_kick_count
historical_torque_count
historical_cement_failure_count

historical_LC_severity
historical_SP_severity
historical_kick_severity

historical_event_xi_distance
```

Also:

```text
number_of_offset_wells
number_of_wells_with_matching_event
event_frequency
```

---

# 73. DATA QUALITY FEATURES

Every model input should be able to see quality information.

Examples:

```text
flow_in_quality
flow_out_quality
pressure_quality
torque_quality
overall_telemetry_quality
missing_ratio_30s
missing_ratio_5m
number_of_bad_channels
```

---

# 74. HAZARD 1 — LOST CIRCULATION

## Question

> Is the current well entering or developing a fluid-loss condition?

Inputs:

```text
flow imbalance
pit decline
BHP
fracture margin
mud weight
ECD
formation
historical LC evidence
```

---

# 75. LOST CIRCULATION LOGIC

Multi-signal concept:

```text
negative flow balance
+
persistent pit decline
+
small/negative fracture margin
+
historical LC at similar ξ
=
strong LC evidence
```

Do not trigger on one sample.

Use:

```text
persistence window
```

for example:

```text
5–60 seconds depending on signal frequency
```

with configurable thresholds.

---

# 76. LOST CIRCULATION FEATURE VECTOR

Example:

```json
{
  "delta_flow": -130,
  "delta_flow_5m_mean": -92,
  "pit_volume_slope": -0.08,
  "fg_margin": -0.01,
  "ecd_gcc": 1.55,
  "historical_lc_count": 2,
  "historical_lc_xi_distance": 0.04,
  "telemetry_quality": 0.96
}
```

---

# 77. HAZARD 2 — STUCK PIPE

## Question

> Is the drillstring showing a developing restriction/mobility problem?

Inputs:

```text
overpull
hookload
torque
MSE
ROP
cuttings concentration
friction
trajectory
historical stuck-pipe evidence
```

---

# 78. STUCK PIPE SIGNAL CHAIN

```text
friction/cuttings increase
        |
        +--> torque ↑
        +--> drag ↑
        +--> overpull ↑
        +--> ROP ↓
        +--> MSE changes
```

Module 5 should combine these.

---

# 79. STUCK PIPE FEATURE VECTOR

```json
{
  "overpull": 28,
  "overpull_slope": 2.2,
  "torque_zscore": 2.1,
  "mse_zscore": 1.8,
  "rop_change_pct": -55,
  "cuttings_concentration": 0.19,
  "historical_stuck_pipe_count": 3
}
```

---

# 80. HAZARD 3 — KICK / OVERPRESSURE

## Question

> Is the well moving toward a formation-influx / underbalanced condition?

Inputs:

```text
pit gain
flow-out > flow-in
ROP break
d-exponent deviation
BHP
pore-pressure margin
historical kick evidence
```

---

# 81. KICK SIGNAL CHAIN

```text
Pore pressure > BHP
        |
        v
formation influx
        |
        +--> flow-out increases
        +--> pit volume increases
        +--> pressure behaviour changes
        +--> possible ROP/d-exponent anomaly
```

Use multiple indicators.

---

# 82. KICK FEATURE VECTOR

```json
{
  "pit_gain_rate": 0.18,
  "flow_imbalance": 110,
  "rop_break_score": 0.72,
  "d_exponent_deviation": -2.1,
  "pp_margin": -0.04,
  "historical_kick_count": 2
}
```

---

# 83. HAZARD 4 — TORQUE & DRAG DYSFUNCTION

Inputs:

```text
torque
torque oscillation
RPM oscillation
stick-slip index
drag
MSE
trajectory
dogleg
```

Desired detection:

```text
persistent torque elevation
+
torque oscillation
+
RPM oscillation
+
mechanical inefficiency
```

---

# 84. HAZARD 5 — CEMENTING INTEGRITY

This hazard is primarily contextual/historical during drilling.

Inputs may include:

```text
casing section
formation
cement-job data
CBL/cement quality
previous cement failures
historical losses/kicks during cementing
```

Do not invent continuous telemetry that does not exist.

The risk may be:

```text
historical concern
```

rather than a live sensor anomaly.

---

# 85. RULE ENGINE BEFORE ML

Before training complex models, build deterministic rules.

Example:

```python
if (
    delta_flow_mean < FLOW_LOSS_THRESHOLD
    and pit_slope < PIT_DECLINE_THRESHOLD
    and fg_margin < FG_MARGIN_THRESHOLD
):
    lc_rule_score = 1.0
```

Then combine historical evidence:

```python
lc_historical_score = historical_lc_evidence(...)
```

This makes the initial system explainable.

---

# 86. ANOMALY DETECTION

After the rule engine works, add statistical anomaly detection.

Recommended first choices:

```text
rolling Z-score
EWMA
CUSUM
change-point detection
Isolation Forest
```

Isolation Forest is useful for multidimensional abnormal states.

Example features:

```text
flow imbalance
pit slope
SPP deviation
torque z-score
ROP change
MSE deviation
RPM variance
```

---

# 87. WHY ISOLATION FOREST FIRST

Advantages:

```text
does not require large labelled hazard datasets
works on multivariate features
easy to retrain
easy to inspect
works as a first anomaly baseline
```

Use it as:

```text
normal-behaviour anomaly score
```

not automatically as:

```text
hazard probability
```

---

# 88. SUPERVISED HAZARD MODELS

Once we have enough labelled sequences:

```text
XGBoost
Random Forest
LightGBM if permitted
```

Initial target:

```text
NORMAL
LOST_CIRCULATION
STUCK_PIPE
KICK
TORQUE_DRAG
WASHOUT
```

For the first production model, prefer a model that supports:

```text
feature importance
missing values
fast inference
small deployment footprint
```

XGBoost is a strong initial candidate.

---

# 89. TEMPORAL MODELS

Only introduce deep sequence models after the data pipeline works.

Candidates:

```text
LSTM
Temporal CNN
GRU
Transformer
```

They can use sequences such as:

```text
last 5 min telemetry
last 10 min telemetry
last 20 min telemetry
```

But they require:

```text
consistent timestamps
good labels
substantial sequences
well-level split discipline
```

Do not deploy an LSTM just because it sounds more advanced.

---

# 90. TRAINING DATA STRUCTURE

Create three main training datasets.

## Dataset A — Normal behaviour

```text
real public normal-operation telemetry
+
normal simulator telemetry
```

Purpose:

```text
anomaly detection
baseline modelling
```

## Dataset B — Synthetic labelled hazards

```text
simulator scenarios
```

with:

```text
scenario_id
hazard_label
severity
start_time
start_depth
end_time
end_depth
```

Purpose:

```text
supervised hazard classifier
```

## Dataset C — Historical real labelled incidents

When legitimate public/OIL events are available:

```text
DDR/WCR event labels
+
telemetry around event window
```

Purpose:

```text
real-world validation
field calibration
supervised retraining
```

---

# 91. DO NOT RANDOMLY SPLIT TELEMETRY ROWS

This is one of the biggest ML risks.

Suppose one well has:

```text
100,000 rows
```

and we randomly split rows:

```text
80% train
20% test
```

The same well may exist in both sets.

The model can partially memorize the well's behaviour.

That causes leakage.

Instead:

```text
TRAIN = wells A..N
VALIDATION = separate wells
TEST = completely unseen wells
```

---

# 92. WELL-LEVEL SPLITTING

Recommended:

```text
70% wells -> train
15% wells -> validation
15% wells -> test
```

Exact proportions can change with dataset size.

Important:

```text
NO WELL OVERLAP
```

between train/validation/test.

---

# 93. TEMPORAL LEAKAGE

Do not use future information.

For prediction at time `t`:

```text
features <= t
label window > t
```

For example:

```text
predict hazard 10 min ahead
```

then features can only use:

```text
data up to now
```

not:

```text
future event measurements
```

---

# 94. LOOK-AHEAD LABELING

For proactive prediction, define:

```text
prediction horizon
```

Example:

```text
5 min ahead
10 min ahead
20 min ahead
30 min ahead
```

Label:

```text
1
```

if a hazard begins inside the future horizon.

Example:

```text
current time = 10:00

hazard starts = 10:15

10-minute horizon:
label = 0

20-minute horizon:
label = 1
```

This must be consistent.

---

# 95. DEPTH-BASED LABELING

Because drilling is a depth-indexed process, use depth windows too.

Example:

```text
predict loss within next 20 m
```

Then label based on future depth relative to current bit position.

This enables:

```text
time-horizon prediction
+
depth-horizon prediction
```

---

# 96. EVENT LABEL FORMAT

Recommended:

```json
{
  "well_id": "NHK-089",
  "event_id": "EVT-00123",

  "hazard": "LOST_CIRCULATION",

  "start_timestamp": "...",
  "end_timestamp": "...",

  "start_md": 3224,
  "end_md": 3240,

  "start_tvdss": 3189,
  "end_tvdss": 3204,

  "formation": "Tipam Sandstone",

  "severity": 4,

  "label_source": "DDR",
  "provenance": "OBSERVED"
}
```

---

# 97. SYNTHETIC LABEL FORMAT

```json
{
  "scenario_id": "SIM-LC-00042",

  "well_id": "NHK-SIM-001",

  "scenario": "LOST_CIRCULATION",

  "start_sim_time": 1200,
  "end_sim_time": 1350,

  "start_md": 3230,
  "end_md": 3262,

  "start_tvdss": 3012,
  "end_tvdss": 3044,

  "severity": 3,

  "provenance": "SYNTHETIC"
}
```

---

# 98. SYNTHETIC DATA GENERATION STRATEGY

Do not create only one scenario with identical parameters.

Randomize within physically plausible ranges:

```text
formation
rock strength
mud weight
pump rate
WOB
RPM
friction coefficient
pore pressure
fracture pressure
loss coefficient
influx coefficient
trajectory
```

This prevents the ML model from learning a single simulator configuration.

---

# 99. DOMAIN RANDOMIZATION

For synthetic training, vary:

```text
noise level
sensor latency
sensor bias
formation parameters
trajectory
bit parameters
mud properties
operating controls
fault severity
fault onset depth
fault duration
```

The goal:

```text
MODEL LEARNS HAZARD PATTERN
not
MODEL MEMORIZES ONE SIMULATOR TRACE
```

---

# 100. SIM-TO-REAL STRATEGY

Synthetic data will never be perfectly real.

Therefore:

```text
synthetic
   +
public real
   +
later OIL real
```

should be used together.

Use:

```text
synthetic -> broad controlled coverage
real -> realism
OIL -> field specificity
```

---

# 101. NORMALIZATION

For ML training, normalize features based on the training set only.

Options:

```text
StandardScaler
RobustScaler
MinMaxScaler
```

For heavily skewed variables:

```text
log1p
Yeo-Johnson
```

Use the same fitted preprocessing object at inference.

Never fit the scaler on test data.

---

# 102. FEATURE PIPELINE VERSIONING

Every trained model must store:

```text
feature_schema_version
preprocessor_version
model_version
training_dataset_version
simulation_version
```

Example:

```text
MODEL:
risk-xgb-v1.2

FEATURES:
feature-set-v1.3

PREPROCESSOR:
prep-v1.1

SIMULATOR:
physics-v0.7

DATASET:
nwis-training-2026-09
```

---

# 103. CLASS IMBALANCE

Hazard events are usually rarer than normal operation.

Do not solve class imbalance by blindly duplicating every positive row.

Options:

```text
class weights
event-level oversampling
sequence-level sampling
focal loss for deep models
balanced mini-batches
```

Evaluation must remain on the original test distribution.

---

# 104. SEQUENCE SAMPLING

For temporal models:

```text
window length = 5–20 minutes
stride = configurable
```

Example:

```text
10 Hz telemetry
10-minute window

=> 6000 timesteps
```

That may be too large.

So first engineer lower-rate features:

```text
1 Hz
```

Then:

```text
10-minute sequence
=> 600 feature timesteps
```

Sequence length should be experimentally selected.

---

# 105. LABEL SMOOTHING

Do not let one sensor glitch create a one-row hazard label.

Use event windows:

```text
pre-event warning window
event window
post-event recovery
```

Example:

```text
T-10 min -> warning context
T-2 min  -> imminent context
T0       -> event
T+10 min -> event / recovery
```

This helps temporal models learn the progression.

---

# 106. PRE-EVENT WINDOWS

A useful training pattern:

```text
NORMAL
      |
      |
      v
EARLY DEVIATION
      |
      v
PRE-EVENT
      |
      v
HAZARD
      |
      v
RECOVERY
```

Module 5 is primarily interested in detecting the progression toward the hazard, not only the event after it has already happened.

---

# 107. ML TARGETS

We should train two related outputs.

## Target A — Anomaly

```text
normal / abnormal
```

## Target B — Hazard

```text
LC
SP
KICK
TORQUE_DRAG
WASHOUT
```

Then use:

```text
anomaly score
+
hazard model
+
physics/rule evidence
```

rather than relying on only one model.

---

# 108. MODEL OUTPUT

Canonical output:

```json
{
  "well_id": "NHK-SIM-001",
  "timestamp": "...",
  "depth_tvdss": 3012.8,

  "hazards": {
    "lost_circulation": {
      "score": 0.81,
      "state": "ELEVATED"
    },
    "stuck_pipe": {
      "score": 0.22,
      "state": "LOW"
    },
    "kick": {
      "score": 0.14,
      "state": "LOW"
    },
    "torque_drag": {
      "score": 0.47,
      "state": "WATCH"
    },
    "cementing": {
      "score": 0.10,
      "state": "LOW"
    }
  }
}
```

The score is a model score.

Do not call it a calibrated probability unless calibration has been demonstrated.

---

# 109. RISK STATES

Recommended mapping:

```text
0.00–0.24 = LOW
0.25–0.49 = WATCH
0.50–0.74 = ELEVATED
0.75–1.00 = HIGH
```

These are UI categories for the prototype.

Thresholds should eventually be calibrated with field experts and real data.

---

# 110. CONFIDENCE

Risk and confidence are separate.

Example:

```text
Risk = HIGH
Confidence = LOW
```

because:

```text
only one offset well
formation top inferred
sensor quality low
no independent live confirmation
```

Another:

```text
Risk = HIGH
Confidence = HIGH
```

because:

```text
seven relevant offsets
four matching historical events
same formation
same xi
multiple live anomalies
high telemetry quality
```

---

# 111. CONFIDENCE COMPONENTS

Build:

```text
historical evidence confidence
live sensor confidence
geological correlation confidence
model confidence
data coverage confidence
```

Example:

```text
confidence =
weighted(
    historical,
    live,
    geological,
    model,
    quality
)
```

The exact formula should be configurable.

---

# 112. DATA QUALITY SCORE

Example:

```text
data_quality =
1
-
weighted_missingness
-
weighted_bad_sensor_fraction
-
staleness_penalty
```

Bound:

```text
0 <= data_quality <= 1
```

Do not report 100% data quality if channels are stale or missing.

---

# 113. SOURCE GROUNDING

Historical evidence must maintain provenance.

Example:

```json
{
  "source_grounding": 1.0,
  "evidence": [
    {
      "well_id": "NHK-089",
      "event": "LOST_CIRCULATION",
      "document_id": "DDR-089-2015",
      "page": 17,
      "bbox": [100, 200, 600, 350]
    }
  ]
}
```

This allows Module 7 to open the original page.

---

# 114. RISK FUSION

The final hazard state can use:

```text
physics/rule evidence
+
statistical anomaly
+
ML score
+
historical evidence
+
data quality
+
geological correlation confidence
```

Example conceptual fusion:

```text
raw_model_score
        |
        +--> live anomaly strength
        +--> physics margin
        +--> historical evidence
        +--> correlation confidence
        +--> quality
        |
        v
   final risk score
```

Keep the fusion layer deterministic and documented.

---

# 115. DO NOT USE THE LLM AS THE RISK SOLVER

LLM/RAG should answer:

```text
What happened in similar wells?
What did engineers do?
What evidence supports this?
Show the original report.
```

The risk engine should answer:

```text
What is happening now?
How abnormal is it?
Which hazard is developing?
How strong is the evidence?
```

---

# 116. RAG + RISK ARCHITECTURE

```text
Module 5:
    LC risk = ELEVATED

              |
              v

Historical retrieval:
    similar ξ
    same formation
    similar operational state

              |
              v

RAG:
    historical case summaries
    mitigation steps
    source documents

              |
              v

Module 6:
    engineer-facing recommendation
```

---

# 117. MODEL EXPLAINABILITY

For XGBoost/Random Forest:

provide:

```text
top contributing features
```

Example:

```text
LOST CIRCULATION

Top contributors:

1. FG margin         +0.24
2. Flow imbalance    +0.20
3. Pit decline       +0.16
4. Historical LC     +0.15
5. ECD               +0.08
```

For deep models, use appropriate explainability methods later.

Never display a fabricated explanation.

---

# 118. BACKTESTING

For every historical test well:

```text
simulate inference as if the well were live
```

At each timestamp:

```text
only data available up to that timestamp
```

Then calculate:

```text
prediction
lead time
false positives
false negatives
```

This is better than evaluating on shuffled rows.

---

# 119. EVALUATION METRICS

For anomaly detection:

```text
precision
recall
F1
false alerts per hour
time-to-detection
```

For hazard classification:

```text
precision
recall
F1
PR-AUC
ROC-AUC where appropriate
confusion matrix
```

For proactive warning:

```text
lead time
event recall at 10 min
event recall at 20 min
event recall at 30 min
```

---

# 120. COST-SENSITIVE METRICS

For drilling risk analytics, false negatives and false positives have different costs.

Track:

```text
missed event
false alert
late alert
correct alert
```

A useful operational metric:

```text
false alerts per drilling hour
```

because a system that constantly alerts is not useful.

---

# 121. LEAD-TIME METRIC

For each true event:

```text
lead_time =
event_start - first_correct_alert
```

Report:

```text
median lead time
P25
P75
```

and separately:

```text
percentage of events detected
```

Do not make a blanket "30–60 minute lead time" claim unless the data supports it.

The current production description can use this as a target/demo objective, not a verified guarantee.

---

# 122. CALIBRATION

If the output is described as probability, calibrate it.

Options:

```text
Platt scaling
isotonic regression
temperature scaling
```

Validate calibration with:

```text
reliability diagram
Brier score
expected calibration error
```

Until then use:

```text
score
state
confidence
```

not:

```text
probability
```

---

# 123. MODEL REGISTRY

Every production-capable model record:

```text
model_id
model_version
training_dataset
feature_version
preprocessor_version
code_version
simulator_version
training_time
training_wells
validation_wells
test_wells
metrics
calibration_version
approved_by
```

---

# 124. MODEL RETRAINING

Retraining should happen only after checking:

```text
new data quality
label quality
feature drift
distribution drift
performance drift
```

Do not retrain automatically on every new data point.

Potential cadence:

```text
quarterly
or
after sufficient new labelled events
```

depending on production governance.

---

# 125. DATA DRIFT

Monitor:

```text
mud weight distribution
RPM distribution
WOB distribution
ROP distribution
pressure distribution
formation distribution
sensor missingness
```

If the new distribution is far from training:

```text
model confidence decreases
```

not:

```text
pretend the model is still equally reliable
```

---

# 126. TRAINING PIPELINE

Recommended pipeline:

```text
INGEST
  |
  v
SCHEMA CHECK
  |
  v
UNIT NORMALIZATION
  |
  v
TIME ALIGNMENT
  |
  v
DEPTH ALIGNMENT
  |
  v
QUALITY FLAGS
  |
  v
FEATURE ENGINEERING
  |
  v
LABELING
  |
  v
WELL-LEVEL SPLIT
  |
  v
TRAIN
  |
  v
VALIDATE
  |
  v
CALIBRATE
  |
  v
TEST ON UNSEEN WELLS
  |
  v
REGISTER MODEL
  |
  v
DEPLOY
```

---

# 127. MODEL TRAINING PSEUDOCODE

```python
raw = load_observed_and_synthetic_data()

validated = validate_schema(raw)

normalized = normalize_units(validated)

aligned = align_time_and_depth(normalized)

quality = compute_quality_flags(aligned)

features = engineer_features(
    aligned,
    module4_context=True
)

labels = build_event_labels(
    aligned,
    event_definitions
)

train_wells, val_wells, test_wells = split_by_well(
    aligned.well_id
)

preprocessor = fit_preprocessor(
    features[train_wells]
)

X_train = preprocessor.transform(features[train_wells])
X_val = preprocessor.transform(features[val_wells])
X_test = preprocessor.transform(features[test_wells])

model = train_xgboost(
    X_train,
    labels[train_wells],
    class_weights=True
)

validate(model, X_val, labels[val_wells])

test_results = evaluate(
    model,
    X_test,
    labels[test_wells]
)

register_model(
    model,
    preprocessor,
    test_results
)
```

---

# 128. INITIAL MODEL STACK

Recommended first stack:

```text
Baseline:
    rules + rolling statistics

Anomaly:
    Isolation Forest

Classification:
    XGBoost

Optional temporal:
    GRU/LSTM/Temporal CNN

Later:
    Transformer
```

The first release does NOT require all of these simultaneously.

---

# 129. WHY XGBOOST FIRST

Advantages:

```text
fast inference
good tabular performance
works with engineered features
strong baseline
feature importance
easy CPU deployment
good with moderate dataset sizes
```

The simulator can generate synthetic training sequences, while public real datasets provide realism.

---

# 130. WHY NOT TRAIN ON PDFs DIRECTLY

Documents are not the direct training input to the hazard classifier.

Use documents through:

```text
Module 1
  ↓
structured events
  ↓
Module 3 / Module 4
  ↓
historical evidence
```

The risk model sees:

```text
structured historical features
```

not raw PDF pixels.

RAG sees the source documents for explanation/evidence.

---

# 131. HOW MODULE 1 FEEDS MODULE 5

```text
DDR
 |
 v
OCR / VLM
 |
 v
structured event
 |
 +--> event type
 +--> depth
 +--> severity
 +--> mitigation
 +--> duration
 +--> formation
 |
 v
Module 4 correlation
 |
 v
historical evidence
 |
 v
Module 5
```

---

# 132. HISTORICAL EVENT NORMALIZATION

For every event:

```text
event_type
well_id
timestamp
MD
TVDSS
formation
xi
severity
duration
mitigation
root_cause
source_doc_id
page
bbox
confidence
```

This becomes training context.

---

# 133. NPT DURATION LABELS

If real event duration is available:

```text
NPT_start
NPT_end
NPT_duration
```

derive:

```text
duration_hours
```

Do not infer exact duration from a narrative unless the extraction system explicitly supports it.

---

# 134. HAZARD-SPECIFIC HISTORICAL FEATURES

For LC:

```text
historical LC frequency
severity
duration
mitigation
ξ distance
```

For stuck pipe:

```text
count
severity
depth
trajectory
mud type
BHA
mitigation
```

For kick:

```text
kick count
mud weight
formation pressure
severity
control method
```

For cement:

```text
cement job
casing section
CBL
failure
remediation
```

---

# 135. MODULE 4 → MODULE 5 INTERFACE

Required fields:

```text
active_well_id
current_md
current_tvdss
current_formation
current_xi

offset_well_id
omega_score
equivalent_tvdss
xi_distance
historical_event_count
historical_event_severity
correlation_confidence
formation_confidence
```

---

# 136. OFFSET EVIDENCE AGGREGATION

Example:

```text
5 relevant wells

NHK-089 -> LC
NHK-145 -> LC
NHK-201 -> no LC
NHK-220 -> LC
NHK-301 -> no LC
```

Historical LC evidence:

```text
3 / 5 wells
```

This can become:

```text
historical_lc_frequency = 0.60
```

but must be weighted by:

```text
Omega
xi proximity
data quality
event severity
```

---

# 137. HAZARD-SPECIFIC OFFSET WEIGHTING

The public SIH26121 repositories we inspected suggest a useful enhancement:

Do not necessarily use one identical similarity weighting for every hazard.

For example:

```text
stuck-pipe:
    trajectory / friction / BHA may matter more

kick:
    pressure / mud / formation context may matter more

loss:
    formation / fracture / mud window may matter more
```

This is a design improvement inspired by public implementations.

It must be calibrated, not hard-coded as a factual rule.

---

# 138. TRAJECTORY SIMILARITY

A useful advanced feature is comparing inclination/trajectory sequences rather than only final inclination.

Potential method:

```text
inclination profile
+
azimuth profile
+
dogleg profile
```

Possible distance:

```text
Dynamic Time Warping / FastDTW
```

Use it as an optional offset-similarity feature.

Do not make it the sole geological correlation mechanism.

---

# 139. PUBLIC REPOSITORY RESEARCH — WHAT WE LEARNED

Public SIH26121 repositories we reviewed showed several recurring patterns.

### Pattern A — proximity/depth matching

Typical:

```text
distance radius
+
depth window
+
formation
```

Useful as an MVP but insufficient as the final geological model.

### Pattern B — analog similarity

One public implementation uses:

```text
formation similarity
mud-weight similarity
BHA similarity
mud-type similarity
trajectory similarity
```

combined using AHP-style weighting.

Useful ideas:

```text
hazard-specific similarity
trajectory similarity
structured feature scoring
```

### Pattern C — document intelligence + RAG

Other implementations use:

```text
PDF
 ↓
VLM/OCR
 ↓
structured database
 ↓
vector retrieval
 ↓
RAG
```

Useful ideas:

```text
source provenance
page-level evidence
human review
RAG for historical knowledge
```

Our design should combine useful ideas from these approaches without copying a weaker raw-depth correlation.

---

# 140. IMPORTANT DIFFERENCE FROM PUBLIC SIMPLE CORRELATION

The core correlation should remain:

```text
MD
 ↓
TVDSS
 ↓
formation
 ↓
xi
 ↓
equivalent offset horizon
```

not simply:

```text
absolute depth difference < 50m
```

Module 4 is responsible for this.

---

# 141. MODULE 5 RISK CORRIDOR

Module 5 should support future depth risk.

At:

```text
current TVDSS = z
```

evaluate:

```text
z + 10
z + 20
z + 30
...
z + 200
```

At each future depth:

```text
formation
xi
offset equivalents
historical evidence
physics expectation
```

produce:

```text
LC risk
SP risk
Kick risk
Torque risk
```

This allows Module 6 to fire warnings before the event.

---

# 142. RISK CORRIDOR DATA STRUCTURE

```json
{
  "active_well_id": "NHK-412",
  "current_tvdss": 2986,
  "points": [
    {
      "tvdss": 2996,
      "lost_circulation": 0.20,
      "stuck_pipe": 0.18,
      "kick": 0.10,
      "torque_drag": 0.24
    },
    {
      "tvdss": 3006,
      "lost_circulation": 0.32,
      "stuck_pipe": 0.22,
      "kick": 0.12,
      "torque_drag": 0.35
    }
  ]
}
```

---

# 143. MODULE 6 TRIGGER CONTRACT

Module 5 emits:

```json
{
  "hazard": "LOST_CIRCULATION",
  "state": "HIGH",
  "score": 0.81,
  "confidence": 0.89,
  "distance_ahead_m": 18,
  "formation": "Tipam Sandstone",
  "evidence_count": 3
}
```

Module 6 decides:

```text
alert severity
alert timing
recommendation
acknowledgement workflow
```

Keep those concerns separate.

---

# 144. LIVE ALERT PROGRESSION

Example:

```text
>50m:
SAFE

20–50m:
PROACTIVE

0–20m:
IMMINENT
```

These are UI/demo categories.

The actual thresholds must be configurable.

---

# 145. ENGINEER INTERVENTION LOOP

The digital twin should support parameter changes:

```text
pump rate
RPM
WOB
mud weight
flow rate
```

The engineer interacts.

Then:

```text
operator change
      |
      v
physics model
      |
      v
state changes
      |
      v
telemetry changes
      |
      v
Module 5 risk changes
```

This is the final closed loop.

---

# 146. EXAMPLE CLOSED LOOP — LOST CIRCULATION

```text
START
 |
 v
normal drilling
 |
 v
BHP approaches fracture pressure
 |
 v
loss begins
 |
 v
flow-out falls
 |
 v
pit drops
 |
 v
Module 5 detects LC
 |
 v
Module 6 warns engineer
 |
 v
engineer reduces/reviews operating parameters
 |
 v
BHP/loss state changes
 |
 v
flow balance improves
 |
 v
risk decreases
```

The exact recommended operating action must not be hard-coded as a universal prescription.

It should come from approved engineering rules, historical evidence, or an authorized knowledge base.

---

# 147. EXAMPLE CLOSED LOOP — KICK

```text
formation becomes overpressured
 |
 v
BHP margin falls
 |
 v
influx begins
 |
 v
flow-out rises
 |
 v
pit volume rises
 |
 v
Module 5 raises kick risk
 |
 v
Module 6 alerts
 |
 v
engineer performs approved well-control response
 |
 v
physics state changes
 |
 v
influx reduces
 |
 v
risk decreases
```

---

# 148. EXAMPLE CLOSED LOOP — STUCK PIPE

```text
friction rises
 |
 v
drag increases
 |
 v
overpull increases
 |
 v
torque increases
 |
 v
ROP degrades
 |
 v
Module 5 sees multi-signal anomaly
 |
 v
historical stuck-pipe evidence confirms context
 |
 v
risk rises
```

---

# 149. DATABASE — RAW TELEMETRY

Table:

```text
telemetry_raw

id
well_id
wellbore_id
timestamp
sequence
md
tvdss
channel_name
value
unit
quality
source
provenance
ingestion_version
```

For high-throughput systems, use a time-series extension or time-series optimized store.

---

# 150. DATABASE — CANONICAL TELEMETRY

```text
telemetry

id
well_id
timestamp
md
tvdss

rpm
wob
rop
torque
hookload

flow_in
flow_out

standpipe_pressure
annular_pressure

pit_volume
mud_weight
ecd

inclination
azimuth
temperature

quality_score
provenance_class
```

---

# 151. DATABASE — DERIVED FEATURES

```text
derived_features

id
well_id
timestamp
md
tvdss
formation
xi

delta_flow
pit_slope
pit_gain

overpull
mse
d_exponent

torque_variance
rpm_variance
stick_slip_index

cuttings_concentration

pp_margin
fg_margin

historical_lc_count
historical_sp_count
historical_kick_count

data_quality
```

---

# 152. DATABASE — RISK SCORES

```text
risk_scores

id
well_id
timestamp
md
tvdss
formation

lc_score
stuck_pipe_score
kick_score
torque_drag_score
cement_score

lc_state
stuck_pipe_state
kick_state
torque_drag_state
cement_state

confidence
data_quality

model_version
feature_version
```

---

# 153. DATABASE — RISK EVIDENCE

```text
risk_evidence

id
risk_id

evidence_type
source_id
well_id
event_id

feature_name
feature_value
contribution

document_id
page_number
bbox

confidence
```

---

# 154. DATABASE — MODEL REGISTRY

```text
models

id
model_id
model_version
hazard
algorithm

dataset_version
feature_version
preprocessor_version
simulator_version

train_metrics
validation_metrics
test_metrics

calibration_version

created_at
approved_at
status
```

---

# 155. DATABASE — SIMULATION RUNS

```text
simulation_runs

id
simulation_id
well_id

scenario
start_time
end_time

initial_conditions
parameter_overrides

formation_model_version
physics_model_version
sensor_model_version

ground_truth_labels

status
```

---

# 156. DATABASE — SCENARIO EVENTS

```text
scenario_events

id
simulation_id

scenario
hazard
severity

start_time
end_time

start_md
end_md

start_tvdss
end_tvdss

parameter_changes
ground_truth
```

---

# 157. API — LIVE TELEMETRY

```http
GET /api/telemetry/current?well_id={id}
```

Returns current canonical state.

---

# 158. API — TELEMETRY STREAM

```http
WS /api/telemetry/stream?well_id={id}
```

WebSocket sends:

```text
5–10 messages/sec
```

---

# 159. API — SIMULATOR CONTROL

```http
POST /api/simulator/start
POST /api/simulator/pause
POST /api/simulator/reset
POST /api/simulator/step
```

---

# 160. API — SIMULATION SPEED

```http
POST /api/simulator/speed
```

Body:

```json
{
  "speed": 10
}
```

---

# 161. API — SCENARIO INJECTION

```http
POST /api/simulator/scenario
```

Example:

```json
{
  "scenario": "LOST_CIRCULATION",
  "start_depth_tvdss": 3230,
  "severity": 3
}
```

---

# 162. API — CURRENT FEATURES

```http
GET /api/risk/features/current?well_id={id}
```

---

# 163. API — CURRENT RISK

```http
GET /api/risk/current?well_id={id}
```

---

# 164. API — RISK CORRIDOR

```http
GET /api/risk/corridor
```

Parameters:

```text
well_id
depth_tvdss
lookahead_m
step_m
```

---

# 165. API — HISTORICAL EVIDENCE

```http
GET /api/risk/evidence
```

Parameters:

```text
well_id
hazard
formation
xi
```

---

# 166. API — MODEL STATUS

```http
GET /api/models/status
```

Returns:

```json
{
  "models": {
    "lost_circulation": {
      "version": "xgb-lc-v1.2",
      "status": "ACTIVE"
    }
  }
}
```

---

# 167. FRONTEND — MAIN MODULE 5 PANEL

Display:

```text
Current depth
Formation
ξ
Current risk states
Live telemetry
Anomaly strips
Historical evidence
Risk corridor
Model confidence
Data quality
```

---

# 168. FIVE HAZARD GAUGES

Example:

```text
LOST CIRCULATION
████████░░  HIGH
0.81
```

```text
STUCK PIPE
██░░░░░░░░  LOW
0.22
```

```text
KICK
█░░░░░░░░░  LOW
0.14
```

```text
TORQUE / DRAG
████░░░░░░  WATCH
0.47
```

```text
CEMENT
█░░░░░░░░░  LOW
0.10
```

---

# 169. EVIDENCE PANEL

For selected hazard:

```text
WHY IS THIS RISK ELEVATED?

Live signal
    ΔQ = -130 L/min
    persistent for 7 min

Physics
    FG margin = -0.01

Historical
    3 relevant offsets
    2 had LC at similar ξ

Data quality
    96%

Correlation
    confidence = 91%
```

---

# 170. SENSOR TREND PANEL

Show:

```text
flow-in
flow-out
delta-flow

SPP
annular pressure

pit volume

torque
RPM
WOB
ROP

ECD
MSE
```

Use linked cursors.

The user should be able to inspect the same time/depth window across channels.

---

# 171. EVENT REPLAY

Clicking a historical or simulated event should show:

```text
event start
event evolution
event end
```

and replay:

```text
telemetry
risk score
alert
engineer action
```

This makes the simulator useful for demonstrations and training.

---

# 172. SIMULATOR CONTROL UI

Recommended:

```text
DRILLING SIMULATOR

Well: NHK-SIM-001

Depth:
TVDSS:
Formation:
ξ:

RPM:
WOB:
Pump Rate:
Mud Weight:

[ START ]
[ PAUSE ]
[ RESET ]

SCENARIOS

[ NORMAL ]
[ LOST CIRCULATION ]
[ KICK ]
[ STUCK PIPE ]
[ STICK-SLIP ]
[ WASHOUT ]
```

---

# 173. DO NOT ALLOW SCENARIO UI TO BYPASS PHYSICS

Bad:

```text
press "LC"
→ set risk = HIGH
```

Good:

```text
press "LC"
→ modify loss coefficient
→ physics changes
→ telemetry changes
→ feature engine changes
→ risk changes
```

The second workflow is mandatory.

---

# 174. PHYSICS ENGINE MODULE STRUCTURE

```text
physics-engine/

engine.py
state.py
clock.py
config.py

formation/
    formation_model.py
    pressure_model.py

trajectory/
    trajectory_model.py
    minimum_curvature.py

drilling/
    rop_model.py
    mse_model.py
    bit_model.py

hydraulics/
    mud_model.py
    pressure_loss.py
    ecd.py
    pit_balance.py

drillstring/
    torque_drag.py
    torsional.py
    axial.py

hole_cleaning/
    cuttings_model.py

faults/
    lost_circulation.py
    kick.py
    stuck_pipe.py
    stick_slip.py
    washout.py

sensors/
    sensor.py
    noise.py
    drift.py
    failures.py

telemetry/
    websocket.py
    historian.py
    canonical_schema.py
    witsml_adapter.py
```

---

# 175. RISK ENGINE STRUCTURE

```text
risk-engine/

features/
    flow.py
    pressure.py
    torque.py
    drilling.py
    geology.py
    historical.py

anomaly/
    statistics.py
    isolation_forest.py

hazards/
    lost_circulation.py
    stuck_pipe.py
    kick.py
    torque_drag.py
    cementing.py

models/
    xgboost_loader.py

fusion/
    risk_fusion.py
    confidence.py

evidence/
    evidence_resolver.py

evaluation/
    backtest.py
    metrics.py
    calibration.py
```

---

# 176. TRAINING REPOSITORY STRUCTURE

```text
ml/

data/
    raw/
        volve/
        force/
        synthetic/
    processed/
    features/
    labels/

notebooks/
    01_eda
    02_data_quality
    03_feature_engineering
    04_baseline
    05_isolation_forest
    06_xgboost
    07_evaluation

src/
    ingestion/
    preprocessing/
    labels/
    features/
    training/
    evaluation/
    inference/

models/
    registry/

configs/
    features.yaml
    thresholds.yaml
    training.yaml
```

---

# 177. DATA VERSIONING

Track:

```text
dataset version
source versions
preprocessing version
feature version
label version
simulator version
model version
```

Example:

```text
dataset:
nwis-dataset-v0.4

features:
nwis-features-v0.7

sim:
physics-v0.9

model:
xgb-risk-v0.3
```

---

# 178. TRAINING CONFIG

Example:

```yaml
dataset:
  sampling_frequency: 1s

split:
  strategy: well_group
  train: 0.70
  validation: 0.15
  test: 0.15

features:
  rolling_windows:
    - 10s
    - 30s
    - 60s
    - 300s

models:
  anomaly:
    type: isolation_forest

  classifier:
    type: xgboost

labels:
  hazards:
    - lost_circulation
    - stuck_pipe
    - kick
    - torque_drag
    - washout
```

---

# 179. SIMULATION CALIBRATION

Physics parameters should be calibration targets:

```text
alpha_ROP
ROP exponent
friction coefficient
loss coefficient
influx coefficient
pressure profiles
bit torque coefficient
torsional damping
cuttings transport coefficient
sensor noise
```

Fit these against observed public or authorized field data where possible.

---

# 180. PARAMETER CALIBRATION STRATEGY

Start with:

```text
manual engineering baseline
```

Then:

```text
grid / random search
```

Then:

```text
Bayesian optimization
```

if needed.

Use objective functions such as:

```text
MAE of ROP
RMSE of SPP
RMSE of torque
distribution error
event-signature agreement
```

---

# 181. PHYSICS VALIDATION — LEVEL 1

Check monotonic relations.

Examples:

```text
pump rate ↑
→ friction loss ↑

mud density ↑
→ hydrostatic pressure ↑

WOB ↑
→ ROP generally ↑ within calibrated range

RPM ↑
→ ROP generally ↑ within calibrated range

BHP > fracture pressure
→ losses can initiate

Pore pressure > BHP
→ influx can initiate
```

---

# 182. PHYSICS VALIDATION — LEVEL 2

Check conservation:

```text
flow balance
pit balance
mass/volume balance
```

Example:

```text
integrated Qin
+
integrated influx
-
integrated Qout
-
integrated loss
```

should be consistent with modeled inventory change.

---

# 183. PHYSICS VALIDATION — LEVEL 3

Scenario signature tests:

```text
LC
    flow ↓
    pit ↓

Kick
    flow-out ↑
    pit ↑

Stuck pipe
    torque ↑
    overpull ↑
    ROP ↓

Stick-slip
    torque oscillation
    RPM oscillation
```

---

# 184. SENSOR VALIDATION

Verify:

```text
noise distribution
latency
dropouts
range
quantization
drift
```

and ensure:

```text
telemetry != internal truth
```

but remains statistically consistent.

---

# 185. RISK ENGINE VALIDATION

For each hazard:

```text
normal case
early case
clear event
recovery
```

The risk state should transition sensibly.

Example:

```text
LOW
 ↓
WATCH
 ↓
ELEVATED
 ↓
HIGH
 ↓
ELEVATED
 ↓
WATCH
 ↓
LOW
```

Avoid oscillating every second due to threshold noise.

Use hysteresis.

---

# 186. RISK HYSTERESIS

Example:

```text
enter HIGH at 0.75
leave HIGH only below 0.65
```

This prevents:

```text
0.74
0.76
0.74
0.76
```

from flickering the UI.

---

# 187. ALERT DEBOUNCING

Require persistence:

```text
score > threshold
for N consecutive samples
```

before triggering.

Similarly require:

```text
score < recovery_threshold
for M seconds
```

before clearing.

---

# 188. UNIT TESTS

Physics:

```text
test_md_progression
test_minimum_curvature
test_hydrostatic_pressure
test_annular_area
test_friction_loss
test_spp
test_bhp
test_ecd
test_pit_balance
test_rop
test_mse
test_torque
test_stick_slip
```

---

# 189. SCENARIO TESTS

```text
test_normal_scenario
test_lost_circulation
test_kick
test_stuck_pipe
test_stick_slip
test_washout
```

---

# 190. ML TESTS

```text
test_no_data_leakage
test_well_split
test_preprocessor_fit_only_train
test_feature_schema
test_label_generation
test_class_balance
test_inference_latency
test_model_version
```

---

# 191. INTEGRATION TEST

The complete chain:

```text
simulator
 →
telemetry
 →
feature engine
 →
Module 4 context
 →
hazard engine
 →
risk fusion
 →
Module 6
 →
UI
```

Must work without manual intervention.

---

# 192. END-TO-END LOST CIRCULATION TEST

Expected:

```text
scenario injected
      |
      v
loss coefficient changes
      |
      v
physics produces loss
      |
      v
flow-out decreases
      |
      v
pit decreases
      |
      v
LC anomaly rises
      |
      v
historical correlation present
      |
      v
LC risk rises
      |
      v
Module 6 alert
```

---

# 193. END-TO-END KICK TEST

Expected:

```text
overpressure scenario
      |
      v
influx starts
      |
      v
flow-out increases
      |
      v
pit gain
      |
      v
kick anomaly
      |
      v
Module 5 risk
      |
      v
Module 6 alert
```

---

# 194. END-TO-END STUCK PIPE TEST

Expected:

```text
friction / cuttings scenario
      |
      v
drag rises
      |
      v
overpull rises
      |
      v
torque rises
      |
      v
ROP degrades
      |
      v
SP risk rises
```

---

# 195. END-TO-END INTERVENTION TEST

Scenario:

```text
LC begins
```

Then operator changes simulator parameter.

Verify:

```text
physical state changes
→ telemetry responds
→ risk changes
→ alert clears only after recovery condition
```

This is the key digital-twin test.

---

# 196. LATENCY REQUIREMENTS

Targets:

```text
physics -> telemetry:
< 200 ms

telemetry -> features:
< 200 ms

features -> risk:
< 200 ms

risk -> alert:
< 500 ms

total:
~1 second or better
```

These are engineering targets for the prototype, not requirements specified by OIL.

---

# 197. MODEL INFERENCE REQUIREMENTS

For online XGBoost:

```text
single prediction
<< 100 ms
```

For an anomaly model:

```text
single prediction
<< 50 ms
```

Do not build a huge inference pipeline that cannot keep up with telemetry.

---

# 198. SECURITY / SAFETY SEPARATION

The simulator should be clearly labelled:

```text
SIMULATION
```

The production system should clearly identify:

```text
LIVE
SIMULATED
HISTORICAL
```

Never confuse simulated telemetry with live rig telemetry in the interface.

---

# 199. UI DATA BADGE

Recommended:

```text
SOURCE: SIMULATION
```

or:

```text
SOURCE: LIVE WITSML
```

or:

```text
SOURCE: HISTORICAL
```

This should be always visible.

---

# 200. AI GOVERNANCE

The system is decision support.

It should not automatically issue uncontrolled operating commands.

Architecture:

```text
AI / analytics
      |
      v
recommendation
      |
      v
engineer review
      |
      v
approved action
```

Module 6 owns acknowledgement/override/escalation workflows.

---

# 201. MODEL FAILURE BEHAVIOUR

If telemetry is degraded:

```text
do not maintain old confidence indefinitely
```

Instead:

```text
data quality falls
      |
      v
confidence falls
      |
      v
risk output displays reduced confidence
```

If critical inputs are unavailable:

```text
MODEL STATE: LIMITED
```

not:

```text
NORMAL
```

---

# 202. SENSOR FAILURE SCENARIOS

Simulator should support:

```text
flow sensor dropout
pressure sensor bias
RPM stuck value
torque spike
temperature drift
delayed channel
```

These are useful for testing whether Module 5 falsely interprets bad instrumentation as a hazard.

---

# 203. SENSOR FAILURE VS PHYSICAL HAZARD

Example:

```text
flow_out suddenly drops
```

Could mean:

```text
actual lost circulation
```

or:

```text
flow sensor failure
```

Module 5 must use:

```text
cross-channel evidence
sensor quality
redundancy
physics margins
```

to separate them.

---

# 204. MULTI-SIGNAL CONFIRMATION

Example LC:

```text
flow imbalance
+
pit trend
+
pressure condition
```

is stronger than:

```text
flow imbalance alone
```

Example kick:

```text
pit gain
+
flow imbalance
+
pressure margin
```

is stronger than:

```text
ROP spike alone
```

This is fundamental to reducing false alarms.

---

# 205. FEATURE IMPORTANCE BY HAZARD

Recommended conceptual prioritization:

```text
LOST CIRCULATION
    flow / pit / FG margin / ECD / history

STUCK PIPE
    overpull / torque / MSE / ROP / cuttings / trajectory

KICK
    pit gain / flow / PP margin / ROP / d-exponent / history

TORQUE & DRAG
    torque / RPM / stick-slip / drag / MSE / geometry

CEMENT
    cement/CBL/history / formation / casing
```

These are architecture priorities, not fixed final weights.

---

# 206. HAZARD MODELS SHOULD REMAIN INDEPENDENT

Implement:

```python
lost_circulation_engine(...)
stuck_pipe_engine(...)
kick_engine(...)
torque_drag_engine(...)
cementing_engine(...)
```

not:

```python
one_magic_risk_model(...)
```

This gives:

```text
better explainability
better testing
hazard-specific tuning
easier retraining
```

---

# 207. FUSION ENGINE

Example:

```python
final_score = weighted_fusion(
    physics_score,
    rules_score,
    anomaly_score,
    ml_score,
    historical_score,
    quality_score
)
```

Weights are configuration.

Store the contribution of each component.

---

# 208. RISK EVIDENCE OBJECT

Every risk should expose:

```json
{
  "hazard": "LOST_CIRCULATION",
  "score": 0.81,
  "state": "HIGH",

  "contributors": [
    {
      "type": "LIVE_ANOMALY",
      "feature": "delta_flow_5m",
      "value": -130,
      "contribution": 0.20
    },
    {
      "type": "PHYSICS",
      "feature": "fg_margin",
      "value": -0.01,
      "contribution": 0.24
    },
    {
      "type": "HISTORICAL",
      "feature": "matching_offset_events",
      "value": 2,
      "contribution": 0.15
    }
  ]
}
```

---

# 209. MODEL EXPLANATION ≠ LLM EXPLANATION

Model explanation should come from actual feature contribution.

LLM can then turn those facts into readable language.

Example:

```text
Analytics:
FG margin = -0.01
ΔQ = -130
2 matching offset LC events

LLM:
"Loss risk is elevated because the simulated
bottomhole pressure has crossed the modeled
fracture boundary while return flow has declined
for several minutes. Two correlated offset wells
recorded historical losses near the current ξ."
```

The LLM must not invent the evidence.

---

# 210. TRAINING/INFERENCE PARITY

Training and inference must use the same:

```text
unit conversions
feature calculations
rolling windows
normalization
missing-data rules
```

Implement these in shared libraries where possible.

---

# 211. FEATURE STORE CONCEPT

Even without a dedicated feature-store product, structure features so that:

```text
training
and
online inference
```

call the same feature definitions.

Avoid:

```text
training_feature_logic.py
```

being completely separate from:

```text
runtime_feature_logic.py
```

---

# 212. ONLINE FEATURE WINDOW

At runtime:

```text
current t
```

maintain:

```text
last 10 sec
last 30 sec
last 60 sec
last 5 min
```

feature windows.

Use a ring buffer or time-series cache.

Do not query the entire database every telemetry tick.

---

# 213. CACHING

Cache:

```text
current formation
Module 4 correlation result
top offset wells
historical evidence summary
model objects
feature scalers
```

Update expensive components at appropriate frequencies.

For example:

```text
telemetry features:
5–10 Hz

Module 4 correlation:
on depth change / configurable interval

offset ranking:
every 30 sec or on meaningful geological transition

risk model:
5–10 Hz
```

---

# 214. OMEGA UPDATE

Module 4's offset ranking can be recalculated periodically.

Module 5 should consume:

```text
top N relevant offsets
```

rather than recomputing spatial similarity every telemetry sample.

---

# 215. HISTORICAL EVIDENCE CACHE

For the current formation/ξ region:

```text
retrieve historical evidence once
```

then update only when:

```text
xi moves significantly
formation changes
ranking changes
new data arrives
```

This reduces latency.

---

# 216. RISK CORRIDOR COMPUTATION

Do not recompute the entire 200 m corridor from scratch at maximum frequency.

Use:

```text
incremental updates
```

and only recompute affected portions when:

```text
depth changes
formation changes
offset ranking changes
new telemetry changes a risk condition
```

---

# 217. DEMO SCENARIO LIBRARY

Create reproducible scenarios.

```text
scenario_001_normal
scenario_002_loss_early
scenario_003_loss_severe
scenario_004_kick_early
scenario_005_kick_severe
scenario_006_stuck_pipe
scenario_007_stick_slip
scenario_008_washout
scenario_009_sensor_failure
```

Every scenario should be deterministic from a seed.

This makes demonstrations repeatable.

---

# 218. RANDOMNESS POLICY

Randomness is allowed for:

```text
sensor noise
scenario parameter sampling
synthetic dataset generation
```

but always with a seed during testing.

Example:

```python
rng = np.random.default_rng(42)
```

The physics equations must remain deterministic for a given seed/configuration.

---

# 219. SYNTHETIC DATA REPRODUCIBILITY

Every generated sequence stores:

```text
random_seed
simulator_version
parameter_set
scenario_id
```

Therefore:

```text
same seed + same version + same parameters
=
same sequence
```

This is essential for debugging.

---

# 220. SYNTHETIC DATA GENERATION SCALE

Start small:

```text
100 normal
20 LC
20 kick
20 stuck pipe
20 stick-slip
10 washout
```

Then scale to:

```text
thousands of runs
```

only after the simulator produces useful signatures.

Do not generate millions of bad synthetic sequences.

---

# 221. SYNTHETIC DATA QUALITY GATES

Before adding a generated run to training:

```text
physics sanity check
range check
mass balance
scenario activation check
sensor validation
label correctness
```

Reject invalid runs.

---

# 222. DOMAIN RANDOMIZATION TABLE

For every simulation batch randomize:

```text
formation:
    rock strength
    density
    permeability
    PP
    FG

operating:
    WOB
    RPM
    pump rate
    mud weight

well:
    inclination
    azimuth
    trajectory

mechanics:
    friction
    bit condition
    drillstring parameters

sensors:
    noise
    delay
    bias
    dropout
```

---

# 223. DATASET COMPOSITION

Example training mix:

```text
40% public observed
40% synthetic
20% historical extracted
```

This is only an initial experiment.

The correct ratio must be determined empirically.

When OIL data is authorized, the composition should change toward field data.

---

# 224. OIL CALIBRATION TARGET

Eventually:

```text
PUBLIC
   |
   v
initial model
   |
   v
OIL data
   |
   v
field calibration
   |
   v
OIL-specific model
```

Keep the model metadata explicit.

---

# 225. OIL MODEL GOVERNANCE

Production model labels:

```text
PUBLIC_DEVELOPMENT
FIELD_CALIBRATED
FIELD_VALIDATED
PRODUCTION_APPROVED
```

Do not move directly from:

```text
PUBLIC_DEVELOPMENT
```

to:

```text
PRODUCTION
```

without validation.

---

# 226. OIL / NDR DATA ACCESS POLICY

The architecture must support authorized data ingestion without assuming public scrapeability.

Production acquisition should be through:

```text
OIL-provided data
authorized DGH/NDR access
authorized data export
approved API
```

No architecture should depend on bypassing access restrictions.

---

# 227. DEMO DATA BOUNDARY

For the SIH demo:

```text
PUBLIC DATA
+
REPRESENTATIVE / SYNTHETIC OIL-LIKE STRUCTURE
+
PHYSICS SIMULATION
```

Label the data appropriately.

Example:

```text
Data source:
Synthetic / Public Development Data

Field:
Demonstration
```

Do not present synthetic formations as measured OIL observations.

---

# 228. COMPLETE DATA LIFECYCLE

```text
SOURCE
 |
 +--> public observed
 +--> authorized field observed
 +--> synthetic
 +--> inferred
 |
 v
INGEST
 |
 v
NORMALIZE
 |
 v
QUALITY
 |
 v
CORRELATE
 |
 v
FEATURE
 |
 v
LABEL
 |
 v
TRAIN
 |
 v
VALIDATE
 |
 v
REGISTER
 |
 v
DEPLOY
 |
 v
MONITOR
 |
 v
RECALIBRATE
```

---

# 229. MODULE 5 IMPLEMENTATION ORDER

## Phase 1

```text
Formation model
Trajectory
MD/TVDSS
ROP
```

## Phase 2

```text
Hydraulics
BHP
ECD
SPP
Pit balance
```

## Phase 3

```text
Torque
Drag
MSE
Hole cleaning
Stick-slip
```

## Phase 4

```text
Fault/scenario engine
```

## Phase 5

```text
Sensor model
Live WebSocket telemetry
Historian
```

## Phase 6

```text
Feature engineering
Rule-based hazard engines
```

## Phase 7

```text
Module 4 integration
Historical evidence
```

## Phase 8

```text
Isolation Forest
```

## Phase 9

```text
XGBoost
```

## Phase 10

```text
Backtesting
Calibration
```

## Phase 11

```text
Module 6 alerts
```

## Phase 12

```text
Engineer intervention
Closed-loop simulation
```

---

# 230. FIRST WORKING MILESTONE

The first useful implementation should be only:

```text
FORMATION
+
MD/TVDSS
+
ROP
+
FLOW
+
PRESSURE
+
PIT
+
TORQUE
+
WebSocket
```

Then confirm the dashboard shows a live, causally coupled well.

Do not train ML before this works.

---

# 231. SECOND WORKING MILESTONE

Add:

```text
LOST CIRCULATION
```

and prove:

```text
BHP condition
 →
physical loss
 →
flow imbalance
 →
pit decline
 →
risk increase
```

---

# 232. THIRD WORKING MILESTONE

Add:

```text
KICK
```

and prove:

```text
pore pressure > BHP
 →
influx
 →
pit gain
 →
flow imbalance
 →
kick risk
```

---

# 233. FOURTH WORKING MILESTONE

Add:

```text
STUCK PIPE
```

and prove:

```text
friction/cuttings
 →
drag
 →
overpull
 →
torque
 →
ROP degradation
 →
risk
```

---

# 234. FIFTH WORKING MILESTONE

Add:

```text
Module 4
```

Then prove:

```text
same geological horizon
 →
historical offset evidence
 →
risk confidence increases
```

---

# 235. SIXTH WORKING MILESTONE

Train:

```text
Isolation Forest
XGBoost
```

and compare:

```text
rules only
rules + anomaly
rules + anomaly + ML
```

This gives a measurable reason for adding ML.

---

# 236. SEVENTH WORKING MILESTONE

Add:

```text
risk corridor
+
Module 6
```

Then run a full scenario.

---

# 237. THE FINAL SIH DEMO

Example:

```text
ACTIVE WELL: NHK-SIM-001
MD: 3218 m
TVDSS: 3012.8 m
FORMATION: Tipam Sandstone
ξ: 0.63

LIVE TELEMETRY

RPM             110
WOB              85 kN
ROP              14 m/hr
FLOW IN        2100 L/min
FLOW OUT       2095 L/min
SPP             155 bar
PIT              80.2 m3
ECD             1.34 g/cc

RISK

LC       LOW
SP       LOW
KICK     LOW
TORQUE   WATCH
CEMENT   LOW
```

Then the simulated well advances.

---

# 238. DEMO: DEVELOPING LOSS

Physics:

```text
BHP approaches fracture pressure
```

Then:

```text
Q_loss begins
```

Telemetry evolves:

```text
flow out:
2095
2082
2050
2010
1960
```

Pit:

```text
80.2
80.1
79.9
79.6
79.1
```

Module 5:

```text
LC risk:
LOW -> WATCH -> ELEVATED -> HIGH
```

---

# 239. DEMO: HISTORICAL CORRELATION

Module 4 says:

```text
current ξ = 0.63

relevant offsets:
NHK-089
NHK-145
MOR-034

historical LC:
2 matching wells
```

Module 5:

```text
Historical evidence: HIGH
Live anomaly: HIGH
Physics margin: HIGH
Data quality: 96%
Correlation confidence: 91%

FINAL:
LOST CIRCULATION = HIGH
```

---

# 240. DEMO: ALERT

Module 6:

```text
PROACTIVE HAZARD WARNING

Historical analogue:
LC zone

Distance ahead:
18 m

Formation:
Tipam Sandstone

Evidence:
2/3 relevant offsets experienced losses

Current signal:
negative flow imbalance

Review required.
```

The exact engineering recommendation should be sourced from approved engineering logic or historical evidence, not invented by the language model.

---

# 241. DEMO: ENGINEER RESPONSE

Engineer changes:

```text
pump rate
or other approved operating parameter
```

Simulator:

```text
state changes
 →
BHP changes
 →
Q_loss changes
 →
flow balance changes
 →
pit trend changes
```

Module 5:

```text
HIGH
↓
ELEVATED
↓
WATCH
```

Module 6 clears after the configured recovery persistence.

---

# 242. WHY THIS IS STRONGER THAN A RANDOM TELEMETRY DEMO

A random dashboard can show:

```text
moving charts
AI score
alert
```

Our system can demonstrate:

```text
engineering input
 →
physics
 →
sensor
 →
telemetry
 →
anomaly
 →
geological evidence
 →
ML/rule fusion
 →
risk
 →
alert
 →
engineer action
 →
physical response
```

That is the actual digital-twin story.

---

# 243. MODULE 5 RESPONSIBILITIES

Module 5 owns:

```text
physics-informed feature interpretation
anomaly detection
hazard scoring
historical evidence fusion
confidence
data quality
ML inference
risk corridor
```

Module 5 does NOT own:

```text
raw document OCR
primary PDF extraction
map rendering
final alert workflow
LLM conversational response
```

Those belong to other modules.

---

# 244. MODULE 5 INPUTS

```text
Module 1:
structured historical events

Module 2:
well/spatial context

Module 3:
historical knowledge retrieval

Module 4:
geological correlation

Telemetry:
live drilling channels

Physics engine:
simulated telemetry during demo
```

---

# 245. MODULE 5 OUTPUTS

```text
hazard scores
risk states
confidence
data quality
anomaly status
historical evidence
risk corridor
model explanation
```

Module 6 consumes these.

---

# 246. COMPLETE MODULE 5 CONTRACT

Input:

```text
well state
telemetry
formation context
xi
offset evidence
historical events
```

Process:

```text
preprocess
feature engineering
rules
anomaly
ML
historical fusion
confidence
```

Output:

```text
hazard-specific risk
evidence
confidence
lead-time projection
```

---

# 247. DEFINITION OF DONE — PHYSICS ENGINE

```text
[ ] Well depth evolves
[ ] MD/TVDSS updates
[ ] Formation changes with depth
[ ] ROP responds to WOB/RPM/formation
[ ] Hydraulics respond to pump rate and mud
[ ] BHP is calculated
[ ] ECD is calculated
[ ] SPP is calculated
[ ] Pit balance is conserved
[ ] Losses emerge from fracture condition
[ ] Influx emerges from pressure condition
[ ] Torque responds to mechanics
[ ] MSE is calculated
[ ] Stick-slip can emerge
[ ] Hole-cleaning effects exist
[ ] Sensor noise exists
[ ] Telemetry streams live
```

---

# 248. DEFINITION OF DONE — ML

```text
[ ] Real public data loaded
[ ] Synthetic data generator works
[ ] Data provenance is preserved
[ ] Units normalized
[ ] Missing values handled
[ ] Quality flags implemented
[ ] Time-depth alignment implemented
[ ] Features versioned
[ ] Event labels versioned
[ ] Well-level split
[ ] Isolation Forest baseline
[ ] XGBoost baseline
[ ] Unseen-well evaluation
[ ] Lead-time metrics
[ ] False-alert metrics
[ ] Model registry
[ ] Inference pipeline
```

---

# 249. DEFINITION OF DONE — RISK ENGINE

```text
[ ] LC engine
[ ] Stuck-pipe engine
[ ] Kick engine
[ ] Torque/drag engine
[ ] Cement engine
[ ] Historical evidence fusion
[ ] Data quality
[ ] Confidence
[ ] Hysteresis
[ ] Debouncing
[ ] Risk corridor
[ ] Evidence provenance
```

---

# 250. DEFINITION OF DONE — END TO END

```text
[ ] Simulator starts
[ ] Telemetry appears
[ ] Module 4 context updates
[ ] Risk models update
[ ] Hazard scenario produces expected signature
[ ] Risk increases
[ ] Module 6 alert fires
[ ] Engineer changes a parameter
[ ] Physics responds
[ ] Telemetry responds
[ ] Risk falls
[ ] Alert clears
[ ] Entire run is replayable
```

---

# 251. ENGINEERING PRINCIPLES TO KEEP

## Principle 1

**Physics before AI.**

## Principle 2

**Telemetry comes from state, not random animation.**

## Principle 3

**Historical evidence is useful only after geological correlation.**

## Principle 4

**Risk is not the same as probability.**

## Principle 5

**Confidence is separate from risk.**

## Principle 6

**Data quality is a first-class signal.**

## Principle 7

**No leakage between training and test wells.**

## Principle 8

**Synthetic data supplements real data; it does not replace it.**

## Principle 9

**RAG provides evidence, not the core risk number.**

## Principle 10

**Engineer remains in the decision loop.**

---

# 252. FINAL ARCHITECTURE

```text
                         eRTMAC-NWIS
                              |
      +-----------------------+-----------------------+
      |                       |                       |
      v                       v                       v
   MODULE 1                MODULE 2                MODULE 3
 Document/Data            Geospatial              Knowledge
 Extraction               Wells                    Repository
      |                       |                       |
      +-----------------------+-----------+-----------+
                                      |
                                      v
                                  MODULE 4
                           Geological Correlation
                                      |
                         MD -> TVDSS -> Formation -> ξ
                                      |
                           Relevant Offset Evidence
                                      |
                    +-----------------+----------------+
                    |                                  |
                    v                                  v
             PHYSICS ENGINE                       LIVE DATA
                    |                                  |
                    v                                  v
             SENSOR MODEL                         WITSML/API
                    |                                  |
                    +----------------+-----------------+
                                     |
                                     v
                                  MODULE 5
                         Predictive Risk Analytics
                                     |
                      +--------------+--------------+
                      |              |              |
                      v              v              v
                  Rules         Anomaly ML      Historical
                                                   Evidence
                      |              |              |
                      +--------------+--------------+
                                     |
                                     v
                              Risk Fusion
                                     |
                        +------------+------------+
                        |                         |
                        v                         v
                     Risk                    Confidence
                        |
                        v
                    MODULE 6
               Alerts / Recommendations
                        |
                        v
                    MODULE 7
               Unified Command Cockpit
```

---

# 253. ONE-SENTENCE FINAL SPECIFICATION

> **Module 5 is a reduced-order, physics-informed real-time drilling digital twin that generates causally coupled telemetry from well, formation and operator states, derives engineering features, detects anomalies, fuses those signals with Module 4's stratigraphically correlated historical evidence, and produces hazard-specific risk, confidence and risk-corridor outputs for Module 6 decision support.**

---

# 254. SOURCE / RESEARCH REFERENCES

## WITSML / Energistics

WITSML overview:

https://docs.energistics.org/WITSML/WITSML_TOPICS/WITSML-000-002-0-C-sv2000.html

WITSML Log data object:

https://docs.energistics.org/WITSML/WITSML_TOPICS/WITSML-000-048-0-C-sv2000.html

WITSML trajectory data object:

https://docs.energistics.org/WITSML/WITSML_TOPICS/WITSML-000-039-0-C-sv2000.html

WITSML growing data objects / streaming:

https://docs.energistics.org/WITSML/WITSML_TOPICS/WITSML-000-030-0-C-sv2000.html

Trajectory data model:

https://docs.energistics.org/WITSML/WITSML_TOPICS/WITSML-000-041-0-C-sv2000.html

Trajectory best practices:

https://docs.energistics.org/WITSML/WITSML_TOPICS/WITSML-000-042-0-C-sv2000.html

## Volve

Equinor Volve data sharing:

https://www.equinor.com/energy/volve-data-sharing

## Public SIH26121 repository research

NWIS-Sentinel:

https://github.com/n3ssdub3y/SIH_2026_PLANNS

Example similarity implementation:

https://github.com/n3ssdub3y/SIH_2026_PLANNS/blob/main/NLP/nlp_task_ddr/module2/compute_similarity.py

pallavi-a11y implementation:

https://github.com/pallavi-a11y/eRTMAC-NWIS

tarumishra22 implementation:

https://github.com/tarumishra22/eRTMAC-NWIS

PetrolQ:

https://github.com/thor11223344/PetrolQ

---

# 255. FINAL IMPLEMENTATION RULE

The final system should always preserve this causal sequence:

```text
PHYSICAL WORLD / SIMULATION
        ↓
ENGINEERING STATE
        ↓
SENSOR OBSERVATION
        ↓
TELEMETRY
        ↓
PREPROCESSING
        ↓
DERIVED FEATURES
        ↓
ANOMALY / RULES / ML
        ↓
MODULE 4 GEOLOGICAL CONTEXT
        ↓
HISTORICAL EVIDENCE
        ↓
HAZARD-SPECIFIC RISK
        ↓
CONFIDENCE + DATA QUALITY
        ↓
MODULE 6
        ↓
ENGINEER
        ↓
OPERATOR RESPONSE
        ↓
PHYSICAL STATE CHANGES
```

**That loop is the definition of the Module 5 implementation.**
