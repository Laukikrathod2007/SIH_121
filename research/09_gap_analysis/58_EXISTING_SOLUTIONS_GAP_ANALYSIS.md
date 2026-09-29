# SIH 26121 — Existing Solutions Gap Analysis: Commercial, Domestic & Open-Source

## 1. Executive Summary
This document analyzes the operational boundaries and technical blind spots of existing solutions in drilling intelligence. By systematically categorizing commercial suites, Indian domestic systems, and open-source GitHub projects, it establishes precisely what industry solves today and illuminates the unaddressed operational white space that defines the value proposition of NWIS.

---

## 2. Sector-by-Sector Capability & Blind Spot Analysis

```
                                 THE DRILLING INTELLIGENCE SPECTRUM
┌─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┐
│     GLOBAL COMMERCIAL SUITES    │      INDIAN DOMESTIC SYSTEMS    │       OPEN-SOURCE PROJECTS      │
│     (SLB, Halliburton, BHI)     │         (ONGC WIS, Cairn)       │      (DrillMind, DrillSense)    │
├─────────────────────────────────┼─────────────────────────────────┼─────────────────────────────────┤
│ • Strengths: Deep physics twins │ • Strengths: Field-proven       │ • Strengths: Transparent code,  │
│   and enterprise integration.   │   in domestic basins.           │   zero licensing cost.          │
│ • Blind Spot: Closed cloud lock-│ • Blind Spot: Custom monolithic │ • Blind Spot: Toy scripts, no   │
│   in and astronomical cost.     │   codebases; non-exportable.    │   real-time streaming or UI.    │
└─────────────────────────────────┴─────────────────────────────────┴─────────────────────────────────┘
```

### 1. Global Commercial Suites (SLB Tela, Halliburton DWP, Baker Hughes JewelSuite)
- **What They Solve Well:**
  - Robust multi-phase hydraulics and torque-and-drag physics modeling.
  - Massive commercial datasets and enterprise data platform integrations.
- **Critical Blind Spots & Operational Gaps:**
  - **Proprietary Cloud Confinement:** Rigidly locked into proprietary cloud infrastructures (DELFI, Landmark Cloud), creating compliance friction with Indian data residency mandates.
  - **Prohibitive Cost:** High annual licensing fees and per-well monitoring surcharges that fail public CPSE L1 tender economics.
  - **Static Planning Bias:** Most offset well analytics operate during the *pre-drill planning phase* (generating static PDF reports), failing to provide dynamic, ahead-of-the-bit risk corridors during live operations.
  - **Opaque Proof:** Often summarize historical events in black-box dashboards without linking directly to original audited PDF pages and bounding boxes.

### 2. Indian Domestic Solutions (ONGC RTDOC/WIS, Cairn Nirmaan)
- **What They Solve Well:**
  - Tailored to domestic geological basins (Assam, Cambay, KG, Barmer).
  - Integrates local operational reporting practices and MoPNG regulatory forms.
- **Critical Blind Spots & Operational Gaps:**
  - **Tightly Coupled Point Solutions:** Architected as internal bespoke tools for a single operator's IT stack; cannot be readily transferred or licensed by Oil India Limited.
  - **Reporting-Centric:** ONGC’s WIS (Dec 2024) focuses primarily on Generative AI automation of Daily Drilling Reports (DDR generation), rather than active real-time offset hazard prediction ahead of the bit.

### 3. Open-Source Repositories (DrillMind, DrillSense, GitHub Projects)
- **What They Solve Well:**
  - Demonstrates raw ML feasibility on static CSV/LAS files.
  - Provides open, inspectable codebases.
- **Critical Blind Spots & Operational Gaps:**
  - **No Real-Time Streaming:** Operates exclusively in batch mode on historical CSV files; zero support for streaming WITS0/WITSML feeds or circular telemetry ring-buffers.
  - **The Measured Depth Trap:** Ignores subsurface directional surveying, comparing raw measured depths without TVDSS or stratigraphic ratio normalization.
  - **Toy User Interfaces:** Minimalistic Streamlit or CLI scripts that fail dark-mode ergonomics, spatial mapping, and rig-floor usability standards.

---

## 3. The Unaddressed White Space: Where Current Systems Fail

| Operational Reality | Commercial Suites | Indian Systems | Open-Source | What NWIS Delivers |
| :--- | :---: | :---: | :---: | :--- |
| **Air-Gapped Rig-Floor Execution** | ❌ (Cloud dependent) | ⚠️ (Requires VPN) | ⚠️ (CLI only) | **Full local Docker stack on edge IPC.** |
| **Stratigraphic Depth Alignment ($\xi$)** | ⚠️ (Requires manual tops)| ⚠️ (Manual lookup) | ❌ (Raw MD only) | **Automated dynamic depth projection.** |
| **Zero-Hallucination Document Proof**| ❌ (Summary only) | ⚠️ (Text only) | ❌ (None) | **1-click PDF bounding-box verification.** |
| **Decoupled Physics-ML Architecture** | ⚠️ (Monolithic) | ⚠️ (Single-purpose)| ❌ (Single model) | **4 independent, explainable hazard engines.** |
| **Sovereign, Perpetual IP Ownership**| ❌ (Annual SaaS) | ❌ (Proprietary ONGC)| ⚠️ (Unmaintained) | **Turnkey open-source stack owned by OIL.** |

---

## 4. Architectural Verdict for SIH 26121

**Verdict:** `[FILLING THE SOVEREIGN ADVISORY WHITE SPACE]`.
- NWIS directly captures the golden middle ground: **commercial-grade algorithmic rigor and UI ergonomics**, combined with **open-source agility, zero licensing costs, and strict on-premise data sovereignty**.
- This precise differentiation provides the core argumentative pillar for winning the SIH 26121 grand finale.
