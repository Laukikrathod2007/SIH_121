# eRTMAC-NWIS ML Training Dataset & Preprocessing Report
**Document ID:** `docs/ML_DATASET_REPORT.md`  
**System:** eRTMAC-NWIS Module 5 Predictive Drilling Risk Analytics  
**Provenance Tier:** `SYNTHETIC` (Physics Digital Twin with Domain Randomization)  
**Standardized Internal Units:** SI System (m, s, Pa, kg/m³, N, N·m, m³/s)  
**Feature Grid Resolution:** 1.0 second canonical resampled grid  

---

## 1. Executive Summary & Provenance
Every record in this dataset originates from the reduced-order drilling physics digital twin, strictly validated through the automated **Synthetic Data Quality Gate**. No fabricated labels or unphysical values are permitted into the training pool.

- **Primary Data Sources:**
  1. `eRTMAC-NWIS Physics Engine` (reduced-order coupled digital twin).
  2. Upper Assam Basin geological sequence (Tipam Sandstone, Barail Sandstone, Barail Lower Sand, Kopili Formation).
  3. Domain-randomized mechanical and hydraulic properties ($±15\%$ rock strength, mud weights $1.22–1.34$ g/cc).

---

## 2. Dataset Dimensions & Class Distribution

| Metric | Measured Value |
| :--- | :--- |
| **Total Simulation Runs** | 7 |
| **Total Telemetry Records** | 840 |
| **Unique Wells** | 7 |
| **Total Time Span (Simulated)** | 840 seconds (14.0 minutes) |
| **Engineered Feature Count** | 55 |
| **Missing Data Ratio** | 0.00% (Sensor dropout handled via documented imputation) |

### Class Balance by Hazard Scenario
| Scenario Type | Records | Proportion (%) |
| :--- | :--- | :--- |
| `NORMAL` | 120 | 14.3% |
| `LOST_CIRCULATION` | 120 | 14.3% |
| `KICK_OVERPRESSURE` | 120 | 14.3% |
| `STUCK_PIPE` | 120 | 14.3% |
| `STICK_SLIP` | 120 | 14.3% |
| `WASHOUT` | 120 | 14.3% |
| `POOR_HOLE_CLEANING` | 120 | 14.3% |

### Event Phase Distribution
| Event Phase | Records | Proportion (%) |
| :--- | :--- | :--- |
| `EventPhase.NORMAL` | 120 | 14.3% |
| `EventPhase.PRE_EVENT` | 234 | 27.9% |
| `EventPhase.EVENT` | 306 | 36.4% |
| `EventPhase.RECOVERY` | 180 | 21.4% |

---

## 3. Strict Well-Level Splitting (Leakage Prevention)
To eliminate spatial and temporal data leakage, records are partitioned strictly at the well level. No single well appears across multiple partitions:

- **Training Wells (5 wells, 600 records):** `NHK-DEV-007, NHK-DEV-002, NHK-DEV-004, NHK-DEV-005, NHK-DEV-003`
- **Validation Wells (1 wells, 120 records):** `NHK-DEV-001`
- **Testing Wells (1 wells, 120 records):** `NHK-DEV-006`

---

## 4. Multi-Horizon Labeling Methodology
Labels are assigned deterministically based on simulation ground-truth fault onset without looking into future test feature vectors:
1. **Event Phases:** `NORMAL`, `PRE_EVENT` (warning precursor window $\le 600s$), `EVENT` (active dysfunction), `RECOVERY`.
2. **Predictive Time Horizons:** Binary classification targets for event occurrence within **5 min (300s)**, **10 min (600s)**, **20 min (1200s)**, and **30 min (1800s)**.
3. **Predictive Depth Horizons:** Ahead-of-bit event occurrence within **10m**, **20m**, **50m**, and **100m**.

---

## 5. Synthetic Data Quality Gate Results
All 7 runs successfully passed the quality gate criteria:
- **Range Verification:** ROP, WOB, RPM, SPP, and Pit Volume stayed within physical bounds.
- **Mass Balance Verification:** Pit volume changes matched integrated fluid losses and influxes ($|\Delta V_{pit} - \int (Q_{influx} - Q_{loss}) dt| < \epsilon$).
- **Scenario Activation:** Physical signatures emerged organically (e.g. Lost Circulation produced negative flow balance and pit decline; Kick produced positive influx and pit gain; Stuck Pipe produced overpull surge).
