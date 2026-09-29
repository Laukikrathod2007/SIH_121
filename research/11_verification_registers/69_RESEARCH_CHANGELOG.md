# SIH 26121 — Research Changelog & Epistemic Evolution

## 1. Executive Summary
This changelog records major discoveries, previous assumptions that were disproven, empirical evidence uncovered, and the resulting architectural implications throughout the research investigation for SIH Problem Statement 26121.

---

## 2. Chronological Record of Discoveries

### Entry 2026-09-26.01: Refutation of "OIL has no digital systems"
- **Previous Assumption:** Oil India Limited relies primarily on paper tour sheets, has no central digital monitoring platform, and requires a greenfield software solution.
- **New Evidence:** Official OIL technology disclosures, Annual Report 2024–25, and Tender CDH6605P21 confirm that OIL operates **eRTMAC** (Enhanced Real-Time Monitoring & Analytics Center) 24/7 in Duliajan, actively monitors multi-rig operations over WITS/WITSML, licenses Landmark (Halliburton) **Well Plan** for hydraulics, and is rolling out **eRTMAC 2.0**.
- **Implication:** NWIS must NOT attempt to replace eRTMAC or re-implement basic mud hydraulics. NWIS must be positioned as a standalone, complementary decision-support system that injects institutional memory alongside eRTMAC.
- **Affected Files:** [10_OIL_CURRENT_STATE.md](file:///d:/Programming/Project%203.0/PS121/research/10_OIL_CURRENT_STATE.md), [11_OIL_eRTMAC_DEEP_AUDIT.md](file:///d:/Programming/Project%203.0/PS121/research/11_OIL_eRTMAC_DEEP_AUDIT.md), [12_OIL_DIGITALISATION_AND_AI.md](file:///d:/Programming/Project%203.0/PS121/research/12_OIL_DIGITALISATION_AND_AI.md).

---

### Entry 2026-09-26.02: Refutation of "Nobody in the world has done this"
- **Previous Assumption:** An AI-powered offset well intelligence platform is a completely unprecedented novelty with zero existing commercial prior art.
- **New Evidence:** Detailed commercial product audits revealed:
  - **SLB Tela Offset Wells Insights:** Agentic AI solution ingesting unstructured offset well reports, PDFs, and DDRs, mapping risk occurrences, and answering natural-language queries.
  - **Baker Hughes JewelSuite & DHP:** Automated offset well analysis reducing study time from 5 days to 5 hours, combined with real-time dynamic hazard prediction.
  - **Cognite Know Your Well:** Commercialized institutional memory platform demonstrated on 20 Volve wells (1.5M points) on OSDU.
  - **Halliburton OpenWells / DWP:** Offset well technical limit analysis and AI integration via InformatiQ.
- **Implication:** Claiming conceptual monopoly before SIH judges will instantly destroy team credibility. Novelty must be claimed on **Dynamic Contextual Interval Alignment**, **Ahead-of-the-Bit Risk Corridors**, and **Sovereign Standalone Integration with eRTMAC**, not on the generic concept of offset well AI.
- **Affected Files:** [30_GLOBAL_COMMERCIAL_SOLUTIONS.md](file:///d:/Programming/Project%203.0/PS121/research/30_GLOBAL_COMMERCIAL_SOLUTIONS.md) through [39_OTHER_GLOBAL_SOLUTIONS.md](file:///d:/Programming/Project%203.0/PS121/research/39_OTHER_GLOBAL_SOLUTIONS.md).

---

### Entry 2026-09-26.03: Discovery of ONGC's Advanced Digital Drilling Stack
- **Previous Assumption:** Indian upstream operators are significantly behind global IOCs in adopting AI for drilling operations.
- **New Evidence:** Comprehensive audit of ONGC revealed an extraordinarily mature domestic digital stack:
  - **RTDOC (Dehradun):** Centralized 24/7 drilling operations center.
  - **WIS (Well Information System):** Generative AI-powered daily drilling reporting launched in Dec 2024.
  - **Digital Well Program (DWP):** Cloud well planning integration.
  - **Drilling Belief Analytics (DBA):** Edge-based probabilistic stuck pipe and pressure anomaly alerts trialed in Rajahmundry and Sivasagar (Assam).
  - **DRISHTI & TATHYA.AI:** Real-time stuck pipe AI copilot and legacy well record AI extraction.
- **Implication:** ONGC provides a verified national architectural reference. We can demonstrate to the judges how NWIS equips Oil India Limited with comparable sovereign capabilities.
- **Affected Files:** [20_INDIAN_UPSTREAM_ECOSYSTEM.md](file:///d:/Programming/Project%203.0/PS121/research/20_INDIAN_UPSTREAM_ECOSYSTEM.md), [21_ONGC_DIGITAL_DRILLING_AUDIT.md](file:///d:/Programming/Project%203.0/PS121/research/21_ONGC_DIGITAL_DRILLING_AUDIT.md), [24_INDIAN_DEPLOYMENTS_AND_CASE_STUDIES.md](file:///d:/Programming/Project%203.0/PS121/research/24_INDIAN_DEPLOYMENTS_AND_CASE_STUDIES.md).

---

### Entry 2026-09-26.04: Rejection of the "One ML Model for All 5 Risks" Fallacy
- **Previous Assumption:** A single machine learning model (e.g. multi-class neural network or XGBoost) can predict mud losses, stuck pipe, kicks, torque spikes, and cementing failures simultaneously.
- **New Evidence:** Physical domain analysis established that the five hazards have mutually incompatible physical mechanisms, diagnostic sensors, and temporal lead times (e.g. mud loss = flow deficit; differential stuck pipe = static pipe across permeable sand; kick = Boyle's law gas expansion; torque = torsional resonance; cementing = casing standoff).
- **Implication:** NWIS must deploy a decoupled, multi-model predictive framework where specialized models evaluate each hazard family independently.
- **Affected Files:** [04_DRILLING_DOMAIN_FUNDAMENTALS.md](file:///d:/Programming/Project%203.0/PS121/research/04_DRILLING_DOMAIN_FUNDAMENTALS.md), [56_DRILLING_RISK_PREDICTION.md](file:///d:/Programming/Project%203.0/PS121/research/56_DRILLING_RISK_PREDICTION.md) through [61_CEMENTING_RISK_RESEARCH.md](file:///d:/Programming/Project%203.0/PS121/research/61_CEMENTING_RISK_RESEARCH.md).

---

### Entry 2026-09-26.05: Establishment of the "Historical Risk Corridor" Formulation
- **Previous Assumption:** Offset wells can be compared by simply plotting them on a map and looking at events within $\pm 50$ meters of raw Measured Depth.
- **New Evidence:** Subsurface borehole geometry proves that raw Measured Depth (MD) comparison between deviated wells is physically invalid due to trajectory inclination and geological dip. Comparing raw MD can trigger alerts thousands of meters off-target.
- **Implication:** Designed the formal mathematical transformation:
  $$\text{Offset MD} \xrightarrow{\text{Survey}} \text{TVDSS} \xrightarrow{\text{Stratigraphic Ratio }\xi} \text{Active Projected TVDSS} \xrightarrow{\text{Active Survey}^{-1}} \text{Active Target MD}$$
  This formulation creates the **Historical Risk Corridor**, the signature technical innovation of NWIS.
- **Affected Files:** [52_DEPTH_FORMATION_CORRELATION.md](file:///d:/Programming/Project%203.0/PS121/research/52_DEPTH_FORMATION_CORRELATION.md).

---

### Entry 2026-09-26.06: Completion of Tracks A–D & Synthesis of Engineering Blueprint
- **Milestone:** All planned research tracks across Machine Learning models (GBDT vs LSTM vs Transformers), Explainability & Uncertainty (TreeSHAP & Conformal Prediction), Datasets (Volve, FORCE 2020, Utah FORGE), Data Sovereignty & Security, Patent Freedom-to-Operate, 40-Feature Competitive Matrix, Oil India vs. Global Major Audits, SIH Demo Workflow, and Formal Evidentiary Registers have been authored and cross-verified against primary sources.
- **Outcome:** The research corpus is 100% complete across 71 documents. Ground truth, operational realities, and system architecture are locked. The project is fully transitioned to prototype code implementation.
- **Affected Files:** [83_ML_MODEL_RESEARCH.md](file:///d:/Programming/Project%203.0/PS121/research/83_ML_MODEL_RESEARCH.md) through [FINAL_RESEARCH_SYNTHESIS.md](file:///d:/Programming/Project%203.0/PS121/research/FINAL_RESEARCH_SYNTHESIS.md).

