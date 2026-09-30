# Competitor Repository Audit: DDR_UTAH_FORGE

## 1. Repository Metadata
- **Repository**: `DDR_UTAH_FORGE`
- **URL**: `https://github.com/djimrastephane/DDR_UTAH_FORGE.git`
- **Owner**: djimrastephane
- **Project**: DDR Utah FORGE — Geothermal Drilling Knowledge Mining & Causality RAG
- **Category**: Domain Drilling Intelligence / Benchmark Pipeline
- **Relevance**: High (Deepest document extraction, OCR segmentation, and causality tracking pipeline)
- **Primary Language**: Python (FastAPI, Streamlit, PyMuPDF, OpenCV, NetworkX, ChromaDB)
- **Files Inspected**: 108 code files across `src/ddr_rag/`, `src/rag_pdf/`, `app/ui/`, `app/api/`, `dashboards/`, `scripts/`.

---

## 2. Architecture & Tech Stack Reconstructed
```
[Streamlit Multi-Page Dashboard (`app/ui/page_modules/`)]
   ├── Campaign Summary & Well Overview (`well_overview.py`, `campaign_summary.py`)
   ├── Operations Log & Sequence Tracker (`operations_log.py`, `operation_sequence.py`)
   ├── NPT Intelligence & Root Cause Tracker (`npt_intelligence.py`, `root_cause_tracker.py`)
   ├── Operational Causality Graph (`operational_graph.py` via NetworkX)
   └── Corpus Search & Lessons Learned (`corpus_search.py`, `lessons_learned.py`)
        │
        ▼ (FastAPI Service: `app/api/main.py`)
[RAG & PDF Vision Pipeline (`src/rag_pdf/`)]
   ├── Page Extraction & Rotation Correction (`extract_page.py`, `rotation_handler.py`)
   ├── Region Classification & Layout Segmentation (`region_classify.py`, `region_segment.py`)
   ├── OCR Quality Scoring & Table Fallback (`ocr_quality.py`, `ocr_table_fallback.py`)
   ├── Heading Hierarchy & Boilerplate Stripper (`headings.py`, `boilerplate.py`)
   └── Hybrid Question Router (`question_router.py`)
        │
        ▼
[Domain Analytics & Causality Engine (`src/ddr_rag/`)]
   ├── Phase-Based Causality Analyzer (`causality_analyzer.py`: MIRU -> COND -> INTRM -> PROD)
   ├── Multi-Category NPT Classifier (`npt_classifier.py` across 14 categories)
   ├── Domain Graph Builder (`graph_builder.py` with sliding window co-occurrence)
   └── Extraction Profile Registry (`extractor_registry.py`, `ddr_profile.py`)
```

---

## 3. Verified vs Mock vs Claimed Breakdown

| Capability / Feature | Implementation Status | Evidence / Code Path | Notes & Findings |
| :--- | :--- | :--- | :--- |
| **Nearby Well Discovery** | ❌ **NOT FOUND** | N/A | Wells are grouped by static project campaigns (`UtahForge/wells/FORGE-16A-32`), not spatial radius. |
| **GIS / Map Interface** | 🟡 **PARTIAL** | `app/ui/page_modules/well_overview.py` | 2D schematic plot of well locations; no PostGIS, spatial indexing, or satellite layers. |
| **Historical DDR / EOWR Parsing** | ✅ **VERIFIED** | `src/rag_pdf/extract_page.py`, `src/ddr_rag/ddr_extractor.py` | Highly robust PDF parsing with layout bounding-box segmentation and OCR quality validation. |
| **OCR Quality & Fallback** | ✅ **VERIFIED** | `src/rag_pdf/ocr_quality.py`, `ocr_table_fallback.py` | Assesses character density and OCR confidence, falling back to OpenCV contour table extraction. |
| **NLP Event Extraction** | ✅ **VERIFIED** | `src/ddr_rag/npt_classifier.py` | 14-class NPT hierarchy (fishing, well control, bop, mpd, equipment, tools, weather, logistics). |
| **RAG Retrieval** | ✅ **VERIFIED** | `src/rag_pdf/retrieval/` | ChromaDB vector search combined with section and heading metadata filtering. |
| **Hybrid Search** | 🟡 **PARTIAL** | `src/rag_pdf/question_router.py` | Routes between dense vector and structured metadata queries based on query intent. |
| **Formation Correlation** | ❌ **NOT FOUND** | N/A | No formation thickness scaling or dip projection (geothermal crystalline basement setting). |
| **Depth Correlation** | 🟡 **PARTIAL** | `src/ddr_rag/causality_analyzer.py` | Phase and depth window tracking, but lacks TVDSS trajectory calculation. |
| **Phase Causality Analysis** | ✅ **VERIFIED** | `src/ddr_rag/causality_analyzer.py` L40-95 | Measures escalating term frequencies and carryover NPT signals across casing phase transitions. |
| **Knowledge Graph** | ✅ **VERIFIED** | `src/ddr_rag/graph_builder.py` | NetworkX operational co-occurrence graph linking operations, NPT codes, and equipment. |
| **Evidence Citations** | ✅ **VERIFIED** | `app/ui/ui_artifacts.py` | Direct page-level source attribution with exact section headers. |
| **Real-Time Telemetry** | ❌ **NOT FOUND** | N/A | Batch post-drilling analysis platform. |

---

## 4. Code-Level Investigation & Gaps
1. **Geothermal Granitic Domain Bias**:
   - Built on Utah FORGE hard-rock geothermal data (granite basement). It lacks hydrocarbon sedimentary physics (pore pressure, gas kicks, shale swelling, differential sticking in depleted sands).
2. **Missing Geospatial Subsurface Integration**:
   - Does not integrate PostGIS, trajectory calculations, or regional fault maps.
3. **No Real-Time Telemetry or Lookahead**:
   - Designed strictly as an offline post-drilling knowledge mining tool, not an active RTOC decision support platform during live drilling.

---

## 5. What We Can Learn & PS 121 Differentiation
- **Strengths to Learn From**: The phase-transition causality engine (`causality_analyzer.py`), OpenCV table OCR fallback (`ocr_table_fallback.py`), and 14-category NPT classifier are masterclasses in drilling domain engineering.
- **Our Opportunities**:
  1. Adapt the deep PDF OCR and layout segmentation pipeline to Assam-Arakan sedimentary EOWR and DDR formats.
  2. Integrate the causality engine with active 3D well trajectories and live telemetry.
  3. Layer PostGIS spatial discovery and Eaton PPFG mud window calculations over the document knowledge graph.
