# eRTMAC-NWIS: Modules 5 and 6 — Predictive Risk Analytics and Real-Time Alerts
# Master Document 3 of 6

> An AI reading this file can build Modules 5 and 6 completely.
> Module 5: The 5-hazard predictive engine (telemetry-based early warning).
> Module 6: The alert tier system, rig-state FSM, and recommendation engine.
> HOW to verify the telemetry correlation is correct is fully explained.

---

## MODULE 5: Predictive Drilling Risk Analytics

### 5.1 The 5 Hazard Engines

The PS explicitly lists hazard types to detect. We model FIVE decoupled hazard engines,
each tuned to a specific physical process. They run in parallel on every telemetry packet.

HAZARD 1: Lost Circulation (LC) Detection
HAZARD 2: Stuck Pipe Early Warning
HAZARD 3: Gas Kick / Influx Detection
HAZARD 4: Torque and Drag Anomaly (Wellbore Instability)
HAZARD 5: Cement Job Failure (for post-cementing monitoring)

Why 5 DECOUPLED engines instead of one "general anomaly detector":
  A single autoencoder will not tell you WHICH hazard is occurring.
  The Barail Coal-Shale zone needs the Stuck Pipe engine TURNED UP and the Gas Kick engine
  ON because both hazards co-occur there. The Tipam needs only Lost Circulation.
  Decoupled engines mean: each engine has its own features, thresholds, and tuning.
  An alarm from Engine 2 (Stuck Pipe) has a SPECIFIC recommended action.
  An alarm from "general anomaly" has no actionable information.

### 5.2 HAZARD 1: Lost Circulation Detection

Physical Process: Drilling mud flows from the wellbore into the formation.
  Indicator 1 (PRIMARY): Flow Out < Flow In (mud going somewhere other than back up)
    delta_Q = MFIA - MFOA  (both in L/min)
    If delta_Q > THRESHOLD_LC for >T seconds -> LOST CIRCULATION
    THRESHOLD_LC = 150 L/min (adjustable per formation; lower in Tipam: 80 L/min)

  Indicator 2 (CONFIRMING): Standpipe Pressure DROP while pump rate is constant
    If (SPPA_current - SPPA_5min_avg) < -500 kPa while MFIA is stable -> confirms LC
    Reason: If mud is entering the formation, resistance drops, SPP drops.

  Indicator 3 (CONFIRMING): Pit volume DECREASING with no planned dump-off
    If TVOLUME rate-of-change < -0.05 m3/min -> additional confirmation

  Alert Logic:
    AMBER (Partial Loss): delta_Q > 80 L/min for >60 seconds
    RED (Total Loss): delta_Q > 250 L/min for >30 seconds
                   OR SPPA drops >1500 kPa with stable pump rate

  Feature vector for ML model (IsolationForest or LSTM):
    [delta_Q_60s, delta_Q_120s, SPPA_delta, TVOLUME_rate, ROPAV, DBTM_formation_xi]
    Training data: Volve dataset + synthetic Tipam zone events from our generator.

  Validation — How to know this is correct:
    PHYSICAL CHECK: A Lost Circulation event MUST have delta_Q > 0 (flow in > flow out).
    If the alarm fires when delta_Q <= 0, it is a false alarm. This is the ground truth.
    Cross-check with Volve dataset events where LC events are manually labelled in DDRs.
    Metric: Precision >= 0.85 (less than 15% false alarms at amber threshold).
    False alarm rate MUST be < 2 per 8-hour shift (otherwise engineers start ignoring alarms).

### 5.3 HAZARD 2: Stuck Pipe Early Warning

Physical Process: The drill string becomes immobile in the wellbore.
Two mechanisms in Upper Assam:
  A) Differential Sticking: Drill collar pressed against permeable formation by pressure differential.
     Occurs: Barail Lower Sand and Barail Coal-Shale while string is stationary during connections.
  B) Mechanical Sticking: Wellbore geometry problems (key seat, ledge, swelling shale).
     Occurs: Kopili shale transitions.

  Pre-Stuck Indicators (EARLY WARNING — 30-60 minutes before event):

  For Differential Sticking:
    Indicator 1: INCREASING Torque trend while WOB is constant (string drag increasing)
      TQA_trend = slope of TQA over last 30 minutes
      If TQA_trend > 0.5 kNm/hr while WOB < 0.5*WOB_normal -> AMBER sticky pipe warning

    Indicator 2: INCREASING Hookload on pickup vs rotating weight (overpull building)
      delta_HL = HKLA_pickup - HKLA_rotating
      If delta_HL > 50 kN -> AMBER
      If delta_HL > 150 kN -> RED (string approaching stuck condition)

    Indicator 3: STATIONARY STRING DURATION at connection depth in high-risk zone
      If rig_state = "SLIDE/CONNECTION" AND duration > 8 minutes AND xi_current in Barail_Coal:
        -> AMBER (differential sticking risk elevated; recommend string reciprocation)

  Fully Stuck Confirmation:
    RPM = 0 AND HKLA > HKLA_freehang + 200 kN -> RED (string is stuck)
    RPM = 0 AND no Torque response to applied rotation -> RED

  Validation — How to know stuck pipe detection works:
    In Volve DDRs, stuck pipe events are documented with exact time stamps.
    Run the pre-stuck detector on the 2-hour window BEFORE the stuck time.
    Check: Was the AMBER warning fired 20-60 minutes before the stuck event?
    Metric: True Positive Lead Time (TPLT) >= 20 minutes for 70% of events.
    This metric is SPECIFIC: not just "did it alarm" but "did it alarm EARLY ENOUGH?"

### 5.4 HAZARD 3: Gas Kick / Influx Detection

Physical Process: Formation fluid (gas, oil, or water) enters the wellbore.
Upper Assam risk zone: Barail Coal-Shale (coal seam gas), Kopili (overpressured shales).

  Indicators:
    Flow Out > Flow In (opposite of lost circulation!):
      delta_Q = MFIA - MFOA  (NEGATIVE = outflow > inflow = KICK)
      If delta_Q < -100 L/min for >30 seconds -> kick indicator

    Pit Gain:
      TVOLUME increasing when no deliberate pumping -> influx entering wellbore
      Rate: If TVOLUME_rate > +0.02 m3/min -> AMBER
             If TVOLUME_rate > +0.10 m3/min -> RED (significant influx)

    Pump Pressure Increase while Flow Out spikes:
      Gas expanding as it rises, displacing mud, increasing flow out and reducing backpressure.
      If SPPA INCREASES while MFOA INCREASES -> gas expansion in annulus -> RED

  CRITICAL distinction from LC:
    Lost Circulation: Flow Out < Flow In (delta_Q > 0) AND Pit Volume DECREASING
    Gas Kick:         Flow Out > Flow In (delta_Q < 0) AND Pit Volume INCREASING
    These are OPPOSITE signatures. A system that confuses them is dangerous.

  Validation:
    Run both LC and kick detectors on synthetic events with OPPOSITE delta_Q signs.
    LC detector MUST NOT alarm on kick events (delta_Q < 0).
    Kick detector MUST NOT alarm on LC events (delta_Q > 0).
    This cross-check is MANDATORY before demo.

### 5.5 HAZARD 4: Torque and Drag (Wellbore Instability)

Physical Process: Abnormal friction in the wellbore due to formation cave-ins, ledges,
key seats, or swelling shales.

  Indicators:
    High-Frequency Torque Oscillations (Stick-Slip):
      Normal drilling: torque oscillates within ±10% of mean
      Stick-slip: torque oscillates ±40%+ (string winds up, releases, winds up)
      Detection: CV(TQA) = std(TQA_60s) / mean(TQA_60s) > 0.30 -> stick-slip

    Increasing Drag on Tripping:
      While pulling out of hole (POOH), HKLA should be near free-rotating weight.
      If HKLA exceeds expected overpull curve by > 100 kN -> tight hole/ledge

    Reactive Torque on Backreaming:
      High torque with no WOB while backreaming -> shale closing around drill string

  Formation Context:
    This alarm is especially important in Kopili shale (4,700-5,200 m TVDSS).
    Activate tighter thresholds when xi puts bit in Kopili or Girujan zone.

### 5.6 HAZARD 5: Cement Job Failure

Physical Process: After running casing, the cement job may fail to isolate formations.
Monitored during post-cementing WOH (Waiting On Cement) period.

  Indicators:
    Casing Pressure Buildup: Unexpected pressure rise in casing annulus after cementing
    Return Mud Density Change: Lighter returns indicate cement contamination
    Time-to-First-Return anomaly: If cement starts returning earlier than calculated
                                   -> short job, channeling expected

  Data Source: This is not a 1-Hz telemetry signal; it is from cement job report forms.
  Module 5 reads the cement job report (from Module 1 OCR pipeline) and flags wells
  that had cement problems, surfacing this in Module 3 search results.

---

## MODULE 6: Real-Time Alerts and Recommendation Engine

### 6.1 The Three-Tier Alert System

TIER 1 — RED (Immediate Action Required):
  Event: Gas kick confirmed; Total lost circulation; Drill string fully stuck.
  Response time: Immediate (< 30 seconds after trigger).
  Display: Full-screen red banner with audio alarm + specific action checklist.
  Examples: "SHUT IN WELL IMMEDIATELY — Pit gain 0.8 m3 in 60 seconds"

TIER 2 — AMBER (Warning — Prepare Now):
  Event: Pre-stuck indicators building; Partial mud loss; Stick-slip detected.
  Response time: 5-30 minutes of preparation time available.
  Display: Amber sidebar panel, checklist of preparation steps, historical DDR evidence.
  Examples: "BARAIL COAL APPROACH in 45 m — 3 offset wells had stuck pipe here"

TIER 3 — BLUE (Information — Proactive Intelligence):
  Event: Formation change predicted; Offset well events at upcoming depth.
  Response time: 1-4 hours of preparation time available.
  Display: Blue info card, expandable DDR citations.
  Examples: "Entering Tipam Sandstone in ~180 m — Pre-mix LCM pill recommended.
             See NHK-089 DDR [2015-Day-142]: 30 bbl nut plug cured losses in 2 hrs."

### 6.2 The Rig State Finite State Machine (FSM)

Rig state is the foundation of all alert logic. The SAME sensor values mean completely
different things depending on what the rig is doing:
  SPP = 10,000 kPa is NORMAL during pumping; it is ALARMING during tripping (no pumps).
  Torque = 5 kNm is NORMAL during drilling; it is ALARMING when string should be static.

  The 8 Rig States we classify:

  State 1 — ROTARY_DRILLING:    RPM > 30, WOB > 20 kN, ROP > 1 m/hr, Pumps ON
  State 2 — SLIDE_DRILLING:     RPM < 5, WOB > 20 kN, ROP > 1 m/hr, Pumps ON (motor drilling)
  State 3 — CONNECTION:         RPM < 5, WOB < 5 kN, ROP = 0, Pumps OFF, HKLA = free-hang
  State 4 — CIRCULATING:        RPM < 5, WOB < 5 kN, ROP = 0, Pumps ON, DBTM stable
  State 5 — TRIPPING_IN:        RPM < 5, HKLA changing (dropping), ROP=0, Pumps OFF
  State 6 — TRIPPING_OUT:       RPM < 5, HKLA changing (rising), ROP=0, Pumps OFF
  State 7 — STATIONARY:         RPM=0, WOB=0, HKLA stable, Pumps OFF (survey/BOP test)
  State 8 — CEMENTING:          Pumps ON, SPPA stable, RPM=0, DBTM at casing shoe depth

  FSM Implementation (rule-based classifier, runs every 5 seconds):

  def classify_rig_state(telemetry):
      rpm = telemetry['RPM']
      wob = telemetry['WOB']
      hkla = telemetry['HKLA']
      sppa = telemetry['SPPA']
      mfia = telemetry['MFIA']
      rop = compute_rop(telemetry['DBTM'], window_seconds=60)

      if rpm > 30 and wob > 20 and rop > 1 and mfia > 200:
          return "ROTARY_DRILLING"
      elif rpm < 5 and wob > 20 and rop > 1 and mfia > 200:
          return "SLIDE_DRILLING"
      elif rpm < 5 and wob < 5 and mfia < 50 and abs(hkla - FREE_HANG_WEIGHT) < 50:
          return "CONNECTION"
      elif rpm < 5 and mfia > 200 and rop < 0.5:
          return "CIRCULATING"
      # ... etc.

  Alert thresholds CHANGE based on rig state:
    LOST_CIRCULATION threshold: Active during ROTARY_DRILLING, SLIDE_DRILLING, CIRCULATING
    STUCK_PIPE threshold: Active during ROTARY_DRILLING, SLIDE_DRILLING, CONNECTION
    KICK threshold: Active during ROTARY_DRILLING, CIRCULATING, CONNECTION
    TORQUE_DRAG threshold: Active during TRIPPING_IN, TRIPPING_OUT, ROTARY_DRILLING

### 6.3 The Recommendation Engine

When an alert fires, NWIS does NOT just say "WARNING: possible lost circulation".
It provides a SPECIFIC, EVIDENCE-BACKED recommendation drawn from offset well history.

Alert structure:
  {
    "alert_tier": "AMBER",
    "hazard_type": "LOST_CIRCULATION",
    "trigger": "Flow deficit 95 L/min sustained 90 seconds",
    "current_depth_md": 3215,
    "current_formation": "Tipam Sandstone",
    "xi_position": 0.42,

    "recommendation": {
      "immediate_action": "Reduce pump rate from 1400 to 900 lpm. Monitor flow out closely.",
      "preparatory_action": "Pre-mix 30 bbl medium nut plug LCM pill (40 ppb nut plug +
                             40 ppb calcium carbonate). Have ready to pump on short notice.",
      "evidence_basis": "3 offset wells had lost circulation at this stratigraphic position",
      "source_events": [
        {
          "well": "NHK-089",
          "depth_tvdss": 3228,
          "xi": 0.44,
          "severity": 4,
          "mitigation": "Mixed 30 bbl medium nut plug LCM pill. Pumped at reduced rate
                         1200 lpm. Losses reduced from 45 to 5 bbl/hr in 2 hrs.",
          "outcome": "SUCCESS",
          "doc_link": "/api/docs/NHK089_DDR_2015_D142.pdf",
          "highlight_bbox": [124, 340, 520, 360]
        }
      ]
    }
  }

The specific mitigation text (30 bbl nut plug, 40 ppb, 1200 lpm) comes DIRECTLY from
the extracted DDR text — it is not hallucinated. The LLM is used ONLY for formatting,
not for generating the numerical recommendations.

### 6.4 Alert Suppression (Anti-Spam Logic)

Without suppression, a gas kick alarm may fire 200+ times per 10-minute event.
Rules:
  - Once an alert fires at a given tier, do not re-fire the SAME alert type for 5 minutes.
  - If tier escalates (AMBER -> RED), override suppression immediately.
  - After engineer acknowledges alert, suppress for 15 minutes unless situation changes.
  - During CONNECTION state, suppress STUCK_PIPE amber until connection exceeds 10 minutes.

### 6.5 Telemetry Validation: How to Know Alerts Are Correct

Test 1 — Replay Validation (Most Important):
  Take a historical Volve drilling interval where a documented stuck pipe event occurred
  (timestamp of event known from DDR).
  Replay the telemetry data through the FSM + Hazard 2 engine.
  Measure: At what lead time before the documented event does the AMBER alert fire?
  Acceptance: AMBER fires 15-60 minutes before confirmed stuck pipe in 70%+ of test cases.

Test 2 — False Alarm Rate Measurement:
  Replay 8 hours of normal (no-event) drilling telemetry.
  Count the number of AMBER or RED alerts generated.
  Acceptance: < 2 false alarms per 8-hour shift.
  If >5 false alarms per shift: tighten thresholds before demo.

Test 3 — Physical Plausibility of Delta_Q Alerts:
  ALL lost circulation amber alerts must have MFIA > MFOA (flow in > flow out).
  ALL kick amber alerts must have MFOA > MFIA (flow out > flow in).
  Any alert violating this physical law is a software bug — fix before demo.

Test 4 — Cross-Formation Validation:
  During Gurjan/Girujan interval (surface clays), kick alerts should NOT fire.
  During Tipam interval (depleted sandstone), LC alerts should fire more readily.
  Run synthetic playback of each formation interval with appropriate threshold overrides
  active and confirm correct behavior per formation.

Test 5 — Rig State Sensitivity Check:
  Replay a CONNECTION event (pumps off, string static).
  Confirm: LC alarm does NOT fire (no pumps means delta_Q = 0 = meaningless).
  Confirm: Stuck pipe alarm DOES activate with longer connection time threshold.

### 6.6 The Lookahead Alert (Proactive — Module 6 Signature Feature)

The most powerful alert type — fires BEFORE the hazard zone, not after.

Triggered by: Risk corridor (computed in Module 4) showing HIGH risk at upcoming depth.
Condition: If risk_corridor[current_depth + 30m to 100m]["lost_circulation"] > 6.0 (scale 0-10)
            AND evidence from >= 2 offset wells

Action fired:
  BLUE (Proactive) alert: "ENTERING HIGH-RISK ZONE in ~50 m (current depth 3,165 m MD)
  Barail Coal-Shale historically causes stuck pipe in 3/5 ranked offset wells.
  Recommended preparation:
  1. Pre-mix 25 bbl diesel spotting pill — have ready at suction line.
  2. Plan to reciprocate string every 2 minutes during next connection.
  3. Increase mud density from 1.32 to 1.36 g/cc before this interval.
  Evidence: NHK-089 DDR 2015-D142, NHK-145 DDR 2019-D088, MOR-034 DDR 2020-D201"

This fires based PURELY on historical evidence, with ZERO telemetry anomaly yet.
This is the ahead-of-bit intelligence — 20 to 120 minutes BEFORE any sensor anomaly.
Telemetry-based alerts can only fire DURING or AFTER the event starts.
Historical correlation fires BEFORE.
NWIS combines BOTH: proactive (history) + reactive (telemetry) in a single unified view.

---

## Module 5 and 6 Full Validation Matrix

Scenario                | Expected Alert    | Telemetry Signature           | Pass Criteria
------------------------|-------------------|-------------------------------|------------------
Total lost circulation  | RED immediately   | delta_Q > 250 L/min          | Fires < 30 sec
Partial lost circulation| AMBER at 60s      | delta_Q 80-250 L/min         | Fires 60-90 sec
Gas kick                | RED at 30s        | TVOLUME gain > 0.1 m3/min   | Fires < 30 sec
Pre-stuck indicators    | AMBER at 30 min   | TQA trend + HKLA delta       | Fires > 15 min before
Fully stuck             | RED immediately   | RPM=0, HKLA > limit          | Fires < 15 sec
Stick-slip              | AMBER             | TQA CV > 0.30                | Fires within 2 min
Approaching Barail Coal | BLUE 50 m ahead   | Depth + risk corridor        | Fires before entering
Normal drilling         | NO alert          | All channels nominal         | Zero false alarms
Connection (pumps off)  | NO LC alert       | MFIA = 0                     | LC suppressed
Tripping out normal     | NO stuck alert    | HKLA normal overpull curve   | No false stuck alert


---
---
## SECTION 7: OPERATING ENVELOPES (Inspired by Geomine — Done Better)

### 7.1 What Operating Envelopes Are

An operating envelope is a set of SAVED parameter bounds that define safe drilling operation
for a specific formation/scenario. Think of it as a "safe flight envelope" for drilling.

  Example envelope for "Tipam Sandstone Drilling - Nahorkatiya":
    ROP:       4 – 18 m/hr   (too fast = formation damage; too slow = bit balling)
    WOB:       40 – 120 kN   (too high in depleted zone = lost circ from induced fractures)
    RPM:       60 – 120 rpm  (too low = bit whirl; too high = string fatigue)
    Torque:    2.0 – 6.0 kNm (within this range = clean hole)
    SPP:       9,000 – 14,000 kPa  (normal circulating pressure range)
    Mud Wt:    1.30 – 1.42 g/cc (below pore pressure, above wellbore collapse)
    Flow In:   1,200 – 1,600 L/min

  Geomine has this. We must too. OUR ADDITION: envelopes are not manually entered —
  they are AUTOMATICALLY POPULATED from offset well statistics.

### 7.2 Auto-Population from Offset Well Data

  For each formation zone, NWIS calculates envelope bounds from offset well history:
    rop_envelope = {
        "min": percentile(offset_wells_in_formation.rop_values, 10),
        "max": percentile(offset_wells_in_formation.rop_values, 90),
        "warning_min": percentile(..., 5),
        "warning_max": percentile(..., 95),
    }

  This is better than Geomine's manually configured envelopes because:
  - They are DERIVED from actual historical performance, not engineering guesses.
  - They UPDATE as new wells are drilled and ingested into the database.
  - They CHANGE automatically as the bit crosses formation boundaries (xi calculation triggers
    envelope swap from Tipam parameters to Barail parameters).

### 7.3 Envelope Breach Alert Logic

  AMBER breach: Any parameter outside warning bounds for > 30 seconds
  RED breach: Any parameter outside absolute bounds for > 15 seconds
  
  Display: Each telemetry gauge has a background zone visualization:
    - Green zone: within envelope
    - Amber zone: approaching limit
    - Red zone: outside envelope
  The gauge needle/bar color changes as it enters each zone.

  Formation envelope auto-swap:
    When xi calculation detects formation change (xi crosses 0 or 1):
      notify_engineer(f"Formation change: entering {new_formation}. "
                      f"Operating envelope updating automatically.")
      activate_envelope(new_formation)

---

## SECTION 8: ANTI-COLLISION MONITOR

### 8.1 What It Is

When multiple wells are drilled in a tight cluster (like in Nahorkatiya pad drilling),
there is risk that the NEW well's trajectory comes dangerously close to an existing wellbore.
Anti-collision monitoring computes the closest approach distance (SAFD — Separation Factor Distance)
between the active well and all neighboring wellbores in 3D space.

Geomine mentions this. We implement it properly.

### 8.2 SAFD Calculation

  For each survey station in the active well:
    active_point = (North_active, East_active, TVDSS_active)  # 3D coordinates from min-curvature

  For each offset well, at the nearest corresponding depth:
    offset_point = (North_offset, East_offset, TVDSS_offset)  # interpolated from survey

  3D separation distance:
    distance_3D = sqrt((N_a - N_o)^2 + (E_a - E_o)^2 + (TVDSS_a - TVDSS_o)^2)

  Ellipse of uncertainty (accounts for survey tool errors):
    sigma_a = survey_uncertainty_a (function of depth and tool type)
    sigma_o = survey_uncertainty_o
    combined_uncertainty = sqrt(sigma_a^2 + sigma_o^2)

  SAFD = distance_3D / combined_uncertainty
    SAFD > 1.5: GREEN (safe separation)
    SAFD 1.0-1.5: AMBER (plan review recommended)
    SAFD < 1.0: RED (STOP DRILLING — collision risk)

### 8.3 Anti-Collision Display

  On the 3D trajectory visualization panel:
    - Active well shown as animated line (green, growing downward in real time)
    - All offset wells shown as static lines (gray)
    - SAFD value displayed as a badge on the closest offset well
    - When SAFD < 1.5: closest approach line drawn in amber between the two wells
    - When SAFD < 1.0: RED alert + drill string stop recommendation

  Note: This is a SAFETY feature, not a geological correlation feature. Separate from Omega ranking.
  Offset wells used for anti-collision include ALL nearby wells regardless of Omega score.

---

## SECTION 9: STICK-SLIP PHYSICS ENGINE

### 9.1 Why Physics Over Pure ML

Geomine explicitly states they use a "real-time physics engine" for stick-slip detection —
NOT just an ML anomaly detector. This is the correct engineering approach and we must match it.

Why physics is better for stick-slip:
  - ML detects anomalies AFTER they are well-established in the sensor data.
  - A physics model can predict the TENDENCY toward stick-slip before full oscillation develops.
  - Physics gives engineers a causal explanation: "String overspeed indicates bit has released
    from sticking — it will re-stick in approximately 2-4 seconds at current RPM."
  - No training data required. Equations are derived from drill string mechanics.

### 9.2 The Torsional Drill String Model

The drill string behaves as a torsional oscillator (rotating mass on a spring):
  - The top drive motor applies a constant torque T_applied.
  - The bit has Coulomb friction with the formation (stick-slip friction model).
  - When bit RPM = 0 (stuck), motor winds up the string like a spring.
  - When static friction is overcome, the bit releases suddenly (overspeed event).

  Simplified 2-DOF torsional model:
    I_td * d(omega_td)/dt = T_applied - k_ts * (theta_td - theta_bit) - c_ts * (omega_td - omega_bit)
    I_bit * d(omega_bit)/dt = k_ts * (theta_td - theta_bit) + c_ts * (omega_td - omega_bit) - T_bit_friction

  Where:
    I_td = top drive rotational inertia
    I_bit = bit + BHA rotational inertia
    k_ts = torsional stiffness of drill string (function of string length and diameter)
    c_ts = torsional damping
    omega = angular velocity (RPM converted to rad/s)
    theta = angular position
    T_bit_friction = Coulomb friction torque (Wicker-Sinha model)

  Bit friction model (Wicker-Sinha):
    If |omega_bit| < omega_threshold:
      T_friction = T_static * sign(omega_bit)  # static friction
    else:
      T_friction = T_dynamic + (T_static - T_dynamic) * exp(-gamma * omega_bit^2)  # kinetic

### 9.3 Physics Engine State Outputs

  At each telemetry tick (1 Hz), the physics model outputs:
    predicted_bit_rpm: What the bit is doing (model state, not sensor)
    stick_slip_severity: 0-1 scale (0 = no stick-slip, 1 = severe)
    time_to_restick: Predicted seconds until next stick event
    recommended_rpm_reduction: How much to reduce surface RPM to dampen oscillation

  Stick-slip severity classification:
    0.0 – 0.2: SMOOTH (no action needed)
    0.2 – 0.5: MILD stick-slip (BLUE info: "Reduce WOB by 10%")
    0.5 – 0.8: MODERATE stick-slip (AMBER: "Reduce RPM by 15%, increase flow rate")
    0.8 – 1.0: SEVERE stick-slip (RED: "Reduce WOB to near-zero. String fatigue risk.")

### 9.4 Parameters Required for Physics Model

    string_length_m: current bit depth (DBTM) — from telemetry
    string_od_inch: from well program (loaded at session start)
    drill_collar_length_m: from BHA schematic (loaded at session start)
    formation_type: from xi calculation (Tipam sandstone vs Barail Coal have different bit friction)

  K_torsional_stiffness = G * J / L
    G = shear modulus of steel (80 GPa)
    J = polar moment of inertia of drill pipe cross-section (from OD, ID)
    L = current string length (= DBTM)

  Formation friction coefficients (calibrated for Upper Assam):
    Tipam Sandstone: T_static = 2.5 * WOB, T_dynamic = 1.8 * WOB (moderate friction)
    Barail Coal-Shale: T_static = 4.0 * WOB, T_dynamic = 1.2 * WOB (HIGH stick propensity)
    Kopili Shale: T_static = 3.5 * WOB, T_dynamic = 1.5 * WOB (reactive shale)

  This means: In Barail Coal, the HIGH ratio of static-to-dynamic friction means once the bit
  releases, it overspeeds VIOLENTLY. The physics model predicts the severity BEFORE it peaks.

### 9.5 OUR ADVANTAGE OVER GEOMINE ON STICK-SLIP

  Geomine: Has a "torsional stick-slip physics engine." We cannot verify their implementation.
  NWIS: Our physics model is FORMATION-AWARE. The bit friction coefficients CHANGE when xi
  calculation puts the bit in Barail Coal-Shale (high risk) vs Tipam Sandstone (lower risk).
  Geomine likely uses a generic drill string model.
  NWIS uses formation-specific friction parameters derived from Upper Assam drilling history.
  This makes our stick-slip predictions MORE ACCURATE for OIL fields specifically.
