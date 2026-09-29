# SIH 26121 — DDR & WCR Document Intelligence: Multi-Modal Ingestion Pipeline

## 1. Executive Summary
This document designs the multi-modal document intelligence pipeline required to transform decades of unstructured, semi-structured, and scanned physical well records (DDRs, WCRs, Mud Logs) into a queryable, verified institutional knowledge graph. It details the OCR algorithms, tabular parsing architectures, entity extraction schemas, and bounding-box audit tracking mechanics.

---

## 2. Document Archetypes & Parsing Challenges

Drilling archives contain a heterogeneous mixture of digital and physical formats:

```
[DRILLING DOCUMENT ARCHETYPES]
├── Type A: Native Digital PDFs (Modern DDRs / Electronic Morning Reports)
│   └── Vector text embedded; high layout consistency; tables extractable via PyMuPDF/Camelot.
├── Type B: Scanned Clean Reports (Typed reports from 1990s–2010s)
│   └── Bitmap images of typed text; requires OCR (Tesseract/PaddleOCR); minor skew and noise.
├── Type C: Scanned Carbon Copies & Legacy Archives (1960s–1980s)
│   └── Faded carbon paper, uneven ink, bleed-through, hand annotations, significant skew.
└── Type D: Mud Logging Strip Charts & Composite Well Logs
    └── Extremely wide/tall raster rolls combining depth curves, lithology litho-bars, and text remarks.
```

---

## 3. The 6-Stage Multi-Modal Ingestion Pipeline

To process these archives reliably without hallucination, NWIS implements a strict 6-stage extraction pipeline:

```
[RAW DOCUMENT: PDF / TIFF / IMAGE]
       │
       ▼
[STAGE 1: DOCUMENT CLASSIFICATION & QUALITY PRE-PROCESSING]
├── Detect: Digital Vector PDF vs. Scanned Raster Image
├── Image Enhancement: Auto-deskew (Hough Transform), contrast stretching, binarization (Otsu)
       │
       ▼
[STAGE 2: LAYOUT ANALYSIS & ZONE SEGMENTATION]
├── Segment document into functional zones:
│   ├── Zone 1: Wellhead Metadata (Well Name, Field, Contractor, Spud Date)
│   ├── Zone 2: Tubular & Casing Tallies (Outer Diameter, Weight, Grade, Setting Depth)
│   ├── Zone 3: Mud Properties Table (Mud Weight, Viscosity, PV, YP, pH, Chlorides)
│   ├── Zone 4: Bit & BHA Record (Bit #, Make, Size, Jet Sizes, Footage, Dull Grade)
│   └── Zone 5: 24-Hour Chronological Operations Narrative (Time, Depth, Activity Text)
       │
       ▼
[STAGE 3: HYBRID OCR & TABLE EXTRACTION]
├── Machine-printed text: PyMuPDF for digital text; PaddleOCR / Tesseract for raster text.
├── Tabular data: Lattice & Stream algorithms (Camelot/Tabula) to preserve cell grid alignment.
       │
       ▼
[STAGE 4: DOMAIN ENTITY & EVENT EXTRACTION (NLP / LLM)]
├── Regex / Deterministic Parsers: Extract standard numerical fields (e.g. `MW: 1.28 SG`, `TD: 3450m`).
├── Domain LLM Pipeline: Extracts unstructured events, root causes, NPT hours, and mitigations.
       │
       ▼
[STAGE 5: SCHEMA VALIDATION & CONSISTENCY CHECKING]
├── Physical Consistency Rule: $TVD \le MD$ (Flag if violated).
├── Mud Weight Sanity Rule: $0.95 \le \text{MW (SG)} \le 2.40$ (Prevent decimal misreads).
├── Formation Sequence Rule: Formations must appear in correct chronological stratigraphic order.
       │
       ▼
[STAGE 6: STRUCTURED STORAGE & BOUNDING-BOX AUDIT INDEXING]
├── Relational Facts → PostgreSQL Tables (indexed by Well, Formation, Depth).
├── Dense Text Embeddings → pgvector / Qdrant.
└── Bounding Box Coordinates $[x_1, y_1, x_2, y_2, page\_num]$ stored for every extracted fact!
```

---

## 4. Structured Entity Extraction Schema

Every daily drilling report (DDR) is extracted into a strictly typed JSON schema conforming to international WITSML / OSDU conventions:

```json
{
  "well_id": "OIL-NH-09",
  "report_number": 42,
  "report_date": "2021-04-14",
  "hole_section_od_in": 12.25,
  "current_depth_md_m": 3224.0,
  "daily_footage_m": 48.0,
  "formation_name": "Barail Coal-Shale",
  "mud_properties": {
    "mud_type": "KCL-Polymer",
    "mud_weight_sg": 1.32,
    "funnel_viscosity_s": 54,
    "plastic_viscosity_cp": 22,
    "yield_point_lb_100sqft": 18
  },
  "bit_record": {
    "bit_number": 3,
    "bit_size_in": 12.25,
    "manufacturer": "Smith Bits",
    "iadc_code": "M423",
    "wob_tonnes": 14.0,
    "rpm": 110
  },
  "operational_events": [
    {
      "event_category": "LOST_CIRCULATION",
      "severity": "CRITICAL",
      "event_depth_md_m": 3224.0,
      "loss_rate_m3_per_hr": 28.0,
      "npt_hours": 14.5,
      "narrative": "At 3224m MD encountered depleted fractured Barail sand. Instant loss of returns at 28 m3/hr. Pulled bit off bottom.",
      "mitigation_applied": "Mixed and spotted 15 m3 high-permeability LCM pill containing 35 kg/m3 coarse calcium carbonate and nutshells. Allowed 4 hours soaking.",
      "outcome": "Circulation restored; continued drilling with reduced pump rate 1400 lpm.",
      "source_evidence": {
        "document_name": "NH09_DDR_TourSheet_42.pdf",
        "page_number": 2,
        "bounding_box": [145.2, 420.5, 520.8, 485.1]
      }
    }
  ]
}
```

---

## 5. The "Zero-Hallucination" Bounding Box Proof Mechanism

In life-or-death engineering operations, drilling supervisors will not trust an AI summary that merely states: *"A loss occurred at 3,224 m"*. They demand to see the original signature and log.

NWIS solves this by storing the exact physical bounding box coordinates:
- When an engineer clicks any alert, mitigation, or historical event in the NWIS dashboard, the UI opens an embedded high-resolution PDF viewer.
- The document immediately jumps to the exact page (e.g. Page 2 of DDR #42).
- The viewer renders a **bright yellow bounding box over the original scanned text**, visually proving the exact source of the extracted knowledge.

This single capability transforms NWIS from a questionable AI prototype into an auditable, enterprise-grade decision-support platform.
