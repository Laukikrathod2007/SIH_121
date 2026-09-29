# SIH 26121 — Baker Hughes: Deep Prior-Art & Architectural Audit

## 1. Executive Summary & Corporate Stance
- **Company Name:** Baker Hughes Company
- **Market Position:** Global oilfield service and energy technology leader; pioneer in rotary steerable systems (AutoTrak), drilling dynamics, and well engineering analytics.
- **Primary Solutions Audited:**
  1. **JewelSuite Well Engineering — Offset Well Analyzer**
  2. **Drilling Hazard Prevention (DHP)**
  3. **WellLink Real-Time & Performance Platform**

---

## 2. Deep Dive: JewelSuite Offset Well Analyzer

Baker Hughes' **JewelSuite Offset Well Analyzer** is one of the most mature commercial engineering suites explicitly targeting offset well evaluation:

```
[BAKER HUGHES JEWELSUITE OFFSET WELL ANALYZER]
Multi-Well Subsurface & Drilling Database
       │
       ▼
Automated Offset Search & Ranking Engine
       ├── Multi-Parameter Filtering (Distance, hole size, trajectory, BHA, vintage)
       ├── Automated Section & Run Comparison
       └── Machine Learning Assisted Offset Clustering
       │
       ▼
Engineering Synthesis & Risk Identification
       ├── Offset Performance Benchmarking (ROP, bit dull grade, MSE)
       ├── Hazard & Drilling Complication Mapping
       └── Reduction of Manual Offset Analysis from 5 Days to 5 Hours
```

### Forensic Capability Assessment:
- **What Problem Does It Solve?** Automates the tedious, multi-day manual engineering task of comparing historical well runs, bit records, and BHA designs across an entire field.
- **Quantified Business Impact:** Baker Hughes official documentation explicitly advertises that its automated workflows **"reduce offset-well analysis from roughly five days to five hours."**
- **Offset Selection Mechanism:** Evaluates offsets not merely by surface radius, but by matching subterranean hole sections, casing depths, directional profiles, and geological formations.
- **Destruction of Simplistic Novelty Claims:** This capability directly destroys the claim that *"selecting offset wells by criteria other than distance is a unique invention of NWIS."* Baker Hughes has commercialized this for years.

`[VERIFIED: Baker Hughes JewelSuite Portal: https://www.bakerhughes.com/oilfield-services-and-equipment-digital/well-planning/jewelsuite-well-engineering]`

---

## 3. Deep Dive: Drilling Hazard Prevention (DHP)

Baker Hughes **Drilling Hazard Prevention (DHP)** represents an extraordinarily close commercial analog to the predictive risk and proactive alerting requirements of PS 26121:

```
[BAKER HUGHES DRILLING HAZARD PREVENTION (DHP) ARCHITECTURE]
Offset Well Incident Database + Geomechanical Models + Live Rig Telemetry
       │
       ▼
Dynamic Hazard Identification & Predictive Analytics Engine
       │
       ├── 1. Interactive Hazard Map (Spatial display of past events)
       ├── 2. Predictive Hazard Scoring:
       │      ├── Stuck-Pipe Risk Prediction (Differential & Mechanical)
       │      ├── Lost Circulation / Mud Loss Prediction
       │      ├── Influx / Kick Early Warning
       │      └── Wellbore Instability & Tight Hole Detection
       │
       └── 3. Dynamic Subsurface Risk Register
              └── Tracks depth-indexed hazards ahead of the active drill bit
```

### Forensic Capability Assessment:
- **What Problem Does It Solve?** Prevents drilling crews from stumbling blind into known subsurface hazards by synthesizing historical offset incidents with live sensor trends.
- **Specific Hazard Coverage:** Directly mirrors the five failure modes named in PS 26121 (stuck pipe, lost circulation, kicks, wellbore instability).
- **Dynamic Risk Register:** Continuously maintains an active risk score indexed by depth and formation.

`[VERIFIED: Baker Hughes DHP Portal: https://www.bakerhughes.com/oilfield-services-and-equipment-digital/well-planning/drilling-hazard-prevention]`

---

## 4. Deep Dive: WellLink Real-Time & Performance
- **WellLink Platform:** The backbone data transport and visualization suite for Baker Hughes remote operations centers (BEACON).
- **Core Functionality:** Aggregates high-frequency WITS/WITSML streams, provides multi-well comparative strip charts, calculates real-time hydraulics, and delivers smart alarms to remote drilling teams.

`[VERIFIED: Baker Hughes WellLink Portal: https://www.bakerhughes.com/oilfield-services-and-equipment-digital/autonomous-well-construction/welllink-performance]`

---

## 5. Reverse-Engineering Forensic Questionnaire: Baker Hughes Stack

| Technical & Operational Question | Baker Hughes Capability Status | Detailed Engineering Reality |
| :--- | :---: | :--- |
| **Does it rank offset wells beyond surface distance?** | **YES** | Core marketed feature of JewelSuite Offset Well Analyzer. |
| **Does it predict stuck pipe, mud losses, and kicks?** | **YES** | Drilling Hazard Prevention (DHP) explicitly models these exact hazards. |
| **Does it display hazards on an interactive map?** | **YES** | DHP provides interactive GIS hazard mapping. |
| **Does it ingest unstructured historical scanned PDFs via AI?** | **PARTIAL** | Strong on structured run data and numerical logs; unstructured PDF text mining is less prominent than in SLB Tela or Cognite. |
| **Does it show clickable bounding-box citations to original PDF pages?** | **NO** | Displays hazard register entries; does not link back to physical scanned PDF pages. |
| **Is DHP deployed as an open, sovereign microservice inside OIL?** | **NO** | Proprietary commercial software requiring Baker Hughes enterprise licensing. |

---

## 6. Indian Market Penetration & OIL Deployment Audit

- **Baker Hughes Indian Presence:** Corporate offices in Mumbai, regional service bases in Barmer (Rajasthan), Kakinada (KG Basin), and Duliajan/Sivasagar (Assam). `[VERIFIED]`
- **Indian Drilling Engagements:** Provides directional drilling (AutoTrak RSS), MWD/LWD, drill bits, and completion equipment to ONGC, Cairn, and OIL. `[VERIFIED]`
- **JewelSuite DHP Deployment at OIL:**
  - *Status:* `[NOT DOCUMENTED]`.
  - While Baker Hughes provides physical drilling tools and mud logging services to OIL, there is no public record of OIL procuring or deploying the JewelSuite DHP enterprise software suite across eRTMAC.

---

## 7. Conclusions for SIH 26121

1. **Baker Hughes Proves the Physical Validity of PS 26121:** The fact that Baker Hughes built entire software suites around **Offset Well Analysis** and **Drilling Hazard Prevention** proves that the problem Oil India is presenting in PS 26121 is one of the highest-value challenges in petroleum engineering.
2. **The Unstructured Data & Document Evidence Gap:** Baker Hughes systems are heavily focused on structured engineering parameters (casing weights, bit hydraulics, geomechanical curves). They do not solve the "messy PDF black hole" where decades of qualitative daily tour sheets and handwritten DDRs reside.
3. **NWIS Unique Focus:** NWIS must combine Baker Hughes' concept of an **ahead-of-the-bit risk register** with **modern multimodal document intelligence**, creating an open, auditable platform that proves every alert with the underlying original report page.
