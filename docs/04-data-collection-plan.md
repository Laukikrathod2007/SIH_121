# Data Collection & Preparation Plan
## eRTMAC-NWIS OCR/NLP Pipeline (Module 2)

**Document Version:** 1.0  
**Last Updated:** September 27, 2026  
**Purpose:** Comprehensive strategy for acquiring, preparing, and validating data sources for the document ingestion pipeline

---

## 1. Executive Summary

Since Oil India Limited's actual drilling data is proprietary and unavailable publicly, we will use **publicly available analogous datasets** from proven oil & gas operations to build and validate our OCR/NLP extraction pipeline. This approach:

- ✅ Demonstrates technical capability with real-world document complexity
- ✅ Allows accurate validation of extraction accuracy (targeting >94%)
- ✅ Provides credible demonstration for hackathon evaluation
- ✅ Can be directly replaced with OIL data post-deployment without architecture changes

---

## 2. OIL India Data Requirements (Target Schema)

### 2.1 Nine Data Source Categories from Problem Statement

| Source Type | Critical Fields to Extract | Usage in System |
|------------|---------------------------|-----------------|
| **Well Completion Reports (WCR)** | Well name, location, total depth, formation tops, casing program, mud program, cement records | M4: Offset Relevance, M5: Depth Correlation |
| **Daily Drilling Reports (DDR)** | Date, depth, ROP, drilling parameters (WOB, RPM, SPP), incidents, NPT | M7: Risk Prediction, M8: Alert Generation |
| **Drilling & Mud Logging DBs** | Real-time parameters, gas readings, lithology, mud properties | M7: Risk Model Training |
| **Historical Well Parameters** | Time-series drilling data, bit records, hydraulics | M6: Hybrid Search, M7: Pattern Recognition |
| **Reservoir & Geological Data** | Formation names, depth intervals, pressure regimes, hazard zones | M5: Depth Correlation, M4: Geological Similarity |
| **eRTMAC Data Streams** | Real-time telemetry (we will **mock/simulate** this) | M8: Live Alert Triggers |
| **Well Trajectory & Survey Data** | Inclination, azimuth, TVD, coordinates | M4: Spatial Relevance, M5: TVDSS Conversion |
| **Casing/Cementing/Mud Programs** | Casing depths, cement volumes, mud weights, rheology | M6: Search Corpus, M7: Engineering Parameters |
| **Operational Event Records** | Kick events, loss circulation, stuck pipe, fishing, NPT duration | M7: Ground Truth Labels for Risk Models |

### 2.2 Target Extraction Schema (JSON Structure)

```json
{
  "well_metadata": {
    "well_name": "string",
    "field": "string",
    "location": {"lat": "float", "lng": "float"},
    "spud_date": "YYYY-MM-DD",
    "completion_date": "YYYY-MM-DD",
    "total_depth": "float",
    "rig_contractor": "string"
  },
  "formation_tops": [
    {"formation_name": "string", "depth_md": "float", "depth_tvd": "float"}
  ],
  "casing_program": [
    {"size": "float", "depth": "float", "grade": "string", "cement_volume": "float"}
  ],
  "mud_program": [
    {"depth_interval": ["float", "float"], "mud_weight": "float", "mud_type": "string", "rheology": {}}
  ],
  "drilling_parameters": [
    {"timestamp": "ISO8601", "depth": "float", "rop": "float", "wob": "float", "rpm": "float", "torque": "float", "spp": "float", "flow_rate": "float"}
  ],
  "incidents": [
    {"date": "YYYY-MM-DD", "depth": "float", "incident_type": "string", "description": "string", "npt_hours": "float"}
  ]
}
```

---

## 3. Public Data Sources Strategy

### 3.1 Primary Dataset: Equinor Volve Field (Norway)

**Why Volve?**
- ✅ **Gold standard** for drilling AI projects worldwide
- ✅ Contains actual WCRs, DDRs, real-time WITSML, production data
- ✅ ~40,000 files, 7 years of operations (2008-2016)
- ✅ Legally accessible under Equinor Open Data License (free for students/research)
- ✅ Used by winning teams in similar hackathons

**What We'll Use:**

| Document Type | File Format | Purpose | Download Link |
|--------------|-------------|---------|---------------|
| **Well Completion Reports** | PDF (scanned) | OCR extraction demo, formation tops, casing programs | [Volve Official Portal](https://www.equinor.com/energy/volve-data-sharing) |
| **Daily Drilling Reports** | PDF (mixed quality) | OCR stress test, incident extraction, NPT analysis | Same portal + [Andy McDonald's cleaned version](https://www.andymcdonald.scot/data/volve/) |
| **Real-time WITSML Data** | XML/CSV | Ground truth for validating OCR extraction accuracy | [UiS CSV files](https://www.ux.uis.no/~atunkiel/file_list.html) |
| **Well Logs (LAS)** | LAS format | Depth correlation, lithology data | Volve portal |
| **Mud Reports** | PDF | Mud program extraction, rheology parameters | Volve portal |

**Download Instructions:**
1. Visit official portal (no registration required for academic use)
2. Alternative: Kaggle mirror for faster download: https://www.kaggle.com/datasets/lamyalbert/volve-production-data
3. Use Andy McDonald's pre-parsed CSV versions for quick prototyping

---

### 3.2 Secondary Dataset: Utah FORGE (USA)

**Why Utah FORGE?**
- ✅ **Messy scanned DDRs** (perfect for stress-testing OCR)
- ✅ Public geothermal drilling data (DOE funded, fully open)
- ✅ Includes handwritten notes, faxed reports, poor-quality scans
- ✅ Real operational event records (kick events, lost circulation)

**What We'll Use:**

| Document Type | Purpose | Link |
|--------------|---------|------|
| **Well 78B-32 DDRs** | OCR robustness testing (poor scan quality) | [GDR Portal - Search "78B-32"](https://gdr.openei.org) |
| **Well 56-32 Drilling Logs** | Pason data, mud logs, daily reports | Search "FORGE 56-32" on GDR |
| **NPT Event Records** | Ground truth for incident classification | data.gov FORGE catalog |

**Download Instructions:**
1. Go to https://gdr.openei.org
2. Search "FORGE 78B-32" or "FORGE 56-32"
3. Download PDF reports under "Drilling Data and Logs"
4. Also available on data.gov: https://catalog.data.gov/dataset/?tags=forge

---

### 3.3 Tertiary Dataset: Norwegian SODIR (Formerly NPD)

**Why SODIR?**
- ✅ Structured wellbore data from Norwegian Continental Shelf
- ✅ Covers ~5,000+ wells with metadata, casing programs, formation tops
- ✅ CSV export available (no OCR needed — useful for validation baseline)
- ✅ Real operational history including blowouts, incidents

**What We'll Use:**

| Data Type | Purpose | Access |
|-----------|---------|--------|
| **Wellbore Master Data** | Well metadata, locations, depths | [Factpages Wellbore DB](https://factpages.sodir.no/en/wellbore) - Export as CSV |
| **Historical Incidents** | Kick/blowout records for risk model training | Same portal - "Incidents" section |
| **Casing Programs** | Structured casing data (no OCR needed) | Wellbore details export |

**Download Instructions:**
1. Visit https://factpages.sodir.no/en/wellbore
2. Use search filters (e.g., "North Sea" + "Production")
3. Export selected wells to CSV/Excel
4. Download incident reports from "Wellbore - History"

---

### 3.4 Optional: DGH India (Assam-Arakan Basin)

**Status:** ⚠️ **Limited Public Data** — DGH India does not publish detailed well data publicly

**What Might Be Available:**
- Basin-level statistics (not well-specific)
- Regional geological reports (useful for formation name mapping)
- Block allocation maps (useful for spatial context)

**Recommendation:** 
- Use DGH India **only for regional geological nomenclature** (Barail Formation, Girujan Clay, etc.)
- Do NOT expect actual OIL well data from DGH
- Reference DGH publications for **formation depth windows** cited in your demo

**Link:** https://www.dghindia.gov.in (check "Data Management" section)

---

## 4. Data Preparation Workflow

### Phase 1: Download & Organize (Days 1-2)

```
data/
├── raw/
│   ├── volve/
│   │   ├── wcr/              # Well Completion Reports (PDF)
│   │   ├── ddr/              # Daily Drilling Reports (PDF)
│   │   ├── witsml/           # Real-time WITSML (XML/CSV)
│   │   ├── mud_reports/      # Mud logging reports
│   │   └── las_logs/         # Well logs (LAS format)
│   ├── forge/
│   │   ├── 78b32_ddr/        # Utah FORGE DDRs
│   │   ├── 56-32_logs/
│   │   └── incident_reports/
│   └── sodir/
│       ├── wellbore_master.csv
│       ├── casing_programs.csv
│       └── incidents.csv
├── processed/
│   ├── extracted_json/       # OCR output
│   ├── validated/            # Human-verified samples
│   └── training_labels/      # For ML model training
└── synthetic/
    └── oil_india_mock/       # Synthetic OIL data for demo
```

**Action Items:**
1. Download Volve from Kaggle (fastest) or official portal
2. Download Utah FORGE 78B-32 and 56-32 DDRs from GDR
3. Export SODIR wellbore CSV for validation baseline
4. Organize into folder structure above

---

### Phase 2: OCR Extraction Pipeline (Days 3-5)

**Tools:** PaddleOCR + spaCy NLP

**Extraction Steps:**

```python
# Pseudo-code for OCR pipeline
for pdf_file in data/raw/volve/ddr/:
    # Step 1: OCR with PaddleOCR
    raw_text = paddleocr.extract_text(pdf_file)
    
    # Step 2: NLP entity extraction (spaCy)
    entities = {
        "well_name": extract_well_name(raw_text),
        "date": extract_date(raw_text),
        "depth": extract_depth(raw_text),
        "drilling_params": extract_parameters(raw_text),
        "incidents": extract_incidents(raw_text)
    }
    
    # Step 3: Structure into JSON
    json_output = structure_to_schema(entities)
    
    # Step 4: Save to processed/extracted_json/
    save_json(json_output, f"processed/extracted_json/{well_name}_{date}.json")
```

**Target Accuracy Metrics:**
- Well name extraction: **>98%** (critical identifier)
- Depth extraction: **>95%** (numerical precision required)
- Incident detection: **>90%** (NLP challenge with varied terminology)
- Overall structured extraction: **>94%** (compare against WITSML ground truth)

---

### Phase 3: Validation Against Ground Truth (Days 6-7)

**Validation Strategy:**

1. **Use Volve WITSML as Ground Truth**
   - WITSML files contain authoritative drilling parameters
   - Compare OCR-extracted JSON vs. WITSML XML
   - Calculate field-by-field accuracy

2. **Manual Validation Sample**
   - Randomly select 50 DDRs
   - Human reviewer verifies OCR output
   - Calculate precision/recall for incident extraction

3. **Error Analysis**
   - Identify common OCR failures (handwriting, poor scans, tables)
   - Document edge cases for OCR improvement
   - Create confidence scoring system (low/medium/high quality extractions)

**Validation Output:** 
- `data/processed/validation_report.json` with accuracy metrics
- Include this in hackathon presentation as proof of pipeline robustness

---

### Phase 4: Synthetic OIL India Data Generation (Days 8-10)

**Purpose:** Demonstrate system with OIL India context (wells, formations, geography)

**Approach:**
1. Take Volve drilling parameters (real engineering values)
2. Remap metadata to Upper Assam context:
   - Well names: "Nahorkatiya-A1", "Moran-B2", "Digboi-C3"
   - Formations: Barail Formation (3400-3700m hazard zone), Girujan Clay, Tikak Parbat
   - Coordinates: Upper Assam lat/lng (26.5°N, 95.0°E region)
3. Generate synthetic DDRs using Volve templates + OIL nomenclature
4. Save as `data/synthetic/oil_india_mock/`

**Synthetic Data Generator Script:**
```python
# Generate 20 synthetic OIL India wells
oil_wells = [
    {"name": "Nahorkatiya-A1", "location": (26.75, 95.35), "target_depth": 3850},
    {"name": "Moran-B2", "location": (26.82, 94.92), "target_depth": 4100},
    # ... 18 more wells
]

for well in oil_wells:
    # Use Volve drilling parameters as template
    template_data = random.choice(volve_extracted_jsons)
    
    # Remap to OIL India context
    oil_data = {
        "well_name": well["name"],
        "location": well["location"],
        "drilling_params": template_data["drilling_params"],  # Real values
        "formations": map_to_assam_formations(template_data["formations"]),
        "incidents": template_data["incidents"]  # Keep real incident patterns
    }
    
    save_json(oil_data, f"synthetic/oil_india_mock/{well['name']}.json")
```

---

## 5. Database Schema Population

### 5.1 Module 1 Integration

Once OCR extraction is complete, populate **Module 1: Database Schema** tables:

**Tables to Populate:**

1. **`wells` table**
   - Source: WCR metadata (well name, location, depths)
   - Insert synthetic OIL India wells + Volve wells (for validation)

2. **`offset_well_documents` table**
   - Source: Full PDF files (store as BLOB or file path)
   - Link to extracted JSON in `document_chunks` table

3. **`document_chunks` table**
   - Source: Page-by-page OCR extraction
   - Store raw text + vector embeddings (for Module 6: Hybrid Search)

4. **`drilling_logs` table**
   - Source: WITSML/DDR time-series data
   - Insert drilling parameters at 1-minute intervals

5. **`incidents` table**
   - Source: Extracted incident records from DDRs
   - Critical for Module 7: Risk Prediction training labels

**Population Script:**
```sql
-- Example: Insert well from OCR extraction
INSERT INTO wells (well_id, name, location, spud_date, total_depth)
SELECT 
    json_extract(data, '$.well_metadata.well_name'),
    json_extract(data, '$.well_metadata.field'),
    ST_Point(json_extract(data, '$.well_metadata.location.lng'), 
             json_extract(data, '$.well_metadata.location.lat')),
    json_extract(data, '$.well_metadata.spud_date'),
    json_extract(data, '$.well_metadata.total_depth')
FROM processed_json_files;
```

---

## 6. Quality Assurance Checklist

### 6.1 OCR Pipeline Validation

- [ ] **Extraction Accuracy >94%** (compare vs. WITSML ground truth)
- [ ] **Well name extraction >98%** (critical for data integrity)
- [ ] **Depth correlation accuracy** (MD vs. TVD correctly extracted)
- [ ] **Incident detection recall >90%** (no missed kick/loss events)
- [ ] **Confidence scoring implemented** (flag low-quality extractions)

### 6.2 Data Coverage

- [ ] **At least 50 Volve WCRs** extracted and validated
- [ ] **At least 200 Volve DDRs** processed (covers multiple wells)
- [ ] **20 Utah FORGE DDRs** (demonstrates OCR robustness on poor scans)
- [ ] **20 Synthetic OIL India wells** generated with realistic parameters
- [ ] **SODIR data imported** for validation baseline

### 6.3 Database Population

- [ ] **Wells table:** 70+ wells (50 Volve + 20 synthetic OIL)
- [ ] **Document chunks:** >5,000 chunks (embedded for search)
- [ ] **Drilling logs:** >500,000 time-series records
- [ ] **Incidents:** >100 labeled events (for risk model training)

---

## 7. Presentation Strategy for Hackathon

### 7.1 Transparency Statement (Recommended)

> **Data Source Disclosure:**  
> "Our system is trained on publicly available analogous datasets (Equinor Volve, Utah FORGE) which provide real-world drilling document complexity comparable to OIL India's operations. We demonstrate the system using synthetic wells styled on Upper Assam nomenclature (Nahorkatiya, Moran, Digboi fields) with engineering parameters from proven offshore operations. Post-deployment, the OCR/NLP pipeline is designed for direct integration with OIL India's actual WCR/DDR corpus without architectural changes."

### 7.2 Demo Script

1. **Show OCR Pipeline in Action**
   - Live demo: Upload a Volve DDR PDF → Extract JSON in real-time
   - Display validation metrics: "94.7% field extraction accuracy"

2. **Display Synthetic OIL India Well**
   - Map view showing Nahorkatiya field with 5 wells
   - Click "Nahorkatiya-A1" → Show extracted formation tops (Barail Formation @ 3,456m)
   - Highlight incident: "Lost circulation event @ 3,542m (Barail hazard zone)"

3. **Validate Against Ground Truth**
   - Side-by-side: OCR-extracted JSON vs. Official WITSML
   - Show accuracy metrics: "Depth extraction: 98.2% accurate"

---

## 8. Download Links Summary

### Primary Sources (Start Here)

1. **Equinor Volve Field**
   - Official: https://www.equinor.com/energy/volve-data-sharing
   - Kaggle (faster): https://www.kaggle.com/datasets/lamyalbert/volve-production-data
   - Cleaned CSVs: https://www.andymcdonald.scot/data/volve/
   - WITSML CSVs: https://www.ux.uis.no/~atunkiel/file_list.html

2. **Utah FORGE (DOE Geothermal)**
   - Main portal: https://gdr.openei.org
   - Search: "FORGE 78B-32" and "FORGE 56-32"
   - Direct link: https://gdr.openei.org/search?q=FORGE

3. **Norwegian SODIR**
   - Wellbore database: https://factpages.sodir.no/en/wellbore
   - Export as CSV (no login required)

4. **DGH India (Optional - Regional Context Only)**
   - Portal: https://www.dghindia.gov.in
   - Check "Data Management" for basin reports

---

## 9. Success Criteria

### Module 2 (Document Ingestion) Completion Definition

✅ **Pipeline Operational:**
- OCR + NLP extraction working end-to-end
- Handles PDF (WCR/DDR), XML (WITSML), CSV formats
- Outputs structured JSON matching target schema

✅ **Validation Passed:**
- >94% extraction accuracy vs. WITSML ground truth
- >90% incident detection recall
- Confidence scoring identifies low-quality extractions

✅ **Database Populated:**
- 70+ wells in database (50 real + 20 synthetic)
- >5,000 searchable document chunks (for Module 6)
- >100 labeled incidents (for Module 7 training)

✅ **Demo Ready:**
- Can process uploaded PDF in <30 seconds
- Display extraction results in UI with confidence scores
- Show validation metrics in presentation

---

## 10. Timeline & Milestones

| Days | Phase | Deliverable |
|------|-------|-------------|
| 1-2 | Data Download | All Volve/FORGE/SODIR data organized in `data/raw/` |
| 3-5 | OCR Pipeline Build | PaddleOCR + spaCy extraction working, outputs JSON |
| 6-7 | Validation | Accuracy metrics calculated, validation report generated |
| 8-10 | Synthetic Data | 20 OIL India wells generated, database populated |
| 11-12 | Integration | Module 2 feeds into Module 4 (Offset Relevance) and Module 7 (Risk Prediction) |

**Checkpoint:** By Day 7, OCR pipeline must achieve >90% accuracy or pivot to manual data entry for demo wells.

---

## 11. Risk Mitigation

### Risk 1: OCR Accuracy Below 90%

**Mitigation:**
- Use Volve CSV files (already digitized) as fallback
- Manual correction for 20 demo wells (feasible in 2 days)
- Focus OCR demo on high-quality PDFs only

### Risk 2: Volve Data Download Issues

**Mitigation:**
- Use Kaggle mirror (faster, no registration)
- Andy McDonald's pre-parsed CSVs as backup
- SODIR CSV export as last resort (structured data, no OCR needed)

### Risk 3: Insufficient Incident Labels for Risk Model

**Mitigation:**
- Combine Volve + FORGE + SODIR incident records (should yield 100+)
- Synthetic incident generation if needed (use templates from real events)
- Focus risk model on 2-3 incident types (kick, loss, stuck pipe) instead of all 5

---

## 12. Next Steps (Action Items)

### Immediate (Today)
1. ✅ Download Volve dataset from Kaggle (fastest option)
2. ✅ Download Utah FORGE 78B-32 DDRs from GDR portal
3. ✅ Set up `data/raw/` folder structure

### This Week
1. Build OCR extraction script (PaddleOCR + spaCy)
2. Process 10 Volve DDRs as proof-of-concept
3. Calculate initial accuracy metrics

### Next Week
1. Scale to 200+ DDRs
2. Generate 20 synthetic OIL India wells
3. Populate Module 1 database tables

---

## 13. Additional Resources

### Useful References for OIL India Geology

**Assam-Arakan Basin Formations (Use for synthetic data mapping):**
- **Barail Formation** (3,400-3,700m): Known hazard zone for lost circulation
- **Girujan Clay**: Upper formation, shale-prone
- **Tikak Parbat Limestone**: Carbonate reservoir
- **Kopili Formation**: Older Eocene shales
- **Sylhet Limestone**: Paleocene reservoir

**OIL India Operating Fields (Use for well naming):**
- Nahorkatiya Field (Dibrugarh District)
- Moran Field (Dibrugarh District)
- Digboi Field (Tinsukia District) - India's oldest producing field
- Duliajan Field (Dibrugarh District)
- Hugrijan Field (Dibrugarh District)

**Synthetic Well Coordinate Reference:**
- Upper Assam region: 26.5°N - 27.5°N, 94.5°E - 95.5°E
- Use approximate coordinates near known fields (publicly available on maps)

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-09-27 | Initial data collection plan created | Team eRTMAC-NWIS |

---

**Team Note:** This plan prioritizes **speed** (use pre-digitized Volve CSVs for quick start) and **credibility** (validate OCR against WITSML ground truth). Focus OCR effort on 20-50 high-value demo PDFs rather than processing all 40,000 Volve files. Remember: judges care more about your pipeline architecture and validation methodology than the volume of data processed.
