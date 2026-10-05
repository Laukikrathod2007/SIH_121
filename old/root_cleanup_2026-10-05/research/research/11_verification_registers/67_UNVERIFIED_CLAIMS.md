# SIH 26121 — Register of Unverified Claims & Operator Inquiry Protocol

## 1. Executive Summary
Transparent scientific methodology requires explicitly documenting what is *not known* or what cannot be verified through public records. This document cataloges four specific operational parameters that remain confidential to Oil India Limited, defines how NWIS maintains defensive architectural fallbacks, and formulates targeted questions for OIL evaluators during the SIH grand finale.

---

## 2. Unverified Operational Claims Register

```
                               UNVERIFIED CLAIMS AUDIT
┌─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┐
│ CLAIM 1: INTERNAL DB SCHEMA     │ CLAIM 2: FIELD VSAT PROTOCOL    │ CLAIM 3: HANDWRITTEN OCR RATIO  │
│ • Oracle vs OpenWorks vs Mongo  │ • Raw WITS0 vs WITSML Gateway   │ • % handwritten pre-1990 DDRs   │
├─────────────────────────────────┼─────────────────────────────────┼─────────────────────────────────┤
│ CLAIM 4: NPT HOURLY COST TIER   │ SYSTEM MITIGATION STRATEGY      │ JURY INQUIRY PROTOCOL           │
│ • Exact rig day rate variations │ • Multi-adapter ingestion layer │ • Direct question during Q&A    │
└─────────────────────────────────┴─────────────────────────────────┴─────────────────────────────────┘
```

---

## 3. Granular Analysis & Engineering Fallbacks

### Claim 1: OIL's Internal eRTMAC Archival Schema
- **Unverified Aspect:** Public disclosures confirm OIL operates eRTMAC and licenses Landmark Well Plan, but do not specify whether historical DDRs and well trajectories are archived in an Oracle relational schema, Landmark OpenWorks, or unindexed shared network folders.
- **Architectural Fallback:** NWIS implements a **Universal Relational Data Adapter**. It can ingest standard WITSML XML files, OSDU JSON schemas, or direct CSV/Excel exports from legacy Oracle tables without code refactoring.

### Claim 2: Rig-to-eRTMAC Field Transmission Protocol
- **Unverified Aspect:** Whether remote rigs in Arunachal Pradesh and Upper Assam transmit telemetry using legacy WITS0 Level 0 serial streams over VSAT modems, or modernized WITSML v1.4.1.1 XML/SOAP over IP.
- **Architectural Fallback:** NWIS includes a dual-protocol ingestion gateway: a lightweight Python/Go daemon that parses both raw **WITS0 Record 01–25 serial strings** and structured **WITSML 1.4 XML packets**.

### Claim 3: Proportion of Scanned Handwritten Historical Logs
- **Unverified Aspect:** While post-2010 DDRs are primarily standardized digital PDFs, the proportion of pre-2000 legacy records in Nahorkatiya and Moran fields that are handwritten cursive or degraded mimeograph copies is unknown.
- **Architectural Fallback:** NWIS deploys **Tesseract OCR with OpenCV adaptive binarization** for typed text, augmented with a secondary Vision-Language Model fallback (e.g. Qwen2-VL or local OCR checkpoint) for handwritten text. Low-confidence extractions are explicitly flagged with epistemic uncertainty tags.

### Claim 4: Internal NPT Cost Allocation per Rig Class
- **Unverified Aspect:** The exact internal day rate and financial penalty allocated by OIL accounting for stuck pipe downtime across 1,000 HP, 1,500 HP, and 2,000 HP drilling rigs in Assam.
- **Architectural Fallback:** NWIS provides a configurable ROI parameter panel in the dashboard, allowing the superintendent to input their specific rig day rate (e.g., ₹8,00,000 to ₹15,00,000/day) to calculate live financial savings dynamically.

---

## 4. Targeted Inquiry Questions for Oil India Evaluators

During the SIH Q&A defense, the team can demonstrate domain professionalism by proactively asking:
1. *"In your current eRTMAC 2.0 deployment, are offset well completion reports indexed inside an OpenWorks relational database, or stored as unstructured PDF dossiers?"*
2. *"What percentage of your legacy well archives from Moran and Nahorkatiya are digitized as searchable PDFs versus raw raster scans?"*

---

## 5. Architectural Verdict for SIH 26121

**Verdict:** `[DEFENSIVE MODULARITY]`.
- By recognizing these unverified operational boundaries and building flexible abstraction layers, NWIS guarantees seamless field deployment regardless of OIL's specific internal legacy database quirks.
