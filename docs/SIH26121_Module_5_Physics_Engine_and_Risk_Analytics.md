# SIH26121 eRTMAC-NWIS — Module 5
# Real-Time Predictive Drilling Risk Analytics + Physics-Based Telemetry Engine

> **Purpose**
>
> This document defines how we will build Module 5 as an actual real-time drilling simulation and predictive-risk system.
>
> The core principle is:
>
> **Do not generate random sensor values. Build a reduced-order drilling physics engine that produces physically coupled telemetry, then let the Module 5 analytics engine interpret that telemetry.**
>
> This is a hackathon-scale digital twin, not a replacement for a commercial high-fidelity drilling simulator.

---

## 1. What Module 5 Does

Module 4 answers:

> **Where is the active well relative to historical geological/drilling experience?**

Module 5 answers:

> **Given the current drilling state, live telemetry, geological context, and historical offset evidence, what hazards should we be watching for?**

The five hazard families specified for the production system are:

1. Lost Circulation
2. Stuck Pipe
3. Kick / Overpressure
4. Torque & Drag Dysfunction
5. Cementing Integrity

The risk system should combine:

- current simulated/live telemetry,
- derived drilling features,
- Module 4 geological correlation,
- historical offset-well events,
- anomaly detection,
- deterministic engineering rules,
- optional ML models,
- data-quality/confidence information.

Do not present a naked number such as `85% risk` without explaining the evidence behind it.

---

## 2. Full System Position

```text
                    MODULE 1
       Historical DDR / WCR Extraction
                         |
                         v
                Structured Well Data
                         |
              +----------+----------+
              |                     |
              v                     v
      Formation tops             NPT events
              |                     |
              +----------+----------+
                         |
                         v
                    MODULE 4
            Geological Correlation
                         |
            MD -> TVDSS -> Formation -> xi
                         |
                         v
              Relevant Offset Wells
                         |
                         v
                Historical Evidence
                         |
                         |
REAL-TIME TELEMETRY <----+--------------------+
        ^                                      |
        |                                      v
        |                              MODULE 5
        |                         Predictive Risk Engine
        |                                      |
        |                       +--------------+--------------+
        |                       |              |              |
        |                       v              v              v
        |                      LC             SP            Kick
        |                       |              |              |
        |                       +--------------+--------------+
        |                                      |
        |                              Torque / Drag
        |                                      |
        |                              Cement Integrity
        |                                      |
        |                                      v
        |                             Risk Fusion Layer
        |                                      |
        |                       +--------------+-------------+
        |                       |                            |
        |                       v                            v
        |                  Risk State                   Evidence
        |                  Confidence                    Quality
        |                       |                            |
        |                       +-------------+--------------+
        |                                     |
        |                                     v
        |                                MODULE 6
        |                        Alerts + Recommendations
        |                                     |
        |                                     v
        +-------------------------------- MODULE 7
                                 Unified Drilling Cockpit
```

---

## 3. What Makes This a Real Digital Twin

A weak SIH implementation does this:

```python
flow_out = random.uniform(...)
torque = random.uniform(...)
rop = random.uniform(...)
risk = random.uniform(...)
```

That is only animation.

Our simulator instead does:

```text
Operator commands
    +
Formation properties
    +
Well trajectory
    +
Mud properties
    +
Drillstring properties
    +
Physical relationships
    |
    v
Physics state
    |
    v
Sensor model
    |
    v
Telemetry
    |
    v
Module 5
```

Example:

```text
BHP > fracture pressure
        |
        v
Formation takes fluid
        |
        v
Q_loss increases
        |
        v
Flow-out decreases
        |
        v
Pit volume decreases
        |
        v
Flow imbalance anomaly
        |
        v
Module 5 raises LC risk
```

This causal chain is the main goal.

---

## 4. Reduced-Order, Real-Time Philosophy

We are NOT trying to recreate a commercial simulator such as Drillbench.

A high-fidelity drilling simulator can include:

- transient multiphase hydraulics,
- fluid compressibility,
- detailed PVT,
- temperature,
- complex rheology,
- cuttings transport,
- drillstring vibration,
- torsional dynamics,
- surge/swab,
- formation mechanics,
- well-control transients.

For SIH, we build a **reduced-order model** that:

- runs in real time,
- is deterministic,
- is computationally cheap,
- is physically interpretable,
- can create realistic hazard signatures,
- can be calibrated against historical data later.

The architecture should allow modules to be upgraded individually.

---

## 5. Core Physics Subsystems

Build these subsystems:

```text
1. Formation / geology model
2. Drilling mechanics
3. Hydraulics
4. Pressure / well-control interaction
5. Drillstring torque & drag
6. Hole cleaning / cuttings transport
7. Fault/scenario injection
8. Sensor model
9. Real-time telemetry transport
```

---

## 6. Subsystem 1 — Formation Model

The simulator needs an underground model.

Example:

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
    },
    {
      "name": "Barail Coal-Shale",
      "top_tvdss": 2200,
      "base_tvdss": 3300,
      "rock_density_gcc": 2.35,
      "ucs_mpa": 60,
      "youngs_modulus_gpa": 12,
      "poisson_ratio": 0.30,
      "porosity": 0.08,
      "permeability_md": 5,
      "pore_pressure_gcc": 1.15,
      "fracture_gradient_gcc": 1.65,
      "friction_coefficient": 0.35,
      "leakoff_coefficient": 0.005
    }
  ]
}
```

These are **demo/calibration parameters**. Do not present them as verified OIL field constants.

---

## 7. Formation Parameters We Need

Each formation should expose:

```text
top TVDSS
base TVDSS
thickness

rock density
UCS
Young's modulus
Poisson ratio

porosity
permeability

pore pressure
fracture gradient

friction coefficient
drillability coefficient
leakoff coefficient
```

The simulator uses the current TVDSS to identify the active formation.

```text
Current TVDSS
      |
      v
Formation lookup
      |
      v
Formation properties
      +--> rock strength
      +--> pressure
      +--> friction
      +--> hydraulics response
      +--> loss/influx behaviour
```

---

## 8. Subsystem 2 — Well / Trajectory

The well trajectory comes from directional survey data:

```text
MD
Inclination
Azimuth
```

Use Module 4's trajectory handling to convert:

```text
MD
 |
 v
Minimum Curvature
 |
 +--> TVD
 +--> TVDSS
 +--> Northing
 +--> Easting
```

For the simulator, depth is not simply:

```text
TVDSS = MD
```

unless a vertical-well assumption is explicitly enabled.

---

## 9. Main State Object

Create one central simulation state:

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

The state is the internal "truth".

The telemetry layer observes this state.

---

## 10. Subsystem 3 — Drilling Mechanics

### 10.1 ROP

ROP = **Rate of Penetration**.

Use a reduced-order model such as:

```text
ROP = alpha * RPM * (WOB / Db)^b
```

with calibration terms for the formation and bit.

Conceptual behaviour:

```text
WOB increases
    -> ROP tends to increase

RPM increases
    -> ROP tends to increase

Rock strength increases
    -> ROP tends to decrease
```

Use saturation/diminishing-return terms so that ROP does not become physically absurd.

---

## 11. Depth Evolution

Depth should be integrated continuously.

Conceptually:

```text
dMD/dt = ROP
```

Therefore:

```text
MD_next = MD_current + ROP * dt
```

Then:

```text
MD
 |
 v
Trajectory engine
 |
 v
TVDSS
```

This is what makes the simulated bit actually travel through formations.

---

## 12. Mechanical Specific Energy — MSE

MSE = **Mechanical Specific Energy**.

A useful reduced formulation is:

```text
MSE =
    axial energy contribution
    +
    rotational energy contribution
```

One common simplified form is:

```text
MSE =
WOB / Ab
+
(T * omega) / (Ab * ROP)
```

where:

```text
WOB = weight on bit
Ab  = bit area
T   = torque
omega = angular velocity
ROP = rate of penetration
```

Use MSE primarily as a **drilling-efficiency / dysfunction feature**.

Do not treat a high MSE value alone as proof of a specific hazard.

---

## 13. Subsystem 4 — Hydraulics

The hydraulic loop is:

```text
Mud pumps
   |
   v
Drillpipe
   |
   v
BHA / bit
   |
   v
Annulus
   |
   v
Surface return
```

Model:

- flow rate,
- fluid density,
- geometry,
- hydrostatic pressure,
- frictional pressure loss,
- bit pressure loss,
- annular pressure,
- standpipe pressure,
- ECD.

---

## 14. Flow Velocity

Pipe or annular velocity:

```text
v = Q / A
```

For a simplified annulus:

```text
A_annulus = pi/4 * (Dh^2 - Dp^2)
```

then:

```text
v_annulus = Q / A_annulus
```

This gives a physical connection between pump rate, geometry and circulation behaviour.

---

## 15. Hydrostatic Pressure

Hydrostatic pressure is approximately:

```text
Ph = rho * g * h
```

where:

```text
rho = mud density
g   = gravity
h   = vertical depth
```

Use consistent SI units internally.

Convert to field units only at the API/UI boundary.

---

## 16. Frictional Pressure Loss

For the MVP, use a reduced friction model:

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
v = velocity
```

The friction factor can initially use simplified laminar/turbulent correlations.

Later upgrades:

```text
Power-law rheology
Bingham plastic
Herschel-Bulkley
temperature dependency
transient hydraulics
```

---

## 17. Standpipe Pressure

Approximate:

```text
SPP =
pipe pressure loss
+
BHA pressure loss
+
bit pressure loss
```

Bit loss can initially use:

```text
deltaP_bit = K * Q^2
```

Therefore:

```text
Pump rate increases
        |
        v
Flow velocity increases
        |
        v
Friction increases
        |
        v
SPP increases
```

This is an important causal relationship in the telemetry.

---

## 18. ECD

ECD = **Equivalent Circulating Density**.

Conceptually:

```text
ECD = effective bottomhole pressure converted to equivalent density
```

Approximate relationship:

```text
rho_ECD = P_bottomhole / (g * TVD)
```

with correct pressure datum and unit handling.

Use ECD to compare the circulating pressure state against:

```text
pore pressure
fracture pressure
```

---

## 19. Pressure Window

At every depth maintain:

```text
Pore Pressure
Fracture Pressure
BHP
ECD
Mud Weight
```

The main margins are:

```text
PP_margin = BHP - PorePressure

FG_margin = FracturePressure - BHP
```

Interpretation:

```text
BHP < Pore Pressure
    -> underbalanced condition
    -> kick/influx risk

BHP > Fracture Pressure
    -> formation breakdown / loss risk
```

Do not treat these thresholds as exact real-world operating limits without field-specific calibration.

---

## 20. Subsystem 5 — Lost Circulation Physics

Do not artificially modify flow-out.

Instead, make the formation accept fluid when the pressure condition is met.

For a reduced model:

```text
if BHP > fracture_pressure:

    Q_loss =
        C_loss *
        (BHP - fracture_pressure)^n
```

Otherwise:

```text
Q_loss = 0
```

Then the circulation balance becomes:

```text
Q_return =
    Q_in
    - Q_loss
    + Q_influx
```

So when losses begin:

```text
BHP > FG
     |
     v
Q_loss increases
     |
     v
Flow-out decreases
     |
     v
Pit volume falls
     |
     v
Module 5 sees negative flow imbalance
```

That is the desired physical chain.

---

## 21. Subsystem 6 — Kick / Influx Physics

For a simplified formation-influx model:

```text
if PorePressure > BHP:

    Q_influx =
        PI *
        (PorePressure - BHP)
```

where:

```text
PI = effective formation influx/productivity coefficient
```

Then:

```text
Pore Pressure > BHP
       |
       v
Formation fluid enters
       |
       v
Flow-out rises
       |
       v
Pit volume increases
       |
       v
Kick indicators appear
```

Again, this is a reduced-order demonstration model, not a full well-control simulator.

---

## 22. Mass / Volume Balance

Track the pit/active-fluid volume using:

```text
dVpit/dt =
    Qin
    + Qinflux
    - Qout
    - Qloss
```

This one equation is extremely useful because it connects several hazards.

### Lost circulation

```text
Qloss > 0
=> pit volume decreases
```

### Kick

```text
Qinflux > 0
=> pit volume increases
```

The pit-volume signal therefore emerges from the simulated state.

---

## 23. Subsystem 7 — Drillstring Model

Represent the drillstring as segments:

```text
Surface
 |
 +-- Drill Pipe
 +-- Drill Pipe
 +-- HWDP
 +-- Drill Collars
 +-- BHA
 +-- Bit
```

Each segment can contain:

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

For V1 we can use lumped or segmented calculations.

---

## 24. Torque Model

Torque should depend on:

- bit-rock interaction,
- formation strength,
- WOB,
- RPM,
- friction,
- drillstring torsion.

Use MSE and bit-work relationships as coupling terms.

The objective is:

```text
Formation changes
     |
     v
Required drilling energy changes
     |
     +--> WOB response
     +--> torque response
     +--> ROP response
```

This is more realistic than independent random gauges.

---

## 25. Torque & Drag

For the first model, approximate contact/friction:

```text
F_friction = mu * N
```

and torque contribution:

```text
T_friction = F_friction * r
```

where:

```text
mu = friction coefficient
N = normal contact force
r = effective radius
```

Accumulate forces/torque through the drillstring.

---

## 26. Stick-Slip Model

Stick-slip can be approximated with a torsional spring-damper model:

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
theta = torsional deformation
```

Introduce nonlinear static/dynamic bit friction.

Desired behaviour:

```text
Surface RPM approximately stable
           |
           v
Bit slows
           |
           v
Torsional energy accumulates
           |
           v
Bit releases / accelerates
           |
           v
RPM oscillation
```

Then Module 5 can detect the resulting oscillatory signature.

---

## 27. Subsystem 8 — Hole Cleaning

Drilling produces rock cuttings.

Approximate cuttings generation from:

```text
bit area
*
ROP
*
rock/volume correction
```

Then estimate annular solids concentration.

Conceptual chain:

```text
ROP increases
      |
      v
Cuttings generation increases
      |
      v
If annular velocity is insufficient
      |
      v
Cuttings concentration increases
      |
      v
Cuttings bed develops
      |
      v
Drag / torque increase
      |
      v
Stuck-pipe risk increases
```

This allows several telemetry channels to respond to one physical cause.

---

## 28. Subsystem 9 — Faults Must Change Physics, Not Sensors

This is one of the most important rules.

### WRONG

```python
if scenario == "loss":
    flow_out -= 250
```

### RIGHT

```text
Scenario changes formation leakoff / loss coefficient
        |
        v
BHP exceeds fracture condition
        |
        v
Physical loss flow appears
        |
        v
Flow-out and pit volume change
```

Likewise:

### Kick

Change:

```text
pore pressure
or
formation influx coefficient
```

### Stuck Pipe

Change:

```text
friction
and/or
cuttings accumulation
```

### Stick-Slip

Change:

```text
torsional damping
+
bit-rock nonlinear friction
```

### Washout

Change:

```text
effective hydraulic area / pipe integrity
```

The sensors respond to those physical changes.

---

## 29. Scenario Model

Create explicit scenarios:

```python
scenarios = {
    "NORMAL": {...},

    "TIPAM_LOST_CIRCULATION": {
        "start_depth_tvdss": 3230,
        "parameters": {
            "leakoff_multiplier": 4.0
        }
    },

    "OVERPRESSURE": {
        "start_depth_tvdss": 3060,
        "parameters": {
            "pore_pressure_multiplier": 1.12,
            "influx_coefficient_multiplier": 3.0
        }
    },

    "STUCK_PIPE": {
        "start_depth_tvdss": 3120,
        "parameters": {
            "friction_multiplier": 2.5,
            "cuttings_buildup_multiplier": 2.0
        }
    },

    "STICK_SLIP": {
        "start_depth_tvdss": 3180,
        "parameters": {
            "torsional_damping_multiplier": 0.5,
            "bit_static_friction_multiplier": 1.5
        }
    }
}
```

These values are simulation parameters, not claims about real OIL conditions.

---

## 30. Sensor Model

The physics state is NOT telemetry.

Real sensors have:

- noise,
- bias,
- delay,
- quantization,
- drift,
- missing packets,
- outliers.

Use a simple model:

```text
measurement =
scale * true_value(t - delay)
+
bias
+
noise
```

For each sensor configure:

```text
sampling rate
latency
noise sigma
bias
drift rate
minimum
maximum
resolution
dropout probability
```

---

## 31. Example Sensor Model

True state:

```text
flow_out = 1980.3 L/min
```

Sensor output:

```text
1982
1977
1984
1981
1979
```

For pressure:

```text
true SPP = 156.2 bar
sensor   = 156.8 bar
```

The analytics layer should see the imperfect telemetry, not the hidden true value.

---

## 32. Telemetry Channels

Minimum V1 channels:

| Channel | Unit |
|---|---|
| MD | m |
| TVDSS | m |
| ROP | m/hr |
| RPM | rpm |
| WOB | kN |
| Torque | kN·m |
| Hookload | kN |
| Flow In | L/min |
| Flow Out | L/min |
| Standpipe Pressure | bar |
| Annular Pressure | bar |
| Pit Volume | m³ |
| Mud Weight | g/cc |
| ECD | g/cc |
| MSE | MPa |
| d-exponent | dimensionless |
| Inclination | deg |
| Azimuth | deg |
| Temperature | °C |

Design the telemetry interface so a future real WITSML source can feed Module 5 using the same interface.

---

## 33. Real-Time Simulation Loop

Recommended architecture:

```text
Physics internal timestep:
10–20 Hz

Telemetry publication:
5–10 Hz

Database persistence:
1–2 Hz or batches

Frontend rendering:
5–10 Hz
```

Example:

```python
while simulation_running:

    commands = rig.get_commands()

    formation = geology.get_formation(state.tvdss)

    drilling.update(state, commands, formation, dt)

    state.md += state.rop * dt

    state.tvdss = trajectory.md_to_tvdss(state.md)

    hydraulics.update(state, formation, dt)

    pressure.update(state, formation, dt)

    drillstring.update(state, formation, dt)

    hole_cleaning.update(state, formation, dt)

    faults.apply(state, formation, dt)

    telemetry = sensors.observe(state, dt)

    websocket.publish(telemetry)

    historian.write(telemetry)

    sleep(dt)
```

---

## 34. Module 5 Feature Engine

Do not feed raw telemetry directly into the final hazard model only.

Generate derived features.

### Lost Circulation features

```text
delta_flow
rolling_delta_flow
flow imbalance
duration below threshold
pit volume slope
pit volume acceleration
BHP - fracture pressure
mud-weight margin
historical LC count
historical LC severity
historical ξ proximity
```

### Stuck Pipe features

```text
overpull
overpull slope
hookload trend
torque
torque variance
MSE
MSE anomaly
ROP decrease
cuttings concentration
friction estimate
historical stuck-pipe count
historical ξ proximity
```

### Kick features

```text
pit gain
pit gain rate
flow-out minus flow-in
ROP drilling break
d-exponent deviation
BHP - pore pressure
mud-weight margin
historical kick count
historical overpressure count
historical ξ proximity
```

### Torque/Drag features

```text
torque mean
torque variance
torque oscillation amplitude
RPM variance
stick-slip index
drag estimate
MSE
trajectory inclination
dogleg severity
```

### Cementing features

```text
previous cement failures
CBL failure rate
cement-job quality
formation
casing section
previous losses/kicks in cement interval
data confidence
```

---

## 35. Hazard Engine 1 — Lost Circulation

Inputs:

```text
Live:
    delta flow
    pit trend
    BHP
    fracture margin

Historical:
    offset LC frequency
    severity
    ξ distance
    relevant wells
```

Conceptual logic:

```text
Live flow imbalance
        +
Persistent pit-volume decline
        +
BHP approaching/exceeding fracture pressure
        +
Historical LC evidence
        |
        v
Lost Circulation risk
```

Use persistence and rolling statistics. Do not trigger on one noisy sample.

---

## 36. Hazard Engine 2 — Stuck Pipe

Inputs:

```text
overpull
hookload
MSE
torque
torque variability
ROP
cuttings concentration
friction estimate
historical stuck-pipe evidence
```

Conceptual chain:

```text
Overpull rising
     +
Torque instability
     +
MSE anomaly
     +
ROP degradation
     +
Historical stuck-pipe cases at same ξ
     |
     v
Stuck Pipe risk
```

---

## 37. Hazard Engine 3 — Kick / Overpressure

Inputs:

```text
pit gain
flow imbalance
ROP drilling break
d-exponent trend
BHP / pore-pressure margin
historical kick evidence
historical overpressure evidence
```

Use multi-signal confirmation.

A single ROP spike is an anomaly, not proof of a kick.

Desired logic:

```text
ROP anomaly
   +
pit gain
   +
flow-out > flow-in
   +
low pressure margin
   |
   v
Kick / overpressure risk elevated
```

---

## 38. Hazard Engine 4 — Torque & Drag Dysfunction

Monitor:

```text
torque
RPM
stick-slip
drag
MSE
trajectory
```

Detect:

```text
oscillation
persistent torque elevation
unexpected drag increase
stick-slip behaviour
```

Then combine with historical well behaviour.

---

## 39. Hazard Engine 5 — Cementing Integrity

This should initially be mostly historical/contextual.

Inputs:

```text
formation
casing section
cement-job data
CBL / cement quality data
previous offset failures
loss/kick history during cementing
```

Do not fabricate a continuous sensor if no such data exists.

Instead show:

```text
Cement Integrity:
Elevated historical concern

Evidence:
3 / 7 relevant offsets reported cement issues
```

---

## 40. Risk Fusion

Each hazard engine should output something like:

```json
{
  "hazard": "LOST_CIRCULATION",
  "score": 0.81,
  "state": "ELEVATED",
  "evidence": {
    "live_anomaly": 0.70,
    "historical": 0.88,
    "physics_margin": 0.91
  },
  "confidence": 0.89,
  "data_quality": 0.96,
  "source_grounding": 1.0
}
```

Do not call `score` a probability unless the model has been properly calibrated.

---

## 41. Confidence != Risk

Example:

```text
Risk = HIGH
Confidence = LOW
```

could mean:

```text
only one offset well
formation top inferred
telemetry partially missing
weak historical evidence
```

Another case:

```text
Risk = HIGH
Confidence = HIGH
```

could mean:

```text
7 relevant offset wells
4 matching historical incidents
same formation
same ξ region
multiple live anomalies
high telemetry quality
```

Always show both.

---

## 42. Four-Pillar Evidence Display

Recommended UI:

```text
LOST CIRCULATION
────────────────────────────

Risk State
HIGH

Historical Evidence
HIGH
4 relevant wells
3 historical events

Live Anomaly
MODERATE
ΔQ = -130 L/min
persistent 7 min

Data Quality
96%

Source Grounding
100%
```

This is much more defensible than:

```text
87% RISK
```

---

## 43. Module 4 → Module 5 Interface

Module 4 should provide:

```json
{
  "active_well_id": "NHK-412",
  "depth_tvdss": 3040,
  "formation": "Tipam Sandstone",
  "xi": 0.63,
  "offsets": [
    {
      "well_id": "NHK-089",
      "omega": 0.87,
      "equivalent_tvdss": 3270,
      "historical_events": [...]
    }
  ]
}
```

Module 5 uses this as historical context.

This prevents the analytics engine from treating every nearby well as equally relevant.

---

## 44. RAG's Role

Do not make the LLM calculate raw risk.

### Physics / analytics engine:

```text
What is happening now?
Is the signal abnormal?
How strong is the hazard evidence?
```

### RAG:

```text
What happened previously?
Which historical cases are similar?
What did engineers do?
Which source document proves this?
```

Example:

```text
Module 5:
    LC risk = ELEVATED

        |

        v

RAG:
    3 similar historical cases

    Case 1:
    loss at equivalent ξ
    mitigation: LCM pill

    Case 2:
    partial loss
    mitigation: pump-rate reduction

    Case 3:
    total loss
    mitigation: cement
```

---

## 45. ML Strategy

Do not begin with an LSTM.

Use three layers.

### Layer 1 — Deterministic rules

Examples:

```text
persistent negative flow balance
+
BHP near/above fracture pressure
+
historical LC
```

### Layer 2 — Statistical anomaly detection

Use:

```text
rolling mean
rolling standard deviation
Z-score
EWMA
change-point detection
Isolation Forest
```

### Layer 3 — Supervised ML

Only after sufficient labelled data exists:

```text
XGBoost
Random Forest
LSTM
Temporal CNN
Transformer
```

Training labels need:

```text
well
time/depth
hazard
formation
event start
event end
severity
```

---

## 46. Why Hybrid is Better

Our intended architecture:

```text
                     Physics
                       |
                       v
                 Simulated state
                       |
                       v
                   Telemetry
                       |
             +---------+---------+
             |                   |
             v                   v
       Rule / physics      ML anomaly
          signals             score
             |                   |
             +---------+---------+
                       |
                       v
               Historical evidence
                       |
                       v
                  Fusion engine
                       |
              +--------+--------+
              |                 |
              v                 v
            Risk            Confidence
              |
              v
           Module 6
```

The simulator creates controlled scenarios.

Historical OIL data later calibrates the parameters.

---

## 47. Database Design

### telemetry

```text
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
temperature
inclination
azimuth
```

### derived_features

```text
id
well_id
timestamp
delta_flow
overpull
mse
d_exponent
torque_variance
rop_change
pit_gain
stick_slip_index
cuttings_concentration
pp_margin
fg_margin
```

### risk_scores

```text
id
well_id
timestamp
depth_tvdss
formation

lost_circulation_score
stuck_pipe_score
kick_score
torque_drag_score
cementing_score

confidence
data_quality
```

### risk_evidence

```text
risk_id
source_type
source_id
well_id
event_id
feature_name
feature_value
contribution
```

---

## 48. Telemetry Transport

Use a real-time transport layer:

```text
Physics Engine
      |
      v
Message / Event Layer
      |
      +--> WebSocket --> Dashboard
      |
      +--> Historian --> Database
      |
      +--> Module 5
```

WebSocket is enough for the hackathon cockpit.

Design a WITSML-compatible adapter so the exact same analytics interface can later consume real OIL feeds.

The simulator should not expose special fields that Module 5 relies on but a real telemetry source cannot provide.

---

## 49. Recommended Backend Structure

```text
physics-engine/
│
├── engine.py
├── state.py
├── clock.py
├── config.py
│
├── formation/
│   ├── formation_model.py
│   └── pressure_model.py
│
├── trajectory/
│   └── trajectory_model.py
│
├── drilling/
│   ├── rop_model.py
│   ├── bit_model.py
│   └── mse_model.py
│
├── hydraulics/
│   ├── mud_model.py
│   ├── pressure_loss.py
│   ├── ecd.py
│   └── pit_balance.py
│
├── drillstring/
│   ├── torque_drag.py
│   ├── torsional.py
│   └── axial.py
│
├── hole_cleaning/
│   └── cuttings_model.py
│
├── faults/
│   ├── lost_circulation.py
│   ├── kick.py
│   ├── stuck_pipe.py
│   ├── stick_slip.py
│   └── washout.py
│
├── sensors/
│   ├── sensor.py
│   ├── noise.py
│   ├── drift.py
│   └── failures.py
│
└── telemetry/
    ├── websocket.py
    ├── historian.py
    └── witsml_adapter.py
```

Separately:

```text
risk-engine/
│
├── features/
│   ├── flow.py
│   ├── torque.py
│   ├── pressure.py
│   └── drilling.py
│
├── hazards/
│   ├── lost_circulation.py
│   ├── stuck_pipe.py
│   ├── kick.py
│   ├── torque_drag.py
│   └── cementing.py
│
├── anomaly/
│   ├── statistics.py
│   └── isolation_forest.py
│
├── fusion/
│   └── risk_fusion.py
│
└── evidence/
    └── evidence_resolver.py
```

---

## 50. Live Simulation Control Panel

Build an operator/simulator screen:

```text
┌─────────────────────────────────────────────┐
│ DRILLING SIMULATOR                          │
├─────────────────────────────────────────────┤
│ Active Well: NHK-SIM-001                    │
│ Depth:       3218.4 m MD                    │
│ TVDSS:       3012.8 m                       │
│ Formation:   Tipam Sandstone                 │
│                                             │
│ RPM:         110 rpm                        │
│ WOB:          85 kN                         │
│ Pump Rate:   2100 L/min                     │
│ Mud Weight:  1.31 g/cc                      │
│                                             │
│ [ START ] [ PAUSE ] [ RESET ]              │
│                                             │
│ SCENARIOS                                   │
│ [ Normal ]                                  │
│ [ Lost Circulation ]                        │
│ [ Kick / Overpressure ]                     │
│ [ Stuck Pipe ]                              │
│ [ Stick-Slip ]                              │
│ [ Washout ]                                 │
└─────────────────────────────────────────────┘
```

The important part is that scenario buttons modify the **physics**, not the displayed telemetry.

---

## 51. Example: Normal Drilling

Initial:

```text
Depth = 2980 m TVDSS

Flow In = 2100 L/min
Flow Out = 2090 L/min
Pit = 80.1 m3
SPP = 155 bar
ROP = 14 m/hr
Torque = 18 kN.m

LC Risk = LOW
SP Risk = LOW
Kick Risk = LOW
```

---

## 52. Example: Lost Circulation Scenario

At a selected geological interval:

```text
BHP exceeds fracture pressure
```

Then:

```text
Qloss begins
    |
    +--> Flow-out falls
    +--> Pit volume falls
    +--> Flow delta becomes negative
    +--> Pressure response changes
```

Module 5:

```text
Live anomaly
    +
historical LC evidence at same ξ
    |
    v
LC risk increases
```

Module 6 can then generate the proactive warning.

---

## 53. Example: Kick Scenario

Formation enters an overpressured interval.

```text
Pore pressure > BHP
        |
        v
Qinflux increases
        |
        +--> Flow-out rises
        +--> Pit volume rises
        +--> Flow imbalance changes
        +--> Pressure behaviour changes
        +--> ROP / d-exponent may become anomalous
```

Module 5 should detect a multi-signal kick pattern.

---

## 54. Example: Stuck-Pipe Scenario

Increase friction and/or cuttings buildup.

```text
Cuttings concentration rises
        |
        v
Normal contact/friction rises
        |
        +--> torque rises
        +--> drag rises
        +--> overpull rises
        +--> ROP falls
        +--> MSE changes
```

Module 5 sees the correlated pattern.

---

## 55. Example: Stick-Slip Scenario

Use torsional dynamics.

Expected telemetry:

```text
Surface RPM:
110 110 111 109 110

Bit RPM:
112
118
75
125
64
131
```

with associated torque oscillation.

Module 5 detects:

```text
high-frequency torque variation
+
RPM oscillation
+
stick-slip index
```

and raises torque/drag dysfunction risk.

---

## 56. Closed-Loop Demonstration

The best SIH demonstration is:

```text
START
  |
  v
Normal drilling
  |
  v
Bit moves
  |
  v
Module 4 updates formation + ξ
  |
  v
Relevant offsets change
  |
  v
Historical evidence changes
  |
  v
Physics enters hazard interval
  |
  v
Telemetry starts changing
  |
  v
Module 5 detects anomaly
  |
  v
Historical evidence confirms context
  |
  v
Risk rises
  |
  v
Module 6 issues alert
  |
  v
Engineer changes operating parameter
  |
  v
Physics responds
  |
  v
Telemetry stabilizes
  |
  v
Risk falls
  |
  v
Alert clears
```

This gives a complete:

**state → sensor → analytics → decision → intervention → response**

loop.

---

## 57. Development Roadmap

### V1 — Minimum Physics Engine

Implement first:

```text
[ ] Formation model
[ ] MD progression
[ ] MD -> TVDSS
[ ] ROP
[ ] WOB / RPM
[ ] Basic hydraulics
[ ] Hydrostatic pressure
[ ] Friction pressure loss
[ ] SPP
[ ] BHP
[ ] ECD
[ ] Pore pressure
[ ] Fracture pressure
[ ] Pit volume balance
[ ] Flow in/out
[ ] MSE
[ ] Basic torque
[ ] Sensor noise
[ ] WebSocket telemetry
[ ] Scenario engine
```

Do this before advanced ML.

---

## 58. V2 — Better Physical Behaviour

```text
[ ] Drillstring segmented model
[ ] Torque & drag
[ ] Torsional dynamics
[ ] Stick-slip
[ ] Hole cleaning
[ ] Cuttings accumulation
[ ] Better mud rheology
[ ] Sensor drift
[ ] Sensor dropout
[ ] Washout model
[ ] Surge/swab approximation
```

---

## 59. V3 — Risk Analytics

```text
[ ] Flow anomaly detection
[ ] Overpull detection
[ ] MSE anomaly detection
[ ] Pit gain detection
[ ] d-exponent trend analysis
[ ] Stick-slip detection
[ ] Hazard-specific rules
[ ] Historical offset evidence
[ ] Module 4 ξ context
[ ] Confidence
[ ] Data quality
```

---

## 60. V4 — ML

```text
[ ] Isolation Forest
[ ] XGBoost / Random Forest
[ ] Feature importance
[ ] Hazard-specific predictive model
[ ] calibration
[ ] historical backtesting
```

Use ML only after the data pipeline and physics-derived features are trustworthy.

---

## 61. V5 — Field Calibration

When actual OIL data becomes available:

```text
Historical DDR / WCR
      |
      v
Formation / event extraction
      |
      v
Module 4 correlation
      |
      v
Historical feature distributions
      |
      v
Calibrate:
    alpha / beta ROP parameters
    pressure profiles
    loss coefficients
    friction
    bit response
    hazard thresholds
```

The public/demo simulator must clearly distinguish:

```text
DEMO / SYNTHETIC
vs
FIELD-CALIBRATED
vs
FIELD-OBSERVED
```

---

## 62. Validation Strategy

We need to validate at three levels.

### Physics validation

Check conservation and expected monotonic behaviour.

Examples:

```text
Pump rate ↑ -> hydraulic losses ↑

Mud density ↑ -> hydrostatic pressure ↑

WOB ↑ -> ROP generally ↑ within calibrated range

BHP > fracture pressure
    -> losses can begin

Pore pressure > BHP
    -> influx can begin
```

### Telemetry validation

Check that sensor values remain:

```text
within engineering ranges
continuous
time-ordered
unit-consistent
```

### Hazard validation

Inject a known scenario and verify:

```text
Lost circulation
    -> flow loss signature detected

Kick
    -> pit gain / influx signature detected

Stuck pipe
    -> torque + overpull + ROP degradation detected

Stick-slip
    -> torsional oscillation detected
```

---

## 63. Testing Philosophy

Each subsystem should have unit tests.

Example:

```text
test_hydrostatic_pressure()
test_annular_area()
test_pressure_loss()
test_rop_response_to_wob()
test_rop_response_to_formation_strength()
test_pit_volume_mass_balance()
test_loss_activation_above_fracture_pressure()
test_influx_activation_above_pore_pressure()
test_stick_slip_response()
test_sensor_noise_bounds()
test_tvdss_depth_progression()
```

Then scenario tests:

```text
test_lost_circulation_scenario()
test_kick_scenario()
test_stuck_pipe_scenario()
test_stick_slip_scenario()
```

---

## 64. Important Engineering Caveats

The simulator is a **reduced-order engineering model**.

Do not claim:

```text
"this predicts a real OIL well exactly"
```

without field calibration and validation.

Instead state:

```text
"NWIS uses a physics-informed, reduced-order drilling digital twin
for real-time simulation, anomaly detection, historical correlation,
and decision-support demonstration. Model parameters can be calibrated
against OIL field data."
```

This is technically much more defensible.

---

## 65. Recommended Data Flow

```text
                    Formation Model
                           |
                           v
Operator Commands --> Physics Solver
                           |
         +-----------------+----------------+
         |                 |                |
         v                 v                v
     Mechanics         Hydraulics       Formation
         |                 |                |
         +-----------------+----------------+
                           |
                           v
                       Well State
                           |
                           v
                       Sensor Model
                           |
                           v
                    Telemetry Stream
                           |
                           +------------------+
                           |                  |
                           v                  v
                       Module 5          Historian
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
           Hazard 1      Hazard 2      Hazard 3
             |             |             |
             +-------------+-------------+
                           |
                           v
                     Risk Fusion
                           |
                           v
                      Module 6
                           |
                           v
                      Module 7 UI
```

---

## 66. Final Target Architecture

```text
                         eRTMAC-NWIS
                              |
       +----------------------+----------------------+
       |                      |                      |
       v                      v                      v
 Historical Data         Spatial Wells         Live Simulator
       |                      |                      |
       v                      v                      v
    Module 1               Module 2           Physics Engine
       |                                             |
       +----------------------+----------------------+
                              |
                              v
                         Module 4
                  Geological Correlation
                              |
                MD -> TVDSS -> Formation -> ξ
                              |
                              v
                      Offset Evidence
                              |
                              v
                         Module 5
                   Predictive Risk Fusion
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
          Historical        Live            Physics
           evidence       anomalies         margins
             |                |                |
             +----------------+----------------+
                              |
                              v
                       Hazard Engines
                              |
        +-----------+---------+---------+-----------+
        |           |                   |           |
        v           v                   v           v
       LC          SP                 Kick       Torque/Drag
                              |
                              v
                         Cementing
                              |
                              v
                       Risk + Confidence
                              |
                              v
                         Module 6
                              |
                              v
                         Module 7
                              |
                              v
                    Unified Cockpit
```

---

## 67. The Core Principle

The implementation should always preserve this chain:

```text
PHYSICAL STATE
     ↓
ENGINEERING MODEL
     ↓
SENSOR MODEL
     ↓
LIVE TELEMETRY
     ↓
DERIVED FEATURES
     ↓
ANOMALY DETECTION
     ↓
MODULE 4 HISTORICAL CORRELATION
     ↓
HAZARD-SPECIFIC RISK
     ↓
EVIDENCE + CONFIDENCE
     ↓
MODULE 6 ALERT
     ↓
ENGINEER ACTION
     ↓
PHYSICAL RESPONSE
```

That is what turns Module 5 from a collection of gauges into an actual **real-time predictive drilling digital twin**.

---

## 68. Immediate Build Order

Do not implement everything at once.

### Milestone 1

```text
Formation
+
trajectory
+
MD/TVDSS
+
ROP
```

### Milestone 2

```text
Hydraulics
+
BHP
+
ECD
+
SPP
+
pit balance
```

### Milestone 3

```text
Torque
+
drag
+
MSE
+
hole cleaning
```

### Milestone 4

```text
Lost circulation
+
kick
+
stuck pipe
+
stick-slip scenario physics
```

### Milestone 5

```text
Sensor model
+
WebSocket
+
live dashboard
```

### Milestone 6

```text
Module 5 hazard engines
+
Module 4 correlation
```

### Milestone 7

```text
ML anomaly detection
+
historical backtesting
```

### Milestone 8

```text
Module 6 alerts
+
engineer response
+
closed-loop demo
```

---

## 69. The SIH Demo We Want

The final demo should let the evaluator see:

```text
DEPTH: 3,218 m
FORMATION: Tipam Sandstone
ξ: 0.63

                 LIVE WELL

RPM             110
WOB              85 kN
ROP              14 m/hr
FLOW IN        2100 L/min
FLOW OUT       2095 L/min
SPP             155 bar
PIT              80.2 m3
ECD             1.34 g/cc

        ↓ continue drilling ↓

DEPTH: 3,235 m

Module 4:
2 highly relevant offsets
same ξ region has historical LC events

Physics:
BHP approaches fracture gradient

Telemetry:
Flow imbalance worsening
Pit volume declining

Module 5:
LOST CIRCULATION
Risk: HIGH
Confidence: HIGH

Module 6:
PROACTIVE WARNING
Historical loss zone 18 m ahead

Engineer:
Changes operating parameters

Physics:
Loss rate decreases

Telemetry:
Flow returns toward balance

Module 5:
Risk falls

Module 6:
Alert clears
```

The simulator should make every step emerge from the underlying model.

---

## 70. Definition of Done

Module 5 is considered functional when:

```text
[ ] The well physically advances through depth
[ ] TVDSS updates with trajectory
[ ] Formation properties change with depth
[ ] ROP responds to WOB/RPM/formation
[ ] Hydraulic pressure responds to pump rate/mud density
[ ] Pit balance responds to losses/influx
[ ] Torque responds to drilling state
[ ] MSE is calculated
[ ] Stick-slip can be simulated
[ ] Sensor noise is present
[ ] Telemetry is streamed live
[ ] Module 4 correlation influences historical evidence
[ ] Five hazard engines operate independently
[ ] Risk includes evidence and confidence
[ ] Known injected scenarios produce recognizable signatures
[ ] Module 6 receives risk states
[ ] Engineer parameter changes affect the simulator
[ ] The resulting telemetry responds to that intervention
[ ] No "random risk score" is used as the core mechanism
```

---

## 71. One-Sentence Architecture Summary

> **NWIS Module 5 is a reduced-order, physics-informed real-time drilling digital twin that converts operator inputs and geological/formation parameters into causally coupled telemetry, then fuses those live signals with Module 4's stratigraphically correlated historical evidence to detect and quantify drilling hazards.**
