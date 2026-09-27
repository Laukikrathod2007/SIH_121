# SIH 26121 — Oil India Limited vs. Global Industry Frontier: Digital Drilling Audit

## 1. Executive Summary
This document conducts a rigorous comparative audit between Oil India Limited's (OIL) digital drilling infrastructure and the operational frontier of global supermajors (Equinor, BP, Chevron, Shell, ExxonMobil). It analyzes OIL's current baseline (eRTMAC, Landmark Well Plan, Project DRIVE), identifies the five critical capability gaps preventing proactive decision support, and demonstrates how NWIS elevates OIL to international best-in-class performance.

---

## 2. Comparative Digital Drilling Capability Matrix

| Operational Capability | Global Supermajors (Equinor, BP, Chevron) | Oil India Limited Current Baseline (2026) | eRTMAC-NWIS Target State |
| :--- | :--- | :--- | :--- |
| **Real-Time Monitoring** | Centralized 24/7 RTOCs with automated anomaly detection across 50+ global rigs. | **eRTMAC (Duliajan):** 24/7 centralized monitoring across Assam/Arunachal rigs over WITS/WITSML. | Augmented 24/7 advisory overlay with sub-second hazard detection. |
| **Hydraulics & Well Plan** | Continuous real-time hydrodynamic twins updating ECD ahead-of-the-bit. | **Landmark Well Plan:** Pre-drill hydraulic simulations and static ECD curves. | Real-time sensor corroboration validating active SPP against offset models. |
| **Offset Well Utilization** | Automated spatial-stratigraphic offset retrieval integrated into drilling consoles. | **Manual Pre-Spud Review:** Offset wells reviewed during planning; rarely referenced dynamically while drilling. | **Dynamic Contextual Alignment:** Automated offset interval projection ahead of the bit. |
| **Historical Knowledge Access**| Natural language querying over structured knowledge graphs and indexed reports. | **Siloed PDF Archives:** DDRs, WCRs, and mud logs stored in network drives; keyword search only. | **Hybrid RAG + Bounding Box Proof:** Instant semantic search with verified PDF page displays. |
| **Early Hazard Prediction** | Multi-sensor ML models with 15–45 min lead times for kicks, sticking, and losses. | **Threshold Alarms:** Simple high/low buzzer alarms on rig floor (e.g. Pit Gain $> 1 \text{ m}^3$). | **Decoupled Physics-ML Models:** Early precursor pattern recognition with TreeSHAP explanations. |

---

## 3. The 5 Critical Operational Gaps at Oil India Limited

```
[THE 5 DIGITAL DRILLING GAPS AT OIL]
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ GAP 1: The "Institutional Memory Retirement" Cliff                                     │
│ • Decades of drilling expertise in complex Upper Assam thrust belts resides in the     │
│   minds of veteran superintendents rather than a queryable machine intelligence.       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ GAP 2: Static Pre-Spud vs. Dynamic In-Drilling Offset Intelligence                    │
│ • Offset well data is studied exhaustively before spudding, but remains static. When an│
│   unexpected formation pressure anomaly occurs at 2:00 AM, offset data is inaccessible.│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ GAP 3: The Measured Depth (MD) Trajectory Trap                                         │
│ • Historical events are logged in measured depth. Without subsea stratigraphic ratio   │
│   normalization, comparing deviated offset wells yields dangerously misleading alerts. │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ GAP 4: Vendor Cloud Lock-in & Multi-Crore Licensing                                    │
│ • Proprietary commercial suites (SLB DELFI, Halliburton Landmark Cloud) demand heavy   │
│   annual recurring fees and mandate transmitting proprietary data to external clouds.  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ GAP 5: Unvalidated Alert Fatigue on Rig Consoles                                       │
│ • Traditional threshold buzzers trigger frequent false alarms from pump surging,       │
│   causing drillers to mute safety systems and miss genuine precursors.                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. How NWIS Closes the Gap for Oil India Limited

1. **Codifies Institutional Knowledge:** Transforms thousands of legacy scanned DDRs from Moran, Nahorkatiya, and Digboi fields into an actionable, semantically queryable knowledge base.
2. **Projects the Historical Risk Corridor:** Continuously computes ahead-of-the-bit hazard windows ($z_{target} \pm 30\text{ m}$) as the drill bit advances through Upper Assam stratigraphy.
3. **Respects Data Sovereignty:** Executes 100% on-premise at Duliajan or directly on rig-floor IPCs without external cloud dependencies.
4. **Delivers Zero-Hallucination Auditability:** Provides the rig superintendent with a direct click to the original scanned PDF bounding box, eliminating skepticism.
5. **Complements Existing Investments:** Seamlessly interfaces with OIL's eRTMAC WITS streams and Landmark Well Plan files without disrupting operational workflows.

---

## 5. Architectural Verdict for SIH 26121

**Verdict:** `[MAXIMUM LEVERAGE OF OIL'S EXISTING STACK]`.
- NWIS is explicitly designed **not to replace eRTMAC or Well Plan**, but to serve as the **missing cognitive intelligence layer**.
- By presenting this positioning to the SIH jury, the team demonstrates deep operational empathy for OIL's actual business context rather than pitching an unrealistic, disruptive replacement.
