# SIH 26121 — Research Methodology & Epistemic Standards

## 1. Executive Summary & Epistemic Stance
This document establishes the rigorous methodology, verification hierarchy, claim classification schema, and evidential standards applied across all research for Smart India Hackathon (SIH) Problem Statement 26121:
**"eRTMAC-NWIS (Nearby Wells Intelligence System): An AI-Powered Offset Well Knowledge and Decision Support Platform for Drilling Operations"** sponsored by **Oil India Limited (OIL)**.

In mission-critical drilling engineering, unverified claims, hallucinated AI metrics, and marketing literature conflated with operational facts introduce severe operational and intellectual risk. The foundational rule of this research corpus is:
> **Treat all prior internal notes, pitch decks, competitor marketing pages, and unverified assumptions as unverified hypotheses until independently cross-referenced against primary engineering, regulatory, or empirical sources.**

---

## 2. Epistemic Hierarchy of Sources

To prevent "AI echo chambers" and marketing inflation, every factual assertion in this repository adheres to a strict 4-level evidentiary hierarchy:

```
[LEVEL 1: PRIMARY SOURCES]
├── Official Operator Documentation (OIL Annual Reports, Tenders, Policy Briefs)
├── Regulatory & Government Filings (DGH, MoPNG, OISD Standards, Hydrocarbon Outlook)
├── Official Vendor Engineering Specifications & User Documentation (SLB, Baker Hughes, Halliburton)
├── International Data Standards Bodies (Energistics WITSML, OSDU Forum, PPDM)
└── Peer-Reviewed Primary Technical Papers (SPE OnePetro, Elsevier, Springer Nature, IEEE)

[LEVEL 2: HIGH-QUALITY SECONDARY SOURCES]
├── Industry Technical Journals (Journal of Petroleum Technology - JPT, World Oil, Oil & Gas Journal)
├── Verified Industry Conference Proceedings (ADIPEC, IPTC, SPWLA)
└── Audited Corporate Financial Disclosures (BSE/NSE Filings, Investor Presentations)

[LEVEL 3: SECONDARY & TERTIARY REPORTING]
├── Trade Press & Energy Technology Journalism (Upstream Online, Energy Voice)
├── Executive Interviews & Keynotes
└── Case Studies Published by Software Vendors (treated as VENDOR-CLAIMED until verified)

[LEVEL 4: DISCOVERY ONLY (DISALLOWED AS SOLE EVIDENCE)]
├── Unverified Marketing Overviews, SEO Landing Pages
├── Generic AI Generated Content / Summaries
└── Social Media / Blog Posts (LinkedIn, Reddit)
```

---

## 3. Standardized Claim Classification System

Every technical, operational, and competitive claim documented throughout the `research/` corpus is tagged with one of nine mutually exclusive classification badges:

| Classification Badge | Exact Definition | Evidentiary Standard Required |
| :--- | :--- | :--- |
| `[VERIFIED]` | Absolute empirical fact confirmed by official primary documentation or operating records. | Primary source citation (e.g. OIL tender, OISD standard, peer-reviewed experiment). |
| `[PRIMARY-SOURCE]` | Direct statement published by the entity itself (e.g. Oil India Limited official statement). | Direct official publication, annual report, or government gazette. |
| `[VENDOR-CLAIMED]` | Capability advertised by a commercial vendor without external peer-reviewed validation. | Official product brochure, vendor portal, or vendor press release. |
| `[RESEARCH-SUPPORTED]`| Concept or algorithmic benchmark demonstrated in peer-reviewed scientific literature. | Formal citation (DOI/OnePetro/arXiv) with explicit experimental setup and dataset context. |
| `[SECONDARY-SOURCE]` | Information reported by an independent third-party news or industry publication. | Reputable industry trade publication with attributed authors. |
| `[INFERENCE]` | Technical deduction derived logically from known engineering facts, but not explicitly stated. | Must state the premises, deduction path, and domain constraints explicitly. |
| `[ILLUSTRATIVE]` | Representative numbers, mock values, or hypothetical scenarios used solely for design demonstration. | Explicitly labelled so no developer confuses mock values with actual operational parameters. |
| `[UNVERIFIED]` | Plausible technical claim currently lacking independent primary or secondary confirmation. | Flagged with investigative action plan and questions requiring operator clarification. |
| `[CONTRADICTED]` | Claim found in prior working notes that has been disproven by factual primary evidence. | Documented with counter-evidence to prevent recurrence. |

---

## 4. Rigorous Domain Separation Principles

To prevent confusion among technical developers, system architects, and drilling engineers, five foundational distinctions are strictly enforced:

1. **Nearby Well vs. Relevant Offset Well:**
   - *Nearby Well:* Defined strictly by Euclidean surface or reservoir distance (e.g., within 5 km radius).
   - *Relevant Offset Well:* Defined by geological, structural, formation, lithological, pressure, and operational similarity regardless of spatial proximity. A well 2 km away across a sealing fault may be irrelevant, while a well 15 km away along strike in the same depositional sequence is critical.
2. **Historical Data vs. Historical Knowledge:**
   - *Historical Data:* Raw sensor logs, unstructured Daily Drilling Reports (DDRs), Well Completion Reports (WCRs), and ASCII/LAS files.
   - *Historical Knowledge:* Contextualized, indexed, causally connected facts (e.g. "At 3,250 m MD in the Barail Sand, high ECD caused mud losses of 18 m³/h, cured using 30 kg/m³ medium-grade walnut hull LCM").
3. **Data Retrieval vs. Decision Support:**
   - *Data Retrieval:* Keyword search, SQL query, or vector similarity returning raw PDF snippets.
   - *Decision Support:* Synthesizing historical offset events against active drilling state, evaluating lead-time, quantifying uncertainty, and presenting defensible mitigations with source audit trails.
4. **Anomaly Detection vs. Predictive Risk Modeling:**
   - *Anomaly Detection:* Unsupervised flagging of mathematical deviations in live surface sensor streams (e.g. unexpected SPP drop).
   - *Predictive Risk Modeling:* Forward-looking, depth/formation-projected likelihood of specific failure modes (e.g. differential sticking probability over next 50 m) grounded in offset historical precedent and geomechanics.
5. **Decision Support vs. Autonomous Rig Control:**
   - *Decision Support:* Providing human drilling engineers and supervisors with prioritized, contextual intelligence.
   - *Autonomous Control:* Direct digital closed-loop control of rig drawworks, top drive, or mud pumps. **NWIS is explicitly decision support, NOT autonomous control.**

---

## 5. Audit Workflow for Existing Materials

The prior working document (`TEMP/temp_Research_many_things_wrong.pdf`) and associated discussions (`TEMP/convo1.txt`, `TEMP/convo2.txt`, `TEMP/convo3.txt`) are audited using the following 5-step protocol:

```
Prior Document Claim Extraction
       ↓
Primary Source Identification & Verification (Web, SPE, OIL Tenders)
       ↓
Cross-Referencing Against Indian Upstream Operating Reality (ONGC, OIL, Cairn)
       ↓
Epistemic Tagging ([VERIFIED], [VENDOR-CLAIMED], [CONTRADICTED], etc.)
       ↓
Entry into 120_CLAIM_VERIFICATION_MATRIX.md with Action (KEEP, REWORD, REMOVE)
```

---

## 6. Structure of the Research Corpus

The research output is organized into a modular, decoupled hierarchy across 50+ specialized markdown documents in `research/`, indexed in `00_RESEARCH_MASTER_INDEX.md`:

- **00–05:** Foundations, Methodology, PS Forensics, Physical Domain Fundamentals, Real Workflow.
- **10–14:** Oil India Limited Current State, eRTMAC Capabilities, DRIVE 2.0, Data Assets.
- **20–25:** Indian Upstream Ecosystem (ONGC RTDOC/WIS/DBA/DRISHTI/TATHYA.AI, Cairn, Indian Startups).
- **30–39:** Global Commercial Prior Art (SLB Tela/DrillPlan, Baker Hughes JewelSuite/DHP, Cognite, Halliburton, NOV, Weatherford, Peloton, Corva).
- **40–42:** Open Source Drilling AI (DrillMind, DrillSense, Utah FORGE) & SIH Competitors.
- **50–61:** Deep Technical Tracks (Offset Selection, Correlation, Document NLP/OCR, 5 Risk Families).
- **70–84:** Standards (WITSML, OSDU), Geospatial, Digital Twin, Knowledge Graphs, ML Models.
- **90–104:** Datasets, Data Governance, Patents, Competitive Feature Matrix, True Gap Analysis.
- **110–113:** SIH Product Boundaries, MVP Scope, Demonstration Narrative.
- **120–125:** Claim Matrix, Evidence Register, Bibliography, Unverified Claims, Open Questions, Changelog.
