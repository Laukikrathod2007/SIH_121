# SIH 26121 — Torque Spikes & Torsional Dysfunction: Stick-Slip Analytics

## 1. Executive Summary
Torque spikes, torsional vibration, and stick-slip oscillations represent severe mechanical drilling dysfunctions responsible for drillstring twist-offs, downhole tool electronics failure, and premature PDC cutter destruction. This document analyzes downhole torsional vibration dynamics, Fast Fourier Transform (FFT) sensor precursors, recent 2024–2026 just-in-time learning literature, and historical operational mitigations.

---

## 2. Physical Mechanics of Stick-Slip & Torsional Resonance

Stick-slip is a nonlinear, self-excited torsional vibration of the drillstring caused by the difference between static and dynamic friction at the bit-rock interface:

```
[THE CYCLIC PHASES OF STICK-SLIP OSCILLATION]
Phase 1: "STICK" (0 to 3 Seconds)
├── Bit stops rotating completely (Downhole Bit RPM = 0).
├── Surface top drive continues rotating at constant speed (e.g. 100 RPM).
└── The 3,500m steel drill pipe winds up like a massive torsional spring, storing mechanical energy.
       │
       ▼
Phase 2: "SLIP / ACCELERATION" (3 to 4.5 Seconds)
├── Trapped torsional torque exceeds the static shear friction of the rock.
├── The bit violently breaks free, accelerating to 2× to 3× surface speed (Bit RPM > 280 RPM!).
└── PDC diamond cutters slam into rock faces at hyper-velocity, causing catastrophic impact micro-fractures.
       │
       ▼
Phase 3: "DECELERATION & RE-STICK" (4.5 to 6 Seconds)
└── Dynamic kinetic energy dissipates; the bit stalls again, repeating the cycle infinitely.
```

### Destructive Consequences of Unmitigated Stick-Slip:
1. **PDC Bit Delamination:** Impact shock shatters diamond cutter faces, reducing ROP from 25 m/hr to 3 m/hr.
2. **MWD/LWD Tool Failure:** High-g lateral and torsional shocks destroy downhole electronic circuit boards and battery packs.
3. **Drillstring Twist-Off:** Cyclic torsional fatigue shears drill collar tool joints, leaving a "fish" in the hole requiring days of expensive fishing operations.

`[VERIFIED: SPE Drilling & Completion Technical Papers; NOV Drilling Dysfunction Guidelines]`

---

## 3. Real-Time Telemetry Precursors & Spectral Detection

Stick-slip cannot be diagnosed from average 1-minute telemetry because the average smooths out the oscillations. It requires high-frequency (1-Hz to 10-Hz) sampling and spectral analysis:

```
[NORMAL ROTARY DRILLING: TORQUE PROFILE]
Torque: 14.2 kN·m ± 1.1 kN·m (Stable, low-variance Gaussian noise).

[STICK-SLIP ONSET: ERRATIC OSCILLATION PROFILE]
Torque swings violently between 6.5 kN·m and 24.8 kN·m every 3 to 6 seconds!
Variance ($\sigma^2_{TRQ}$) increases by over 400%.
```

### Engineering Detection Algorithms:
1. **Instantaneous Stick-Slip Severity Index ($I_{SS}$):**
   $$I_{SS} = \frac{\text{Torque}_{max} - \text{Torque}_{min}}{2 \cdot \text{Torque}_{mean}} \times 100\%$$
   - $I_{SS} < 30\%$: Normal, smooth drilling.
   - $30\% \le I_{SS} < 70\%$: Moderate stick-slip (advisory alert).
   - $I_{SS} \ge 70\%$: Severe full stick-slip (immediate operational intervention required).
2. **Fast Fourier Transform (FFT) Spectral Peak:**
   The fundamental torsional frequency of a drillstring is given by:
   $$f_0 = \frac{c_s}{4L} = \frac{3,200\,\text{m/s}}{4 \times 3,500\,\text{m}} \approx 0.23\,\text{Hz}$$
   An FFT spectral peak at $0.23$ Hz indicates active drillstring torsional resonance.

---

## 4. Academic Machine Learning Benchmarks in Literature

- **2024 ScienceDirect Benchmark (Journal of Petroleum Science and Engineering):**
  - *Title:* "Real-time drilling torque prediction ahead of the bit with just-in-time learning."
  - *Methodology:* Used Just-In-Time Learning (JITL) to predict torque profiles by matching current telemetry windows against historical offset drilling sequences.
  - *Benchmark Finding:* Outperformed global static neural networks, reducing torque root-mean-square error (RMSE) by 42% and successfully predicting severe torque spikes **10 to 15 meters prior to entering abrasive chert/limestone stringers**. `[RESEARCH-SUPPORTED: ScienceDirect 2024]`

---

## 5. Proven Engineering Mitigations from Offset Archives

When NWIS flags an approaching torque dysfunction corridor, it extracts proven operational countermeasures:

| Operational Parameter | Action | Physical Mechanism & Engineering Rationale |
| :--- | :--- | :--- |
| **Rotary Speed (RPM)** | **INCREASE (+15 to 30 RPM)** | Shifts operating point above the critical stick-slip resonance frequency curve. |
| **Weight on Bit (WOB)** | **DECREASE (-2 to 4 Tonnes)** | Reduces cutter depth of cut ($\delta$), lowering reactive rock torque. |
| **Drilling Mud Rheology** | **ADD LUBRICANT** | Spot 2–4% liquid ester/glycol drilling lubricant to reduce metal-to-casing and drillstring-to-rock friction coefficient ($\mu$). |
| **Surface Automation** | **ENGAGE SOFT TORQUE** | Activates automated top drive speed damping to absorb torsional vibration reflections. |
| **Wellbore Cleanout** | **WASH & REAM** | Back-ream tight intervals if torque spikes are caused by hole pack-off or ledges. |
