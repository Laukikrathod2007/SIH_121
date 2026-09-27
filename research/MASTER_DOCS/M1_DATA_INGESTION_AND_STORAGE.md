# eRTMAC-NWIS: Module 1 — Historical Drilling Data Extraction and Storage
# Master Document 1 of 6

> An AI reading this file can build Module 1 completely.
> This covers: What data exists, how to ingest it, OCR pipeline, database schema concepts,
> WITSML standards, and the synthetic data generator for demo purposes.

---

## 1. What Module 1 Produces

Input:  500 scanned PDF files (DDRs, WCRs) dumped into a watched folder.
Output: Structured database records containing:
  - Formation top depths per well (in TVDSS meters)
  - Mud properties per DDR page (density g/cc, viscosity cP, water loss mL/30min)
  - NPT event records (type, start depth, end depth, duration hours, mitigation applied)
  - Well header records (well name, field, coordinates, total depth, spud date)
  - Raw text passages indexed for RAG retrieval (Module 3)
  - Bounding box coordinates for every extracted fact (for 1-click PDF proof in Module 6)

---

## 2. What OIL Documents Look Like (Realistic Description)

### 2.1 Daily Drilling Report (DDR) Structure
A typical OIL DDR is a 2-4 page printed form, often scanned at 200-300 DPI grayscale.
It contains FOUR sections:

SECTION 1 — HEADER (top of page)
  Well Name: NHK-412 | Field: Nahorkatiya | Rig: ONGC-DR-IV | Date: 14/03/2018
  Bit Depth Start: 3,218 m | Bit Depth End: 3,231 m | Footage: 13 m
  On Bottom Hours: 18.5 | Circulating Hours: 4.5 | NPT Hours: 1.0

SECTION 2 — OPERATIONS TABLE (tabular, 24-hour breakdown)
  Time (hhmm) | Operation | Depth From | Depth To | Duration
  0000        | Rotary drilling | 3218 | 3224 | 6.0 hrs
  0600        | Connection      | 3224 | 3224 | 0.5 hrs
  0630        | Rotary drilling | 3224 | 3228 | 4.0 hrs
  1030        | Mud loss event  | 3228 | 3228 | 1.0 hrs <<< NPT
  1130        | LCM pill pump   | 3228 | 3228 | 1.5 hrs
  ...

SECTION 3 — MUD REPORT
  Mud Type: PHPA/KCl  | Density: 1.38 g/cc | Viscosity: 45 cP | PV: 18 cP | YP: 27 lbs/100ft2
  Water Loss: 4.2 mL  | Chlorides: 28,000 ppm | pH: 10.2

SECTION 4 — REMARKS (free-text narrative, most valuable for RAG)
  "Total mud losses at 3,228 m while drilling Tipam Sandstone. Initial losses 35 bbl/hr.
   Mixed 30 bbl medium nut plug LCM pill with 40 ppb calcium carbonate + 40 ppb medium
   nut plug. Pumped at reduced rate 1,200 lpm. Losses reduced to 5 bbl/hr after 2 hrs.
   Recommend reducing mud weight from 1.38 to 1.32 g/cc before next Tipam interval."

### 2.2 Well Completion Report (WCR) Structure
A WCR is a 20-80 page document summarizing an entire well. Key extractable sections:
  - Final Well Summary (total depth, formation reached, completion type)
  - Formation Tops Table (formation name, depth MD, depth TVDSS)
  - Casing Program (surface, intermediate, production casing sizes and setting depths)
  - Cement Job Record (volumes, densities, TOC for each casing string)
  - Production Test Results (flow rates, shut-in pressures per zone)
  - Lessons Learned section (free text — gold for RAG)

---

## 3. The OCR and NLP Ingestion Pipeline

### 3.1 Pipeline Architecture

[PDF File] -> [PyMuPDF page renderer] -> [Layout Classifier] -> [OCR Engine] -> [NLP Extractor] -> [DB Writer]

Step 1 — Page Rendering (PyMuPDF):
  doc = pymupdf.open("NHK412_DDR_2018.pdf")
  for page in doc:
      pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))  # 2x zoom for OCR quality
      image = pix.tobytes("png")

Step 2 — Layout Classification:
  Classify each page into: HEADER_TABLE | OPERATIONS_TABLE | MUD_REPORT | REMARKS | WCR_FORMATION_TOPS
  Use heuristic rules: if page contains "Bit Depth" and "Footage" -> DDR_HEADER
  Use positional bounding box analysis for table detection.

Step 3 — OCR (Tesseract for scanned pages, PyMuPDF text for digital PDFs):
  For scanned pages: pytesseract.image_to_data(image, output_type=Output.DICT)
  For digital PDFs: page.get_text("dict") with bounding boxes per word

Step 4 — NLP Information Extraction:
  HEADER: Regex patterns for well name, date, depth values
    Well Name pattern: r'[A-Z]{2,4}-\d{3,4}[A-Z]?' -> matches NHK-412, MOR-089
    Depth pattern: r'(\d{1,4}[,.]?\d{3})\s*m' -> matches 3,228 m or 3228 m
    Date pattern: r'\d{2}/\d{2}/\d{4}' -> matches 14/03/2018

  MUD REPORT: Extract key-value pairs
    density_pattern: r'[Dd]ensity[:\s]+(\d+\.\d+)\s*(?:g/cc|SG|ppg)'
    viscosity_pattern: r'[Vv]iscosity[:\s]+(\d+)\s*(?:cP|secs?)'

  NPT EXTRACTION: Keyword detection in operations table
    NPT_KEYWORDS = ['loss', 'stuck', 'kick', 'influx', 'washout', 'twist off',
                    'fishing', 'reaming', 'tight hole', 'pack off', 'cement failure']

  BOUNDING BOX STORAGE: Every extracted fact stores its source location:
    {"fact": "losses 35 bbl/hr", "page": 2, "x0": 124, "y0": 340, "x1": 520, "y1": 360}
    This is used by Module 6 to highlight the exact text in the PDF viewer.

### 3.2 OCR Confidence Scoring

Following DDR_UTAH_FORGE best practices, numerical fields MUST have confidence checks:
  HIGH_CONFIDENCE = Tesseract word confidence > 85% AND value in physically plausible range
  LOW_CONFIDENCE = Word confidence < 85% OR value outside plausible range
    (e.g., mud density 1.85 g/cc for Tipam interval is physically implausible -> flag)

Plausibility ranges for Upper Assam (from USGS + field knowledge):
  mud_density: 1.00 – 1.60 g/cc (normal; >1.60 rare except for overpressure zones)
  rop_drilling: 1 – 40 m/hr (normal for rotary drilling in sandstone)
  bit_depth: 50 – 6000 m (conductor to deepest well in Upper Assam)
  npt_duration: 0.25 – 72 hours (15 min to 3 days typical for major events)

Low-confidence extractions go to a review queue — NOT auto-committed to the database.

### 3.3 Formation Tops Extraction (Critical for Module 4)

Formation tops are in WCRs, usually as a table:
  Formation          | Top Depth (m MD) | Top Depth (m TVDSS) | Notes
  Alluvium           | 0                | -85 (MSL elev 85m)  | Surface
  Girujan Formation  | 312              | 227                 |
  Tipam Sandstone    | 1,186            | 1,095               | First sand
  Barail Lower Sand  | 3,208            | 2,940               | Main Pay Sand
  Barail Coal-Shale  | 3,890            | 3,580               | Coal seams start
  Kopili Formation   | 4,820            | 4,420               | TD zone

Extraction note: If TVDSS column is absent, calculate it from directional survey data.
If directional survey is absent, flag the well as "MD-only" and apply statistical dip correction
(see Module 4 for the correction algorithm).

---

## 4. WITSML Live Telemetry Ingestion

### 4.1 What WITSML Is

WITSML (Wellsite Information Transfer Standard Markup Language) is the industry standard XML
format for transmitting real-time drilling sensor data. Defined by Energistics consortium.
OIL eRTMAC 2.0 (2026 tender) specifies WITSML 1.4.1 compatibility.

Key WITSML object types relevant to NWIS:
  witsml:log     -> Time-indexed or depth-indexed sensor channel records (the 1-Hz data)
  witsml:wellbore-> Well metadata (name, UWI, trajectory, casing)
  witsml:mudLog  -> Mud property records and gas readings

### 4.2 WITSML Channel Mnemonics We Ingest

Mnemonic | Full Name                  | Unit    | Our Use
---------|----------------------------|---------|----------------------------------
DBTM     | Bit Depth Total (MD)       | m       | Active depth tracking
ROPAV    | Rate of Penetration (avg)  | m/hr    | Drilling break detection
WOB      | Weight on Bit              | kN/daN  | Stuck pipe indicator
RPM      | Rotary Speed               | rpm     | Rig state classification
TQA      | Torque Average             | kNm     | Stick-slip detection
SPPA     | Standpipe Pressure         | kPa     | Lost circulation (pressure drop)
MFIA     | Flow In Average            | L/min   | Mud pump rate
MFOA     | Flow Out Average           | L/min   | Kick/loss detection (delta Q)
TVOLUME  | Total Pit Volume           | m3      | Pit gain/loss detection
HKLA     | Hookload Average           | kN      | Overpull detection

### 4.3 The 1-Hz WebSocket Simulator (for demo)

Since we cannot access live OIL eRTMAC streams, the demo uses the Volve dataset
replayed in real time via a Python WebSocket server:

  class TelemetrySimulator:
      def __init__(self, csv_path):
          self.df = pd.read_csv(csv_path, parse_dates=['datetime'])
          self.current_idx = 0

      async def stream(self, websocket):
          while self.current_idx < len(self.df):
              row = self.df.iloc[self.current_idx]
              payload = {
                  "timestamp": row['datetime'].isoformat(),
                  "DBTM": row['DBTM'],        # Bit depth
                  "ROPAV": row['ROPAV'],      # ROP
                  "WOB": row['WOB'],
                  "RPM": row['RPM'],
                  "TQA": row['TQA'],
                  "SPPA": row['SPPA'],
                  "MFIA": row['MFIA'],
                  "MFOA": row['MFOA'],
                  "TVOLUME": row['TVOLUME']
              }
              await websocket.send(json.dumps(payload))
              self.current_idx += 1
              await asyncio.sleep(1.0)   # 1-Hz rate

The simulator MUST replay at realistic ROP values (8-15 m/hr for Upper Assam sandstone)
so the demo depth progression matches real field timing.

---

## 5. Database Schema Concepts

### 5.1 Core Tables (PostgreSQL + PostGIS)

WELLS table — one row per well:
  well_id (PK), well_name, field_name, spud_date, total_depth_m, td_formation,
  surface_easting (m, Everest 1956 projection), surface_northing,
  wellhead_lat (WGS84), wellhead_lon (WGS84),
  is_active (boolean), completion_type

  PostGIS geometry: geom = ST_GeomFromText('POINT(lon lat)', 4326)

FORMATION_TOPS table — one row per formation per well:
  top_id (PK), well_id (FK), formation_name, depth_md_m, depth_tvdss_m,
  confidence_level (HIGH/LOW/INFERRED), source_document_id

NPT_EVENTS table — one row per NPT incident:
  event_id (PK), well_id (FK), event_type (LOST_CIRCULATION/STUCK_PIPE/KICK/TORQUE/CEMENT),
  start_depth_md, end_depth_md, start_depth_tvdss, end_depth_tvdss,
  duration_hours, severity (1-5), mitigation_applied (text),
  document_id (FK), page_number, bbox_x0, bbox_y0, bbox_x1, bbox_y1

TELEMETRY_REALTIME table — rolling 2-hour window (partitioned by time):
  ts (timestamptz), well_id (FK), DBTM, ROPAV, WOB, RPM, TQA, SPPA, MFIA, MFOA, TVOLUME

DOCUMENTS table — one row per ingested PDF:
  doc_id (PK), well_id (FK), doc_type (DDR/WCR/DST/CBL), report_date,
  original_filename, storage_path, ocr_status, confidence_avg

DOCUMENT_CHUNKS table — for RAG retrieval:
  chunk_id (PK), doc_id (FK), page_number, chunk_text, embedding VECTOR(768),
  bbox_x0, bbox_y0, bbox_x1, bbox_y1  -- bounding box of this text chunk on its page

### 5.2 Vector Search Extension
  CREATE EXTENSION IF NOT EXISTS vector;
  CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops);

---

## 6. Synthetic Data Generator

### 6.1 What We Generate and Why

For the demo, we need ~15 synthetic offset wells in the Nahorkatiya/Moran area, each with:
  - Realistic formation top depths (calibrated to USGS Bulletin 2208-D ranges)
  - 3-10 NPT events at geological hazard zones
  - 200-500 DDR-style text records
  - Directional survey data for TVDSS calculation

### 6.2 Generation Algorithm

import numpy as np

USGS_FORMATION_TOPS = {
    "Gurjan": {"mean_tvdss": 300, "std": 80, "min": 50, "max": 600},
    "Girujan": {"mean_tvdss": 900, "std": 150, "min": 600, "max": 1200},
    "Tipam": {"mean_tvdss": 1800, "std": 400, "min": 1200, "max": 2800},
    "Surma": {"mean_tvdss": 3100, "std": 300, "min": 2800, "max": 3500},
    "Barail_Lower": {"mean_tvdss": 3500, "std": 400, "min": 3000, "max": 4200},
    "Barail_Coal": {"mean_tvdss": 4200, "std": 400, "min": 3500, "max": 5000},
    "Kopili": {"mean_tvdss": 5200, "std": 500, "min": 4500, "max": 6000},
}

NPT_HAZARD_ZONES = {
    "Tipam": {
        "event_types": ["LOST_CIRCULATION"],
        "prob": 0.65,  # 65% of wells hit Tipam losses historically
        "severity_dist": [0.3, 0.4, 0.2, 0.1, 0.0],  # 1-5 severity
        "mitigation_templates": [
            "Mixed {vol} bbl medium nut plug LCM pill. Reduced pump rate from "
            "{rate_before} to {rate_after} lpm. Losses cured in {hours} hrs.",
        ]
    },
    "Barail_Coal": {
        "event_types": ["STUCK_PIPE", "GAS_KICK"],
        "prob": 0.45,
        "severity_dist": [0.1, 0.3, 0.35, 0.2, 0.05],
        "mitigation_templates": [
            "Spotted {vol} bbl {fluid} pill at {depth} m. Applied {overpull} kN "
            "overpull. String freed after {hours} hrs.",
        ]
    }
}

def generate_well(well_name, field, lat, lon, total_depth_tvdss):
    formation_tops = {}
    for form, params in USGS_FORMATION_TOPS.items():
        if params["mean_tvdss"] < total_depth_tvdss:
            top = np.clip(np.random.normal(params["mean_tvdss"], params["std"]),
                          params["min"], params["max"])
            formation_tops[form] = round(top)
    # Generate NPT events in relevant zones
    npt_events = []
    for form, hazard in NPT_HAZARD_ZONES.items():
        if form in formation_tops and np.random.random() < hazard["prob"]:
            depth = formation_tops[form] + np.random.uniform(10, 200)
            npt_events.append(generate_npt_event(depth, hazard))
    return {"well_name": well_name, "formation_tops": formation_tops, "npt_events": npt_events}

### 6.3 Well Coordinates from Parivesh EIA

From OIL EIA filings on parivesh.nic.in, actual NHK/MOR area well coordinates can be extracted.
Use these as the spatial anchor points for the synthetic wells.
Realistic approximate well locations (Upper Assam shelf):
  Nahorkatiya area: ~27.2°N, 95.3°E
  Moran area: ~26.9°N, 94.9°E
  Digboi area: ~27.4°N, 95.6°E
  Lakwa area: ~26.9°N, 94.7°E
  Baghjan area: ~27.5°N, 95.4°E

---

## 7. Background Ingestion Worker

### 7.1 File Watcher

Use Python watchdog to monitor the OIL data clerk drop folder:

  from watchdog.observers import Observer
  from watchdog.events import FileSystemEventHandler

  class DDRHandler(FileSystemEventHandler):
      def on_created(self, event):
          if event.src_path.endswith('.pdf'):
              queue.put(event.src_path)
              logger.info(f"New DDR queued: {event.src_path}")

### 7.2 Processing Queue

  async def process_queue():
      while True:
          pdf_path = await queue.get()
          try:
              result = await run_ocr_pipeline(pdf_path)
              await write_to_database(result)
              await update_vector_store(result["chunks"])
              logger.info(f"Processed: {pdf_path} -> {result['npt_count']} NPT events found")
          except OCRConfidenceError as e:
              await move_to_review_queue(pdf_path, e.confidence_scores)

---

## 8. Validation: How to Know Module 1 Is Working Correctly

Test 1 — OCR Accuracy Check:
  Take 5 DDRs where you manually know the mud weight.
  Run OCR. Compare extracted density vs known value.
  Acceptance criteria: < 5% error rate on numerical fields with HIGH confidence flag.

Test 2 — Formation Top Plausibility:
  Extract formation tops from 10 synthetic WCRs.
  Check all tops fall within USGS Bulletin 2208-D ranges.
  Acceptance criteria: 100% of HIGH confidence extractions within range.

Test 3 — Bounding Box Accuracy:
  For 5 manually verified NPT text passages, confirm the stored bbox coordinates
  highlight the correct text when rendered on the PDF page.
  Acceptance criteria: Highlighted region contains the relevant sentence.

Test 4 — Pipeline Throughput:
  Process 100 DDR PDFs (10 pages each).
  Acceptance criteria: < 30 seconds per PDF on a mid-range laptop CPU (no GPU needed).
