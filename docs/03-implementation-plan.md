# Implementation Plan
## SIH 26121 - eRTMAC-NWIS
## Modular Architecture & Development Roadmap

**Document Version:** 1.0  
**Last Updated:** September 27, 2026  
**Status:** Active  
**Team:** SIH 2026 Hackathon Team

---

## 📋 Table of Contents
1. [System Architecture Overview](#1-system-architecture-overview)
2. [Module Breakdown](#2-module-breakdown)
3. [Technology Stack](#3-technology-stack)
4. [Development Sequence](#4-development-sequence)
5. [Module Implementation Plans](#5-module-implementation-plans)
6. [Integration Strategy](#6-integration-strategy)
7. [Testing & Validation](#7-testing--validation)
8. [Deployment Architecture](#8-deployment-architecture)

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NWIS SYSTEM ARCHITECTURE                             │
│                                                                              │
│  ┌────────────────────────┐         ┌────────────────────────┐              │
│  │   FRONTEND LAYER       │         │   DATA INGESTION       │              │
│  │  (React + TypeScript)  │         │   PIPELINE             │              │
│  │                        │         │  (Background Workers)  │              │
│  │  ┌──────────────────┐  │         │                        │              │
│  │  │ Command Cockpit  │  │         │  ┌──────────────────┐  │              │
│  │  │ - GIS Map        │  │         │  │ PDF Ingestion    │  │              │
│  │  │ - Depth Track    │  │         │  │ OCR + NLP        │  │              │
│  │  │ - Risk Gauges    │  │         │  │ Event Extraction │  │              │
│  │  │ - Alert Banner   │  │         │  └──────────────────┘  │              │
│  │  └──────────────────┘  │         └────────────────────────┘              │
│  └────────────────────────┘                     │                           │
│              │                                   │                           │
│              │ WebSocket                         │                           │
│              │ REST API                          │                           │
│              ↓                                   ↓                           │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │                    BACKEND API LAYER                            │        │
│  │                   (FastAPI + Python)                             │        │
│  │                                                                  │        │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │        │
│  │  │ Well Context │  │ Search API   │  │ Risk API     │          │        │
│  │  │ Manager      │  │              │  │              │          │        │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │        │
│  └─────────────────────────────────────────────────────────────────┘        │
│              │                    │                    │                    │
│              ↓                    ↓                    ↓                    │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │                     INTELLIGENCE LAYER                           │        │
│  │                  (Core Business Logic)                           │        │
│  │                                                                  │        │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐  │        │
│  │  │ Offset Relevance│  │ Depth Correlation│  │ Risk Engine    │  │        │
│  │  │ Engine          │  │ Engine           │  │ (5 Models)     │  │        │
│  │  └─────────────────┘  └─────────────────┘  └────────────────┘  │        │
│  │                                                                  │        │
│  │  ┌─────────────────┐  ┌─────────────────┐                       │        │
│  │  │ Hybrid Search   │  │ Alert Generator │                       │        │
│  │  │ (BM25 + Vector) │  │                 │                       │        │
│  │  └─────────────────┘  └─────────────────┘                       │        │
│  └─────────────────────────────────────────────────────────────────┘        │
│              │                    │                    │                    │
│              ↓                    ↓                    ↓                    │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │                      DATA LAYER                                  │        │
│  │                                                                  │        │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │        │
│  │  │ PostgreSQL + │  │ Vector Store │  │ Redis Cache  │          │        │
│  │  │ PostGIS      │  │ (pgvector)   │  │              │          │        │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │        │
│  └─────────────────────────────────────────────────────────────────┘        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │                   EXTERNAL INTERFACES                            │        │
│  │                                                                  │        │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │        │
│  │  │ eRTMAC Stream│  │ Document Repo│  │ WITSML Parser│          │        │
│  │  │ (Optional)   │  │ (File System)│  │              │          │        │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │        │
│  └─────────────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

1. **Modular Independence:** Each module can be developed, tested, and deployed independently
2. **Clean Interfaces:** REST APIs between layers; no tight coupling
3. **Fail-Safe Degradation:** If AI fails → fallback to rule-based logic
4. **Offline-First:** Rig-site deployment must work without HQ connectivity
5. **Evidence-Backed:** Every alert traceable to source documents
6. **Air-Gapped:** No external API dependencies (on-premise only)

---

## 2. Module Breakdown

### 2.1 Module Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MODULE DEPENDENCIES                          │
│                                                                     │
│  Level 1 (Foundation)                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ M1: Database │  │ M2: Document │  │ M3: Data     │              │
│  │ Schema       │  │ Ingestion    │  │ Generator    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│         │                   │                   │                   │
│         └───────────────────┴───────────────────┘                   │
│                             ↓                                       │
│  Level 2 (Core Intelligence)                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ M4: Offset   │  │ M5: Depth    │  │ M6: Hybrid   │              │
│  │ Relevance    │  │ Correlation  │  │ Search       │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│         │                   │                   │                   │
│         └───────────────────┴───────────────────┘                   │
│                             ↓                                       │
│  Level 3 (Risk & Alerts)                                            │
│  ┌──────────────┐  ┌──────────────┐                                │
│  │ M7: Risk     │  │ M8: Alert    │                                │
│  │ Engine       │  │ Generator    │                                │
│  └──────────────┘  └──────────────┘                                │
│         │                   │                                       │
│         └───────────────────┘                                       │
│                             ↓                                       │
│  Level 4 (API & UI)                                                 │
│  ┌──────────────┐  ┌──────────────┐                                │
│  │ M9: Backend  │  │ M10: Frontend│                                │
│  │ API          │  │ Cockpit      │                                │
│  └──────────────┘  └──────────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Module Summary Table

| Module ID | Module Name | Owner (Team Member) | Dependencies | Estimated Time |
|-----------|-------------|---------------------|--------------|----------------|
| **M1** | Database Schema & Models | Backend Lead | None | 2 days |
| **M2** | Document Ingestion Pipeline | ML Engineer | M1 | 4 days |
| **M3** | Synthetic Data Generator | Data Engineer | M1 | 3 days |
| **M4** | Offset Relevance Engine | ML Engineer | M1, M3 | 5 days |
| **M5** | Depth Correlation Engine | Domain Expert | M1, M3 | 4 days |
| **M6** | Hybrid Search System | Backend Lead | M1, M2 | 4 days |
| **M7** | Risk Prediction Engine | ML Engineer | M4, M5, M6 | 6 days |
| **M8** | Alert Generation System | Backend Lead | M7 | 3 days |
| **M9** | Backend API Layer | Backend Lead | M4-M8 | 4 days |
| **M10** | Frontend Command Cockpit | Frontend Lead | M9 | 6 days |
| **M11** | Integration & Testing | Full Team | All | 4 days |

**Total Estimated Timeline:** 35 days (parallel work reduces to ~21 days)

---

## 3. Technology Stack

### 3.1 Core Technology Choices

#### Frontend
```yaml
Framework: React 18 + TypeScript
State Management: Zustand (lightweight Redux alternative)
UI Components: shadcn/ui + Tailwind CSS
Maps: React Leaflet + OpenStreetMap tiles (cached locally)
Charts: Recharts (drilling telemetry) + Plotly (stratigraphic tracks)
Real-time: Socket.IO client
Build Tool: Vite
```

#### Backend
```yaml
Framework: FastAPI (Python 3.11+)
Async Runtime: uvicorn + asyncio
Background Tasks: Celery + Redis
Real-time: Socket.IO server
API Documentation: OpenAPI/Swagger (auto-generated)
```

#### Data Layer
```yaml
Primary Database: PostgreSQL 15 + PostGIS
Vector Store: pgvector extension
Cache: Redis 7
Search: BM25 (rank_bm25 library) + Vector similarity
```

#### ML/AI Stack
```yaml
NLP: spaCy + transformers (Hugging Face)
LLM: Ollama + Llama 3.2 (local, air-gapped)
OCR: Tesseract + PaddleOCR (for handwritten text)
Document Parsing: unstructured.io
ML Models: scikit-learn, XGBoost
Anomaly Detection: PyOD (Python Outlier Detection)
Explainability: SHAP (SHapley Additive exPlanations)
```

#### Data Processing
```yaml
WITSML Parsing: Custom Python parser (WITSML 2.1)
Geospatial: GeoPandas, Shapely
Depth Conversion: Custom trigonometry library
```

#### DevOps & Deployment
```yaml
Containerization: Docker + docker-compose
Reverse Proxy: Nginx
Monitoring: Prometheus + Grafana (optional for MVP)
Logging: ELK stack (Elasticsearch, Logstash, Kibana) - simplified for MVP
```

### 3.2 Why These Choices?

| Technology | Reason |
|------------|--------|
| **FastAPI** | Async support, auto-docs, WebSocket, type-safe |
| **PostgreSQL + PostGIS** | Industry-standard, geospatial support, WITSML-compatible |
| **pgvector** | Vector similarity search without external services (air-gapped) |
| **Ollama + Llama 3.2** | Local LLM execution (no cloud APIs) |
| **React + TypeScript** | Modern, type-safe, rich ecosystem |
| **Tailwind + shadcn/ui** | Rapid UI development, dark mode support |
| **React Leaflet** | Offline map tile support |
| **Celery + Redis** | Reliable background job processing (PDF ingestion) |

---

## 4. Development Sequence

### 4.1 Sprint Plan (4 Sprints × 5 days = 20 days)

```
┌───────────────────────────────────────────────────────────────────────┐
│ SPRINT 0: Setup (2 days)                                             │
│ ├─ Initialize Git repository                                          │
│ ├─ Setup Docker development environment                               │
│ ├─ Create project structure                                           │
│ └─ Team onboarding & role assignment                                  │
└───────────────────────────────────────────────────────────────────────┘
         ↓
┌───────────────────────────────────────────────────────────────────────┐
│ SPRINT 1: Foundation (5 days) - Parallel Work                        │
│ Team A (Backend):                                                     │
│ ├─ M1: Database schema + SQLAlchemy models                            │
│ ├─ M3: Synthetic data generator (10 wells)                            │
│ └─ Basic CRUD APIs                                                    │
│                                                                       │
│ Team B (ML/Data):                                                     │
│ ├─ M2: Document ingestion pipeline (PDF → JSON)                       │
│ ├─ OCR testing with sample reports                                    │
│ └─ NLP extraction prototypes                                          │
│                                                                       │
│ Team C (Frontend):                                                    │
│ ├─ React project setup                                                │
│ ├─ UI component library setup                                         │
│ └─ Basic map view prototype                                           │
│                                                                       │
│ Sprint Goal: Database + Sample Data + Basic Infra                     │
└───────────────────────────────────────────────────────────────────────┘
         ↓
┌───────────────────────────────────────────────────────────────────────┐
│ SPRINT 2: Core Intelligence (5 days) - Parallel Work                 │
│ Team A (Backend):                                                     │
│ ├─ M4: Offset relevance engine                                        │
│ ├─ M5: Depth correlation (MD → TVDSS)                                │
│ └─ API endpoints for relevance queries                                │
│                                                                       │
│ Team B (ML/Data):                                                     │
│ ├─ M6: Hybrid search (BM25 + vector)                                  │
│ ├─ Event embedding generation                                         │
│ └─ Search quality testing                                             │
│                                                                       │
│ Team C (Frontend):                                                    │
│ ├─ Interactive GIS map with radius slider                             │
│ ├─ Well list view with relevance scores                               │
│ └─ Depth correlation visualization (dual track)                       │
│                                                                       │
│ Sprint Goal: Functional Offset Discovery + Search                     │
└───────────────────────────────────────────────────────────────────────┘
         ↓
┌───────────────────────────────────────────────────────────────────────┐
│ SPRINT 3: Risk & Alerts (5 days) - Parallel Work                     │
│ Team A (Backend):                                                     │
│ ├─ M7: Risk engine framework (5 models)                               │
│ ├─ M8: Alert generation logic                                         │
│ └─ WebSocket real-time push                                           │
│                                                                       │
│ Team B (ML/Data):                                                     │
│ ├─ Implement 2-3 risk models (Lost Circ, Stuck Pipe)                  │
│ ├─ Anomaly detection algorithms                                       │
│ └─ Model evaluation metrics                                           │
│                                                                       │
│ Team C (Frontend):                                                    │
│ ├─ Risk gauge components                                              │
│ ├─ Alert banner with color states                                     │
│ ├─ Evidence viewer modal                                              │
│ └─ Historical risk corridor visualization                             │
│                                                                       │
│ Sprint Goal: Proactive Alert System Functional                        │
└───────────────────────────────────────────────────────────────────────┘
         ↓
┌───────────────────────────────────────────────────────────────────────┐
│ SPRINT 4: Integration & Polish (5 days) - Full Team                  │
│ ├─ M9: Complete backend API documentation                             │
│ ├─ M10: Complete frontend command cockpit                             │
│ ├─ M11: End-to-end integration testing                                │
│ ├─ Demo scenario preparation (recorded drill simulation)              │
│ ├─ Performance optimization                                           │
│ ├─ Documentation & presentation deck                                  │
│ └─ Final bug fixes                                                    │
│                                                                       │
│ Sprint Goal: Shippable MVP Demo                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### 4.2 Critical Path Analysis

**Critical Path (Must be sequential):**
```
M1 (Database) → M3 (Data Generator) → M4 (Offset Relevance) → M7 (Risk Engine) → M8 (Alerts) → M10 (UI)
```

**Parallel Tracks (Can work simultaneously):**
```
Track 1 (Data): M2 (Ingestion) → M6 (Search)
Track 2 (Intelligence): M4 (Relevance) → M5 (Correlation) → M7 (Risk)
Track 3 (Frontend): Basic UI → Map → Dashboard → Final Polish
```

---

## 5. Module Implementation Plans

### MODULE 1: Database Schema & Models
**Owner:** Backend Lead  
**Dependencies:** None  
**Duration:** 2 days

#### Implementation Steps
1. **Design WITSML-compatible schema** (Day 1)
   ```sql
   -- Core tables
   CREATE TABLE wells (
       well_id UUID PRIMARY KEY,
       well_name VARCHAR(50) NOT NULL,
       location GEOGRAPHY(POINT, 4326),
       operator VARCHAR(100),
       field VARCHAR(100),
       spud_date DATE,
       td_depth_m DECIMAL(8,2),
       status VARCHAR(20)
   );

   CREATE TABLE well_trajectories (
       trajectory_id UUID PRIMARY KEY,
       well_id UUID REFERENCES wells(well_id),
       measured_depth_m DECIMAL(8,2),
       inclination_deg DECIMAL(5,2),
       azimuth_deg DECIMAL(5,2),
       tvd_m DECIMAL(8,2),
       tvdss_m DECIMAL(8,2),
       northing_m DECIMAL(10,2),
       easting_m DECIMAL(10,2)
   );

   CREATE TABLE formations (
       formation_id UUID PRIMARY KEY,
       well_id UUID REFERENCES wells(well_id),
       formation_name VARCHAR(100),
       top_depth_md_m DECIMAL(8,2),
       top_depth_tvdss_m DECIMAL(8,2),
       bottom_depth_md_m DECIMAL(8,2),
       lithology VARCHAR(50)
   );

   CREATE TABLE drilling_events (
       event_id UUID PRIMARY KEY,
       well_id UUID REFERENCES wells(well_id),
       event_type VARCHAR(50), -- LOST_CIRC, STUCK_PIPE, KICK, etc.
       depth_start_md_m DECIMAL(8,2),
       depth_end_md_m DECIMAL(8,2),
       formation_name VARCHAR(100),
       severity VARCHAR(20), -- LOW, MEDIUM, HIGH, CRITICAL
       npt_hours DECIMAL(6,2),
       description TEXT,
       mitigation TEXT,
       outcome TEXT,
       source_document VARCHAR(255),
       source_page INTEGER,
       extraction_confidence DECIMAL(3,2),
       event_date DATE
   );

   CREATE TABLE telemetry_snapshots (
       snapshot_id UUID PRIMARY KEY,
       well_id UUID REFERENCES wells(well_id),
       timestamp TIMESTAMP NOT NULL,
       depth_md_m DECIMAL(8,2),
       wob_kn DECIMAL(7,2),
       rpm INTEGER,
       torque_knm DECIMAL(7,2),
       flow_lpm DECIMAL(7,2),
       spp_bar DECIMAL(7,2),
       rop_mhr DECIMAL(6,2),
       mud_weight_kgm3 DECIMAL(7,2),
       pit_volume_m3 DECIMAL(7,2)
   );

   -- Vector embeddings for semantic search
   CREATE TABLE event_embeddings (
       embedding_id UUID PRIMARY KEY,
       event_id UUID REFERENCES drilling_events(event_id),
       embedding VECTOR(768) -- Sentence-BERT dimension
   );

   CREATE INDEX ON event_embeddings USING ivfflat (embedding vector_cosine_ops);
   ```

2. **Create SQLAlchemy models** (Day 2)
   ```python
   # backend/models/well.py
   from sqlalchemy import Column, String, Float, Date
   from geoalchemy2 import Geography
   import uuid

   class Well(Base):
       __tablename__ = "wells"
       
       well_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
       well_name = Column(String(50), nullable=False, index=True)
       location = Column(Geography(geometry_type='POINT', srid=4326))
       operator = Column(String(100))
       field = Column(String(100), index=True)
       spud_date = Column(Date)
       td_depth_m = Column(Float)
       status = Column(String(20))
       
       # Relationships
       trajectories = relationship("WellTrajectory", back_populates="well")
       formations = relationship("Formation", back_populates="well")
       events = relationship("DrillingEvent", back_populates="well")
   ```

3. **Setup Alembic migrations**
   ```bash
   # Initialize Alembic
   alembic init migrations
   
   # Create initial migration
   alembic revision --autogenerate -m "Initial schema"
   alembic upgrade head
   ```

#### Deliverables
- [ ] Complete SQL schema
- [ ] SQLAlchemy ORM models
- [ ] Alembic migration scripts
- [ ] Database seed script (empty tables)

---

### MODULE 2: Document Ingestion Pipeline
**Owner:** ML Engineer  
**Dependencies:** M1 (Database)  
**Duration:** 4 days

#### Implementation Steps

**Day 1-2: OCR & Layout Parsing**
```python
# backend/ingestion/pdf_processor.py
from unstructured.partition.pdf import partition_pdf
from paddleocr import PaddleOCR
import pytesseract

class PDFProcessor:
    def __init__(self):
        self.ocr_engine = PaddleOCR(lang='en')
        
    def extract_text(self, pdf_path: str) -> List[Dict]:
        """Extract text with layout awareness"""
        elements = partition_pdf(
            filename=pdf_path,
            strategy="hi_res",  # High-resolution mode
            extract_images_in_pdf=False
        )
        
        pages = []
        for element in elements:
            pages.append({
                "page_num": element.metadata.page_number,
                "text": element.text,
                "type": element.category,  # Title, Text, Table
                "bbox": element.metadata.coordinates
            })
        return pages
    
    def enhance_with_ocr(self, pdf_path: str) -> str:
        """Fallback OCR for scanned/handwritten pages"""
        result = self.ocr_engine.ocr(pdf_path, cls=True)
        text = "\n".join([line[1][0] for page in result for line in page])
        return text
```

**Day 3: NLP Event Extraction**
```python
# backend/ingestion/event_extractor.py
import spacy
from transformers import pipeline

class EventExtractor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.ner = pipeline("ner", model="dslim/bert-base-NER")
        
        # Domain-specific patterns
        self.event_patterns = {
            "LOST_CIRCULATION": r"(lost|loss of|partial loss|total loss|circulation|returns)",
            "STUCK_PIPE": r"(stuck|pipe stuck|tight hole|overpull|jarring)",
            "KICK": r"(kick|gas|influx|well control|shut[- ]in)",
            "TORQUE_SPIKE": r"(high torque|torque spike|erratic torque)",
        }
        
    def extract_events(self, text: str, well_name: str) -> List[Dict]:
        """Extract drilling events from DDR text"""
        doc = self.nlp(text)
        events = []
        
        for sent in doc.sents:
            sent_text = sent.text.lower()
            
            # Match event type
            event_type = None
            for etype, pattern in self.event_patterns.items():
                if re.search(pattern, sent_text, re.IGNORECASE):
                    event_type = etype
                    break
            
            if event_type:
                # Extract depth (e.g., "at 3,245 m", "3245m", "3245 meters")
                depth_match = re.search(r'(\d{1,4}[,.]?\d{1,3})\s*(?:m|meters?|metres?)', sent_text)
                depth_m = float(depth_match.group(1).replace(',', '')) if depth_match else None
                
                # Extract NPT hours
                npt_match = re.search(r'(?:npt|non[- ]?productive time)[:\s]*(\d+(?:\.\d+)?)\s*(?:hr|hour)', sent_text, re.IGNORECASE)
                npt_hours = float(npt_match.group(1)) if npt_match else None
                
                events.append({
                    "event_type": event_type,
                    "depth_start_md_m": depth_m,
                    "description": sent.text,
                    "npt_hours": npt_hours,
                    "extraction_confidence": 0.75  # Placeholder
                })
        
        return events
```

**Day 4: Integration & Testing**
```python
# backend/ingestion/pipeline.py
from celery import Celery
from models import DrillingEvent, EventEmbedding
from sentence_transformers import SentenceTransformer

celery_app = Celery('nwis', broker='redis://localhost:6379')
embedder = SentenceTransformer('all-MiniLM-L6-v2')

@celery_app.task
def process_pdf_async(pdf_path: str, well_id: str):
    """Background task to process uploaded PDF"""
    processor = PDFProcessor()
    extractor = EventExtractor()
    
    # Step 1: Extract text
    pages = processor.extract_text(pdf_path)
    full_text = "\n".join([p["text"] for p in pages])
    
    # Step 2: Extract events
    events = extractor.extract_events(full_text, well_id)
    
    # Step 3: Save to database
    for event_data in events:
        event = DrillingEvent(
            well_id=well_id,
            source_document=pdf_path,
            **event_data
        )
        db.session.add(event)
        db.session.commit()
        
        # Step 4: Generate embedding
        embedding_vec = embedder.encode(event_data["description"])
        embedding = EventEmbedding(
            event_id=event.event_id,
            embedding=embedding_vec.tolist()
        )
        db.session.add(embedding)
    
    db.session.commit()
    return {"processed_events": len(events)}
```

#### Deliverables
- [ ] PDF text extraction working
- [ ] OCR for handwritten reports
- [ ] Event extraction with 75%+ accuracy
- [ ] Celery background job queue
- [ ] Sample processed data (10 PDFs)

---

### MODULE 3: Synthetic Data Generator
**Owner:** Data Engineer  
**Dependencies:** M1 (Database)  
**Duration:** 3 days

#### Purpose
Generate realistic well data for MVP development (since real OIL data unavailable during hackathon).

#### Implementation
```python
# backend/data/synthetic_generator.py
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()

class SyntheticWellGenerator:
    FORMATIONS = [
        ("Tipam Sandstone", 2800, 3200),
        ("Barail Coal", 3200, 3500),
        ("Lakadong Sandstone", 3500, 3800)
    ]
    
    EVENT_TEMPLATES = {
        "LOST_CIRCULATION": [
            "Experienced partial loss of circulation at {depth}m in {formation}. Pumped 25 bbl nut-plug LCM pill. Circulation restored in 4 hours. NPT = 8 hrs.",
            "Total fluid loss at {depth}m. Mixed 30 bbl medium LCM treatment. Returns observed after 6 hours. NPT = 12 hrs."
        ],
        "STUCK_PIPE": [
            "Pipe stuck at {depth}m during trip out. Overpull 150 kN above normal. Worked pipe and jarred up. Freed after 3 hours. NPT = 6 hrs.",
            "Tight hole at {depth}m. High torque and drag. Applied back-reaming. Cleared restriction in 5 hours. NPT = 10 hrs."
        ]
    }
    
    def generate_field(self, num_wells=20):
        """Generate a synthetic oil field"""
        # Field center: Nahorkatiya, Assam (approx coordinates)
        field_center = (27.37, 95.35)
        
        wells = []
        for i in range(num_wells):
            well = self._generate_well(i, field_center)
            wells.append(well)
        
        return wells
    
    def _generate_well(self, index, center):
        # Random offset within 50km radius
        lat_offset = random.uniform(-0.45, 0.45)  # ~50km
        lon_offset = random.uniform(-0.45, 0.45)
        
        well_data = {
            "well_name": f"NHK-{index+1:03d}",
            "location": (center[0] + lat_offset, center[1] + lon_offset),
            "field": "Nahorkatiya",
            "operator": "Oil India Limited",
            "spud_date": fake.date_between(start_date='-5y', end_date='-1y'),
            "td_depth_m": random.randint(3000, 4000),
            "status": "COMPLETED"
        }
        
        # Generate trajectory
        well_data["trajectory"] = self._generate_trajectory(well_data["td_depth_m"])
        
        # Generate formations
        well_data["formations"] = self._generate_formations()
        
        # Generate 0-3 random events
        well_data["events"] = self._generate_events(well_data["well_name"])
        
        return well_data
    
    def _generate_trajectory(self, td_depth):
        """Generate deviated well trajectory"""
        trajectory = []
        inclination = random.uniform(0, 45)  # 0-45 degree deviation
        azimuth = random.uniform(0, 360)
        
        for md in range(0, int(td_depth) + 1, 100):
            tvd = md * math.cos(math.radians(inclination))
            tvdss = tvd - 350  # Ground elevation ~350m above sea level
            
            trajectory.append({
                "measured_depth_m": md,
                "inclination_deg": inclination,
                "azimuth_deg": azimuth,
                "tvd_m": tvd,
                "tvdss_m": tvdss
            })
        
        return trajectory
    
    def _generate_events(self, well_name):
        """Generate 0-3 realistic drilling events"""
        num_events = random.randint(0, 3)
        events = []
        
        for _ in range(num_events):
            event_type = random.choice(list(self.EVENT_TEMPLATES.keys()))
            template = random.choice(self.EVENT_TEMPLATES[event_type])
            
            formation = random.choice(self.FORMATIONS)
            depth = random.randint(formation[1], formation[2])
            
            description = template.format(
                depth=depth,
                formation=formation[0]
            )
            
            # Extract NPT from description
            npt_match = re.search(r'NPT = (\d+)', description)
            npt_hours = float(npt_match.group(1)) if npt_match else None
            
            events.append({
                "event_type": event_type,
                "depth_start_md_m": depth,
                "depth_end_md_m": depth + random.randint(5, 30),
                "formation_name": formation[0],
                "severity": random.choice(["MEDIUM", "HIGH"]),
                "description": description,
                "npt_hours": npt_hours,
                "extraction_confidence": 1.0  # Synthetic = 100%
            })
        
        return events

# Usage
generator = SyntheticWellGenerator()
field_data = generator.generate_field(num_wells=20)

# Save to database
for well_data in field_data:
    well = Well(**well_data)
    db.session.add(well)
    # ... add trajectories, formations, events
db.session.commit()
```

#### Deliverables
- [ ] 20 synthetic wells with realistic data
- [ ] Geographic clustering around Nahorkatiya field
- [ ] 30-50 drilling events distributed across wells
- [ ] Formation tops and trajectories
- [ ] Database seed script

---

### MODULE 4: Offset Relevance Engine
**Owner:** ML Engineer  
**Dependencies:** M1 (Database), M3 (Data)  
**Duration:** 5 days

#### Purpose
Dynamically rank offset wells by relevance to active well's current state.

#### Implementation

**Day 1-2: Relevance Scoring Framework**
```python
# backend/intelligence/offset_relevance.py
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class RelevanceScore:
    well_id: str
    well_name: str
    overall_score: float
    geographic_similarity: float
    formation_similarity: float
    depth_overlap: float
    trajectory_similarity: float
    event_similarity: float
    explanation: str

class OffsetRelevanceEngine:
    def __init__(self, db_session):
        self.db = db_session
        
        # Configurable weights
        self.weights = {
            "geographic": 0.25,
            "formation": 0.30,
            "depth": 0.20,
            "trajectory": 0.15,
            "event": 0.10
        }
    
    def rank_offsets(
        self,
        active_well_id: str,
        current_depth_md: float,
        max_radius_km: float = 50.0
    ) -> List[RelevanceScore]:
        """Rank all offset wells by relevance"""
        
        # Get active well context
        active_well = self.db.query(Well).filter_by(well_id=active_well_id).first()
        active_depth_tvdss = self._get_tvdss(active_well_id, current_depth_md)
        active_formation = self._get_formation_at_depth(active_well_id, active_depth_tvdss)
        
        # Find candidate offset wells (spatial filter)
        candidates = self._find_nearby_wells(active_well.location, max_radius_km)
        
        scores = []
        for candidate in candidates:
            if candidate.well_id == active_well_id:
                continue  # Skip self
            
            score = self._calculate_relevance(
                active_well,
                candidate,
                current_depth_md,
                active_depth_tvdss,
                active_formation
            )
            scores.append(score)
        
        # Sort by overall score
        scores.sort(key=lambda x: x.overall_score, reverse=True)
        return scores
    
    def _calculate_relevance(
        self,
        active_well: Well,
        offset_well: Well,
        current_md: float,
        current_tvdss: float,
        current_formation: str
    ) -> RelevanceScore:
        """Calculate multi-factor relevance score"""
        
        # 1. Geographic Similarity (inverse distance)
        distance_km = self._calculate_distance(active_well.location, offset_well.location)
        geo_score = max(0, 1 - (distance_km / 50))  # Linear decay over 50km
        
        # 2. Formation Similarity (Jaccard index of shared formations)
        active_formations = set([f.formation_name for f in active_well.formations])
        offset_formations = set([f.formation_name for f in offset_well.formations])
        
        if len(active_formations | offset_formations) > 0:
            formation_score = len(active_formations & offset_formations) / len(active_formations | offset_formations)
        else:
            formation_score = 0
        
        # 3. Depth Overlap (does offset well cover current depth?)
        offset_formations_at_depth = [
            f for f in offset_well.formations
            if f.top_depth_tvdss_m <= current_tvdss <= f.bottom_depth_tvdss_m
        ]
        depth_score = 1.0 if offset_formations_at_depth else 0.5
        
        # 4. Trajectory Similarity (vertical vs deviated)
        active_inclination = self._get_inclination_at_depth(active_well.well_id, current_md)
        offset_avg_inclination = self._get_average_inclination(offset_well.well_id)
        
        inclination_diff = abs(active_inclination - offset_avg_inclination)
        trajectory_score = max(0, 1 - (inclination_diff / 45))  # Normalize by 45°
        
        # 5. Event Similarity (does offset have events in same formation?)
        offset_events_in_formation = [
            e for e in offset_well.events
            if e.formation_name == current_formation
        ]
        event_score = min(1.0, len(offset_events_in_formation) / 3)  # Cap at 3 events
        
        # Weighted overall score
        overall = (
            self.weights["geographic"] * geo_score +
            self.weights["formation"] * formation_score +
            self.weights["depth"] * depth_score +
            self.weights["trajectory"] * trajectory_score +
            self.weights["event"] * event_score
        )
        
        explanation = self._generate_explanation(
            distance_km, formation_score, depth_score, event_score
        )
        
        return RelevanceScore(
            well_id=offset_well.well_id,
            well_name=offset_well.well_name,
            overall_score=round(overall, 3),
            geographic_similarity=round(geo_score, 3),
            formation_similarity=round(formation_score, 3),
            depth_overlap=round(depth_score, 3),
            trajectory_similarity=round(trajectory_score, 3),
            event_similarity=round(event_score, 3),
            explanation=explanation
        )
    
    def _generate_explanation(self, distance, formation_sim, depth_sim, event_sim):
        """Human-readable explanation"""
        parts = []
        if distance < 10:
            parts.append(f"Very close ({distance:.1f} km)")
        elif distance < 25:
            parts.append(f"Nearby ({distance:.1f} km)")
        else:
            parts.append(f"Distant ({distance:.1f} km)")
        
        if formation_sim > 0.7:
            parts.append("Shares major formations")
        
        if depth_sim > 0.9:
            parts.append("Drilled same depth interval")
        
        if event_sim > 0.5:
            parts.append("Has relevant historical events")
        
        return " | ".join(parts)
```

#### Deliverables
- [ ] Relevance scoring algorithm
- [ ] Multi-factor weighting system
- [ ] Explainable relevance reasons
- [ ] API endpoint `/api/offsets/relevant`
- [ ] Unit tests (10+ test cases)

---

### MODULE 5: Depth Correlation Engine
**Owner:** Domain Expert  
**Dependencies:** M1 (Database), M3 (Data)  
**Duration:** 4 days

#### Purpose
Align wells by geological horizon (TVDSS) instead of measured depth (MD).

#### Implementation
```python
# backend/intelligence/depth_correlation.py
import math
from typing import List, Tuple

class DepthCorrelationEngine:
    def __init__(self, db_session):
        self.db = db_session
    
    def convert_md_to_tvdss(
        self,
        well_id: str,
        measured_depth_md: float
    ) -> float:
        """Convert measured depth to true vertical depth subsea"""
        
        # Get trajectory survey closest to MD
        trajectory = (
            self.db.query(WellTrajectory)
            .filter_by(well_id=well_id)
            .filter(WellTrajectory.measured_depth_m <= measured_depth_md)
            .order_by(WellTrajectory.measured_depth_m.desc())
            .first()
        )
        
        if not trajectory:
            # Assume vertical if no trajectory data
            return measured_depth_md - 350  # Ground elevation offset
        
        # Interpolate if not exact match
        next_trajectory = (
            self.db.query(WellTrajectory)
            .filter_by(well_id=well_id)
            .filter(WellTrajectory.measured_depth_m > measured_depth_md)
            .order_by(WellTrajectory.measured_depth_m.asc())
            .first()
        )
        
        if next_trajectory:
            # Linear interpolation
            md1, tvdss1 = trajectory.measured_depth_m, trajectory.tvdss_m
            md2, tvdss2 = next_trajectory.measured_depth_m, next_trajectory.tvdss_m
            
            ratio = (measured_depth_md - md1) / (md2 - md1)
            tvdss = tvdss1 + ratio * (tvdss2 - tvdss1)
            return tvdss
        else:
            return trajectory.tvdss_m
    
    def align_wells_by_formation(
        self,
        active_well_id: str,
        offset_well_ids: List[str],
        formation_name: str
    ) -> List[Tuple[float, float]]:
        """Align wells by top of formation"""
        
        active_formation = (
            self.db.query(Formation)
            .filter_by(well_id=active_well_id, formation_name=formation_name)
            .first()
        )
        
        if not active_formation:
            return []
        
        alignments = []
        for offset_id in offset_well_ids:
            offset_formation = (
                self.db.query(Formation)
                .filter_by(well_id=offset_id, formation_name=formation_name)
                .first()
            )
            
            if offset_formation:
                # Calculate depth shift to align formations
                shift = active_formation.top_depth_tvdss_m - offset_formation.top_depth_tvdss_m
                alignments.append((offset_id, shift))
        
        return alignments
    
    def get_historical_corridor(
        self,
        active_well_id: str,
        current_depth_md: float,
        offset_well_ids: List[str],
        lookahead_m: float = 100.0
    ) -> Dict:
        """Find upcoming historical events in offset wells"""
        
        current_tvdss = self.convert_md_to_tvdss(active_well_id, current_depth_md)
        corridor_end_tvdss = current_tvdss + lookahead_m
        
        upcoming_events = []
        for offset_id in offset_well_ids:
            events = (
                self.db.query(DrillingEvent)
                .filter_by(well_id=offset_id)
                .all()
            )
            
            for event in events:
                event_tvdss = self.convert_md_to_tvdss(offset_id, event.depth_start_md_m)
                
                if current_tvdss < event_tvdss <= corridor_end_tvdss:
                    distance_to_event = event_tvdss - current_tvdss
                    upcoming_events.append({
                        "offset_well_id": offset_id,
                        "event_type": event.event_type,
                        "event_tvdss": event_tvdss,
                        "distance_m": distance_to_event,
                        "formation": event.formation_name,
                        "description": event.description
                    })
        
        # Sort by distance
        upcoming_events.sort(key=lambda x: x["distance_m"])
        
        return {
            "current_tvdss_m": current_tvdss,
            "lookahead_end_tvdss_m": corridor_end_tvdss,
            "upcoming_events": upcoming_events
        }
```

#### Deliverables
- [ ] MD → TVDSS conversion algorithm
- [ ] Formation alignment logic
- [ ] Historical risk corridor calculator
- [ ] API endpoint `/api/depth/correlate`
- [ ] Visualization data formatter (for dual-track UI)

---

### MODULE 6: Hybrid Search System
**Owner:** Backend Lead  
**Dependencies:** M1 (Database), M2 (Ingestion)  
**Duration:** 4 days

#### Purpose
Enable natural language search over historical drilling events.

#### Implementation
```python
# backend/intelligence/hybrid_search.py
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class HybridSearchEngine:
    def __init__(self, db_session):
        self.db = db_session
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self._build_index()
    
    def _build_index(self):
        """Build BM25 and vector indexes"""
        # Fetch all events
        events = self.db.query(DrillingEvent).all()
        
        # BM25 index (keyword search)
        self.event_ids = [e.event_id for e in events]
        self.event_texts = [
            f"{e.event_type} {e.formation_name} {e.description}"
            for e in events
        ]
        tokenized_corpus = [text.lower().split() for text in self.event_texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        # Vector index already in database (event_embeddings table)
        print(f"Index built: {len(events)} events")
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        bm25_weight: float = 0.3,
        vector_weight: float = 0.7
    ) -> List[Dict]:
        """Hybrid search combining BM25 and vector similarity"""
        
        # Step 1: BM25 keyword search
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_scores = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min() + 1e-10)
        
        # Step 2: Vector semantic search
        query_embedding = self.embedder.encode(query)
        
        # Query pgvector for top 50 candidates
        similar_embeddings = (
            self.db.query(EventEmbedding)
            .order_by(EventEmbedding.embedding.cosine_distance(query_embedding))
            .limit(50)
            .all()
        )
        
        event_id_to_vector_score = {
            emb.event_id: 1 - cosine_similarity([query_embedding], [emb.embedding])[0][0]
            for emb in similar_embeddings
        }
        
        # Step 3: Combine scores
        combined_scores = []
        for i, event_id in enumerate(self.event_ids):
            bm25_score = bm25_scores[i]
            vector_score = event_id_to_vector_score.get(event_id, 0)
            
            combined = bm25_weight * bm25_score + vector_weight * vector_score
            combined_scores.append((event_id, combined))
        
        # Sort and return top K
        combined_scores.sort(key=lambda x: x[1], reverse=True)
        top_results = combined_scores[:top_k]
        
        # Fetch full event details
        results = []
        for event_id, score in top_results:
            event = self.db.query(DrillingEvent).filter_by(event_id=event_id).first()
            results.append({
                "event_id": str(event.event_id),
                "well_name": event.well.well_name,
                "event_type": event.event_type,
                "depth_md_m": event.depth_start_md_m,
                "formation": event.formation_name,
                "description": event.description,
                "mitigation": event.mitigation,
                "npt_hours": event.npt_hours,
                "source_document": event.source_document,
                "relevance_score": round(score, 3)
            })
        
        return results
```

#### Deliverables
- [ ] Hybrid search implementation
- [ ] BM25 + vector fusion
- [ ] API endpoint `/api/search`
- [ ] Search quality evaluation (Precision@5)
- [ ] Example queries documented

---

### MODULE 7: Risk Prediction Engine
**Owner:** ML Engineer  
**Dependencies:** M4 (Relevance), M5 (Correlation), M6 (Search)  
**Duration:** 6 days

#### Purpose
Five specialized risk models for proactive hazard detection.

#### Implementation

**Risk 1: Lost Circulation Detector**
```python
# backend/intelligence/risk_models/lost_circulation.py
from typing import Dict
import numpy as np

class LostCirculationRisk:
    def __init__(self, db_session):
        self.db = db_session
        self.threshold_flow_delta = -10.0  # liters per minute
    
    def assess_risk(
        self,
        well_id: str,
        current_telemetry: Dict,
        historical_corridor: Dict
    ) -> Dict:
        """Assess lost circulation risk"""
        
        # Evidence Pillar 1: Historical Prior
        upcoming_losses = [
            e for e in historical_corridor["upcoming_events"]
            if e["event_type"] == "LOST_CIRCULATION"
        ]
        
        if upcoming_losses:
            closest_loss = min(upcoming_losses, key=lambda x: x["distance_m"])
            distance_to_loss = closest_loss["distance_m"]
            evidence_strength = "HIGH" if len(upcoming_losses) >= 2 else "MEDIUM"
        else:
            distance_to_loss = None
            evidence_strength = "NONE"
        
        # Evidence Pillar 2: Live Anomaly Detection
        flow_in = current_telemetry.get("flow_lpm", 0)
        flow_out = current_telemetry.get("flow_return_lpm", 0)
        flow_delta = flow_out - flow_in
        
        pit_volume_change = current_telemetry.get("pit_volume_change_m3", 0)
        
        if flow_delta < self.threshold_flow_delta or pit_volume_change < -0.5:
            anomaly_severity = "HIGH"
            anomaly_score = 0.8
        elif flow_delta < 0:
            anomaly_severity = "MEDIUM"
            anomaly_score = 0.5
        else:
            anomaly_severity = "NONE"
            anomaly_score = 0.1
        
        # Combined Risk Assessment
        if evidence_strength in ["HIGH", "MEDIUM"] and anomaly_severity in ["HIGH", "MEDIUM"]:
            risk_level = "HIGH"
        elif evidence_strength in ["HIGH", "MEDIUM"] or anomaly_severity == "HIGH":
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "risk_type": "LOST_CIRCULATION",
            "risk_level": risk_level,
            "confidence": {
                "evidence_strength": evidence_strength,
                "live_anomaly": anomaly_severity,
                "data_quality": self._calculate_data_quality(current_telemetry),
                "source_grounded": 100 if upcoming_losses else 0
            },
            "indicators": {
                "distance_to_historical_loss_m": distance_to_loss,
                "flow_delta_lpm": flow_delta,
                "pit_volume_change_m3": pit_volume_change,
                "num_historical_cases": len(upcoming_losses)
            },
            "recommendation": self._generate_recommendation(risk_level, closest_loss if upcoming_losses else None)
        }
    
    def _calculate_data_quality(self, telemetry: Dict) -> int:
        """Calculate % of required parameters available"""
        required_params = ["flow_lpm", "flow_return_lpm", "pit_volume_change_m3", "spp_bar"]
        available = sum(1 for p in required_params if telemetry.get(p) is not None)
        return int((available / len(required_params)) * 100)
    
    def _generate_recommendation(self, risk_level: str, closest_loss: Dict) -> str:
        if risk_level == "HIGH":
            return "PROACTIVE: Prepare 25-30 bbl LCM pill in reserve pit. Alert mud engineer. Reduce pump rate by 20%."
        elif risk_level == "MEDIUM":
            return "MONITOR: Have LCM materials staged at rig floor. Continue normal operations with increased surveillance."
        else:
            return "ROUTINE: No action required. Continue drilling."
```

**Risk 2: Stuck Pipe Detector**
```python
# backend/intelligence/risk_models/stuck_pipe.py
class StuckPipeRisk:
    def __init__(self, db_session):
        self.db = db_session
        self.overpull_threshold_kn = 50.0
    
    def assess_risk(
        self,
        well_id: str,
        current_telemetry: Dict,
        historical_corridor: Dict
    ) -> Dict:
        """Assess stuck pipe risk"""
        
        # Historical Prior
        upcoming_stucks = [
            e for e in historical_corridor["upcoming_events"]
            if e["event_type"] == "STUCK_PIPE"
        ]
        
        # Live Anomaly: Torque + Hookload patterns
        torque = current_telemetry.get("torque_knm", 0)
        hookload = current_telemetry.get("hookload_kn", 0)
        
        # Calculate Mechanical Specific Energy (MSE)
        wob = current_telemetry.get("wob_kn", 0)
        rpm = current_telemetry.get("rpm", 0)
        rop = current_telemetry.get("rop_mhr", 0.001)  # Avoid division by zero
        bit_diameter_m = 0.2159  # 8.5 inch bit
        
        mse = (wob / (bit_diameter_m**2 * np.pi / 4)) + (2 * np.pi * rpm * torque / (bit_diameter_m * rop))
        
        # Industry benchmark: MSE > 500 MPa indicates dysfunction
        if mse > 500:
            anomaly_severity = "HIGH"
        elif mse > 300:
            anomaly_severity = "MEDIUM"
        else:
            anomaly_severity = "LOW"
        
        # Combine signals
        if upcoming_stucks and anomaly_severity == "HIGH":
            risk_level = "HIGH"
        elif upcoming_stucks or anomaly_severity == "HIGH":
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "risk_type": "STUCK_PIPE",
            "risk_level": risk_level,
            "indicators": {
                "mse_mpa": round(mse, 1),
                "torque_knm": torque,
                "hookload_kn": hookload,
                "num_historical_cases": len(upcoming_stucks)
            }
        }
```

**Unified Risk Engine**
```python
# backend/intelligence/risk_engine.py
class RiskEngine:
    def __init__(self, db_session):
        self.db = db_session
        self.models = {
            "LOST_CIRCULATION": LostCirculationRisk(db_session),
            "STUCK_PIPE": StuckPipeRisk(db_session),
            "KICK": KickRisk(db_session),
            "TORQUE_SPIKE": TorqueSpikeRisk(db_session),
            "CEMENTING": CementingRisk(db_session)
        }
    
    def assess_all_risks(
        self,
        well_id: str,
        current_depth_md: float,
        current_telemetry: Dict
    ) -> List[Dict]:
        """Run all 5 risk models"""
        
        # Get offset relevance
        relevance_engine = OffsetRelevanceEngine(self.db)
        relevant_offsets = relevance_engine.rank_offsets(well_id, current_depth_md)
        top_3_offset_ids = [r.well_id for r in relevant_offsets[:3]]
        
        # Get historical corridor
        correlation_engine = DepthCorrelationEngine(self.db)
        corridor = correlation_engine.get_historical_corridor(
            well_id, current_depth_md, top_3_offset_ids, lookahead_m=50.0
        )
        
        # Run all risk models
        risks = []
        for model_name, model in self.models.items():
            risk_assessment = model.assess_risk(well_id, current_telemetry, corridor)
            risks.append(risk_assessment)
        
        return risks
```

#### Deliverables
- [ ] 5 risk model implementations
- [ ] 4-Pillar confidence framework
- [ ] MSE and d-exponent calculators
- [ ] API endpoint `/api/risk/assess`
- [ ] Model evaluation metrics

---

### MODULE 8: Alert Generation System
**Owner:** Backend Lead  
**Dependencies:** M7 (Risk Engine)  
**Duration:** 3 days

#### Implementation
```python
# backend/intelligence/alert_generator.py
from enum import Enum
from datetime import datetime

class AlertState(Enum):
    GREEN = "SAFE"
    AMBER = "PROACTIVE_WARNING"
    RED = "IMMEDIATE"

class AlertGenerator:
    def __init__(self, db_session):
        self.db = db_session
    
    def generate_alert(
        self,
        risk_assessment: Dict,
        distance_to_hazard_m: float
    ) -> Dict:
        """Generate proactive alert"""
        
        # Determine alert state based on distance and risk level
        risk_level = risk_assessment["risk_level"]
        
        if distance_to_hazard_m is None:
            state = AlertState.GREEN
        elif distance_to_hazard_m < 15 or risk_level == "HIGH":
            state = AlertState.RED
        elif distance_to_hazard_m < 50 and risk_level in ["MEDIUM", "HIGH"]:
            state = AlertState.AMBER
        else:
            state = AlertState.GREEN
        
        if state == AlertState.GREEN:
            return None  # No alert needed
        
        # Calculate lead time (assuming 20 m/hr ROP)
        lead_time_minutes = int((distance_to_hazard_m / 20) * 60) if distance_to_hazard_m else 0
        
        alert = {
            "alert_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "state": state.value,
            "risk_type": risk_assessment["risk_type"],
            "risk_level": risk_level,
            "distance_to_hazard_m": distance_to_hazard_m,
            "lead_time_minutes": lead_time_minutes,
            "message": self._format_message(state, risk_assessment, distance_to_hazard_m),
            "recommendation": risk_assessment.get("recommendation", ""),
            "evidence": risk_assessment.get("indicators", {}),
            "confidence": risk_assessment.get("confidence", {})
        }
        
        return alert
    
    def _format_message(self, state: AlertState, risk: Dict, distance: float) -> str:
        risk_type = risk["risk_type"].replace("_", " ").title()
        
        if state == AlertState.AMBER:
            return f"⚠️ PROACTIVE WARNING: {distance:.0f}m ahead to historical {risk_type} zone"
        elif state == AlertState.RED:
            return f"🔴 IMMEDIATE ALERT: Entering {risk_type} zone NOW"
        else:
            return f"✓ All Clear - Next hazard: {distance:.0f}m"
```

#### Deliverables
- [ ] Alert state machine (Green/Amber/Red)
- [ ] Lead time calculation
- [ ] WebSocket push notification
- [ ] Alert persistence (audit log)
- [ ] API endpoint `/api/alerts/current`

---

### MODULE 9: Backend API Layer
**Owner:** Backend Lead  
**Dependencies:** M4-M8 (All intelligence modules)  
**Duration:** 4 days

#### API Specification

```python
# backend/api/main.py
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="NWIS Backend API",
    version="1.0.0",
    docs_url="/api/docs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= WELL MANAGEMENT =============
@app.get("/api/wells")
async def list_wells(field: str = None, status: str = None):
    """List all wells with optional filters"""
    pass

@app.get("/api/wells/{well_id}")
async def get_well_details(well_id: str):
    """Get detailed well information"""
    pass

# ============= OFFSET RELEVANCE =============
@app.get("/api/offsets/relevant")
async def get_relevant_offsets(
    active_well_id: str,
    current_depth_md: float,
    radius_km: float = 50.0
):
    """Get dynamically ranked offset wells"""
    pass

# ============= DEPTH CORRELATION =============
@app.post("/api/depth/correlate")
async def correlate_depths(request: DepthCorrelationRequest):
    """Align wells by geological horizon"""
    pass

@app.get("/api/depth/corridor")
async def get_historical_corridor(
    well_id: str,
    current_depth_md: float,
    lookahead_m: float = 50.0
):
    """Get upcoming historical events"""
    pass

# ============= SEARCH =============
@app.get("/api/search")
async def search_events(query: str, top_k: int = 10):
    """Natural language search over drilling events"""
    pass

# ============= RISK ASSESSMENT =============
@app.post("/api/risk/assess")
async def assess_risks(request: RiskAssessmentRequest):
    """Run all 5 risk models"""
    pass

# ============= ALERTS =============
@app.get("/api/alerts/current")
async def get_current_alerts(well_id: str):
    """Get active alerts for a well"""
    pass

@app.websocket("/ws/alerts/{well_id}")
async def websocket_alerts(websocket: WebSocket, well_id: str):
    """Real-time alert stream"""
    await websocket.accept()
    
    while True:
        # Push alerts in real-time
        alert = await get_latest_alert(well_id)
        await websocket.send_json(alert)
        await asyncio.sleep(5)  # 5-second polling

# ============= DOCUMENT INGESTION =============
@app.post("/api/ingest/pdf")
async def upload_pdf(file: UploadFile, well_id: str):
    """Upload and process a drilling report"""
    # Trigger Celery background task
    task = process_pdf_async.delay(file.filename, well_id)
    return {"task_id": task.id}

@app.get("/api/ingest/status/{task_id}")
async def get_ingestion_status(task_id: str):
    """Check PDF processing status"""
    pass
```

#### Deliverables
- [ ] Complete FastAPI application
- [ ] Auto-generated Swagger docs
- [ ] WebSocket implementation
- [ ] Request/response validation (Pydantic)
- [ ] Error handling middleware

---

### MODULE 10: Frontend Command Cockpit
**Owner:** Frontend Lead  
**Dependencies:** M9 (Backend API)  
**Duration:** 6 days

#### Component Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── map/
│   │   │   ├── WellMap.tsx          # Leaflet interactive map
│   │   │   ├── WellMarker.tsx       # Custom well markers
│   │   │   └── RadiusSlider.tsx     # Radius filter control
│   │   ├── depth/
│   │   │   ├── DepthTrack.tsx       # Dual stratigraphic column
│   │   │   ├── FormationBand.tsx    # Formation visualization
│   │   │   └── EventMarker.tsx      # Historical event markers
│   │   ├── risk/
│   │   │   ├── RiskGauge.tsx        # Circular risk gauge
│   │   │   ├── RiskPanel.tsx        # 5-risk dashboard
│   │   │   └── ConfidenceBreakdown.tsx
│   │   ├── alerts/
│   │   │   ├── AlertBanner.tsx      # Top banner (Green/Amber/Red)
│   │   │   ├── AlertHistory.tsx     # Alert log
│   │   │   └── EvidenceModal.tsx    # PDF source viewer
│   │   ├── search/
│   │   │   ├── SearchBar.tsx        # Natural language search
│   │   │   └── ResultCard.tsx       # Search result display
│   │   └── layout/
│   │       ├── CommandCockpit.tsx   # Main dashboard layout
│   │       └── Sidebar.tsx          # Well selector
│   ├── hooks/
│   │   ├── useWebSocket.ts          # Real-time alert subscription
│   │   ├── useOffsetWells.ts        # Offset relevance query
│   │   └── useRiskAssessment.ts     # Risk polling
│   ├── services/
│   │   └── api.ts                   # API client (Axios)
│   ├── store/
│   │   └── wellStore.ts             # Zustand state management
│   └── App.tsx
```

#### Key Component Implementation

**AlertBanner.tsx**
```typescript
// frontend/src/components/alerts/AlertBanner.tsx
import { useEffect, useState } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { Bell, AlertTriangle, CheckCircle } from 'lucide-react';

export function AlertBanner({ wellId }: { wellId: string }) {
  const [alert, setAlert] = useState(null);
  
  const { lastMessage } = useWebSocket(`/ws/alerts/${wellId}`);
  
  useEffect(() => {
    if (lastMessage) {
      setAlert(JSON.parse(lastMessage.data));
    }
  }, [lastMessage]);
  
  if (!alert || alert.state === 'SAFE') {
    return (
      <div className="bg-green-900/20 border border-green-700 rounded-lg p-4">
        <div className="flex items-center gap-3">
          <CheckCircle className="w-6 h-6 text-green-400" />
          <span className="text-green-200 font-medium">
            ✓ All Clear - No immediate hazards detected
          </span>
        </div>
      </div>
    );
  }
  
  const stateColors = {
    'PROACTIVE_WARNING': 'bg-amber-900/30 border-amber-600 text-amber-200',
    'IMMEDIATE': 'bg-red-900/30 border-red-600 text-red-200'
  };
  
  const stateIcons = {
    'PROACTIVE_WARNING': AlertTriangle,
    'IMMEDIATE': Bell
  };
  
  const StateIcon = stateIcons[alert.state];
  
  return (
    <div className={`border rounded-lg p-4 ${stateColors[alert.state]}`}>
      <div className="flex items-start gap-4">
        <StateIcon className="w-8 h-8 mt-1 animate-pulse" />
        
        <div className="flex-1 space-y-2">
          <h3 className="text-lg font-semibold">{alert.message}</h3>
          
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="opacity-70">Distance:</span>
              <span className="font-medium ml-2">{alert.distance_to_hazard_m}m</span>
            </div>
            <div>
              <span className="opacity-70">Lead Time:</span>
              <span className="font-medium ml-2">{alert.lead_time_minutes} min</span>
            </div>
            <div>
              <span className="opacity-70">Risk Level:</span>
              <span className="font-medium ml-2">{alert.risk_level}</span>
            </div>
          </div>
          
          <div className="bg-black/20 rounded p-3 mt-3">
            <p className="text-sm font-medium">Recommended Action:</p>
            <p className="text-sm mt-1 opacity-90">{alert.recommendation}</p>
          </div>
          
          <button 
            onClick={() => {/* Open evidence modal */}}
            className="text-sm underline hover:opacity-80 mt-2"
          >
            View Supporting Evidence →
          </button>
        </div>
      </div>
    </div>
  );
}
```

**CommandCockpit.tsx (Main Layout)**
```typescript
// frontend/src/components/layout/CommandCockpit.tsx
import { useState } from 'react';
import { WellMap } from '../map/WellMap';
import { DepthTrack } from '../depth/DepthTrack';
import { RiskPanel } from '../risk/RiskPanel';
import { AlertBanner } from '../alerts/AlertBanner';
import { SearchBar } from '../search/SearchBar';

export function CommandCockpit() {
  const [activeWellId, setActiveWellId] = useState('well-001');
  
  return (
    <div className="h-screen bg-slate-950 text-slate-100">
      {/* Top Header */}
      <header className="h-16 bg-slate-900 border-b border-slate-800 px-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold">NWIS Command Cockpit</h1>
          <span className="text-sm text-slate-400">| Active Well: NHK-025</span>
        </div>
        <SearchBar />
      </header>
      
      {/* Alert Banner */}
      <div className="px-6 pt-4">
        <AlertBanner wellId={activeWellId} />
      </div>
      
      {/* Main Content */}
      <div className="h-[calc(100vh-140px)] grid grid-cols-12 gap-4 p-6">
        {/* Left: Map */}
        <div className="col-span-4 bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
          <WellMap activeWellId={activeWellId} />
        </div>
        
        {/* Middle: Depth Track */}
        <div className="col-span-5 bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
          <DepthTrack wellId={activeWellId} />
        </div>
        
        {/* Right: Risk Gauges */}
        <div className="col-span-3 bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
          <RiskPanel wellId={activeWellId} />
        </div>
      </div>
    </div>
  );
}
```

#### Deliverables
- [ ] Complete React application
- [ ] Responsive dark-mode UI
- [ ] Real-time WebSocket integration
- [ ] Interactive GIS map (Leaflet)
- [ ] Dual-track depth visualization
- [ ] 5-risk gauge dashboard
- [ ] Alert banner with states
- [ ] Search interface

---

## 6. Integration Strategy

### 6.1 Module Integration Order

**Phase 1: Data Foundation (Days 1-5)**
```
1. Setup PostgreSQL database
2. Run M1 (Database Schema)
3. Run M3 (Synthetic Data Generator) → Seed database
4. Verify: Can query wells, formations, events
```

**Phase 2: Intelligence Layer (Days 6-10)**
```
1. Implement M4 (Offset Relevance)
2. Implement M5 (Depth Correlation)
3. Implement M6 (Hybrid Search)
4. Test individually with Jupyter notebooks
5. Verify: Relevance scores make sense, depth alignment works
```

**Phase 3: Risk & Alerts (Days 11-16)**
```
1. Implement M7 (Risk Engine)
2. Implement M8 (Alert Generator)
3. Test with simulated telemetry
4. Verify: Alerts trigger at correct thresholds
```

**Phase 4: API & UI (Days 17-22)**
```
1. Implement M9 (Backend API)
2. Test APIs with Postman
3. Implement M10 (Frontend)
4. Connect frontend to backend
5. Verify: End-to-end data flow works
```

**Phase 5: Integration Testing (Days 23-25)**
```
1. Run full system with mock eRTMAC data
2. Test alert generation in real-time
3. Performance testing
4. Bug fixes
```

### 6.2 Inter-Module Communication

**API Contracts:**
All modules communicate via REST APIs and database queries. No direct function calls between modules.

**Example Flow (Alert Generation):**
```
1. Frontend polls /api/risk/assess every 5 seconds
2. Backend API calls RiskEngine.assess_all_risks()
3. RiskEngine internally calls:
   - OffsetRelevanceEngine.rank_offsets()
   - DepthCorrelationEngine.get_historical_corridor()
4. RiskEngine returns risk assessments
5. Backend calls AlertGenerator.generate_alert()
6. Alert pushed via WebSocket to frontend
7. Frontend displays alert in AlertBanner component
```

---

## 7. Testing & Validation

### 7.1 Unit Testing Strategy

**Backend Testing (pytest)**
```python
# tests/test_offset_relevance.py
def test_relevance_scoring():
    # Given: 2 wells, one close and similar, one far
    well_a = create_test_well("NHK-01", lat=27.37, lon=95.35, formation="Tipam")
    well_b = create_test_well("NHK-02", lat=27.40, lon=95.35, formation="Tipam")
    well_c = create_test_well("NHK-03", lat=28.00, lon=96.00, formation="Barail")
    
    # When: Ranking offsets for well_a
    engine = OffsetRelevanceEngine(db_session)
    scores = engine.rank_offsets(well_a.well_id, current_depth_md=3000.0)
    
    # Then: well_b should rank higher than well_c
    assert scores[0].well_id == well_b.well_id
    assert scores[0].overall_score > scores[1].overall_score
```

**Frontend Testing (Vitest + React Testing Library)**
```typescript
// tests/AlertBanner.test.tsx
describe('AlertBanner', () => {
  it('shows green state when no alerts', () => {
    const { getByText } = render(<AlertBanner wellId="test-123" />);
    expect(getByText(/All Clear/i)).toBeInTheDocument();
  });
  
  it('shows amber state with proactive warning', async () => {
    mockWebSocket.send({ state: 'PROACTIVE_WARNING', distance_to_hazard_m: 35 });
    
    await waitFor(() => {
      expect(screen.getByText(/35m ahead/i)).toBeInTheDocument();
    });
  });
});
```

### 7.2 Integration Testing

**Scenario: End-to-End Alert Flow**
```
1. Start: Well at 3,200m drilling in Tipam Sandstone
2. Action: Advance depth to 3,220m (20m progress)
3. Expected: System detects historical loss at 3,242m in offset well
4. Expected: Alert banner turns AMBER (22m ahead)
5. Expected: Recommendation displays "Prepare LCM pill"
6. Action: Advance depth to 3,240m
7. Expected: Alert banner turns RED (2m ahead)
```

### 7.3 Performance Benchmarks

| Metric | Target | Test Method |
|--------|--------|-------------|
| API latency (GET /api/offsets/relevant) | <500ms | Apache Bench (ab) |
| Search query response | <2s | Manual + logging |
| Alert generation | <3s | WebSocket latency measurement |
| Map pan/zoom responsiveness | <200ms | Chrome DevTools |
| Database query time (complex join) | <1s | EXPLAIN ANALYZE |

---

## 8. Deployment Architecture

### 8.1 Docker Compose Stack

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgis/postgis:15-3.3
    environment:
      POSTGRES_DB: nwis
      POSTGRES_USER: nwis_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  backend:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://nwis_user:${DB_PASSWORD}@postgres:5432/nwis
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app
      - ./data/pdfs:/data/pdfs
  
  celery_worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info
    environment:
      DATABASE_URL: postgresql://nwis_user:${DB_PASSWORD}@postgres:5432/nwis
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data/pdfs:/data/pdfs
  
  frontend:
    build: ./frontend
    command: npm run dev
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend

volumes:
  postgres_data:
```

### 8.2 Production Deployment (On-Premise at OIL)

**Server Requirements:**
- **HQ Server (Duliajan):**
  - 32 GB RAM
  - 8 CPU cores
  - 500 GB SSD
  - RAID for database
  
- **Rig-Site Edge Device:**
  - Ruggedized industrial PC
  - 16 GB RAM
  - 4 CPU cores
  - 256 GB SSD
  - Offline cache

**Network Architecture:**
```
┌───────────────────────────────────────────────────────────────┐
│ HQ DATACENTER (DULIAJAN)                                      │
│                                                               │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐  │
│  │ PostgreSQL   │     │ Backend API  │     │ Redis Cache  │  │
│  │ (Master DB)  │────▶│ (FastAPI)    │────▶│              │  │
│  └──────────────┘     └──────────────┘     └──────────────┘  │
│         │                     │                               │
│         │                     │                               │
│         │                     ↓                               │
│         │             ┌──────────────┐                        │
│         │             │ Nginx        │                        │
│         │             │ Reverse Proxy│                        │
│         │             └──────┬───────┘                        │
│         │                    │                                │
└─────────┼────────────────────┼────────────────────────────────┘
          │                    │
          │ VSAT / 4G          │ HTTPS
          │ Replication        │ WebSocket
          │                    │
┌─────────┼────────────────────┼────────────────────────────────┐
│ RIG SITE (NAHORKATIYA)       │                                │
│                              │                                │
│  ┌──────────────┐     ┌──────▼───────┐     ┌──────────────┐  │
│  │ PostgreSQL   │     │ Frontend     │     │ Redis Cache  │  │
│  │ (Read Replica)│────▶│ (React SPA)  │────▶│ (Local)      │  │
│  └──────────────┘     └──────────────┘     └──────────────┘  │
│         ↑                                                     │
│         │ Sync when online                                   │
└─────────┼─────────────────────────────────────────────────────┘
          │
      eRTMAC
  (Telemetry Stream)
```

---

## 9. Team Roles & Responsibilities

| Team Member | Primary Role | Modules Owned | Skills Required |
|-------------|-------------|---------------|-----------------|
| **Member 1** | Backend Lead | M1, M6, M8, M9 | FastAPI, PostgreSQL, WebSocket |
| **Member 2** | ML Engineer | M2, M4, M7 | NLP, scikit-learn, XGBoost |
| **Member 3** | Domain Expert | M3, M5 | Petroleum engineering, WITSML |
| **Member 4** | Frontend Lead | M10 | React, TypeScript, Leaflet |
| **Member 5** | DevOps/Integration | M11, Docker | Docker, CI/CD, testing |

**Note:** Roles are flexible. Team members can collaborate on overlapping modules.

---

## 10. Risk Mitigation

### 10.1 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| OCR accuracy too low | High | Implement manual correction UI + confidence scoring |
| Real-time latency issues | Medium | Add Redis caching layer + optimize database queries |
| False alarm rate too high | High | Implement multi-pillar evidence framework + tunable thresholds |
| Frontend performance on video wall | Medium | Optimize React rendering + WebGL for visualizations |

### 10.2 Schedule Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Module dependencies block progress | High | Prioritize M1, M3 completion; enable parallel work |
| Integration bugs in final week | High | Daily integration testing from Day 10 onwards |
| Team member unavailability | Medium | Cross-train on critical modules |

---

## 11. Success Criteria

### 11.1 MVP Demo Readiness

**Must-Have Features (Non-Negotiable):**
- [ ] Interactive GIS map showing 20 synthetic wells
- [ ] Offset relevance ranking working (top 3 wells highlighted)
- [ ] Depth correlation visualization (dual track)
- [ ] At least 2 risk models functional (Lost Circ + Stuck Pipe)
- [ ] Alert banner showing Amber warning 30m before hazard
- [ ] Evidence viewer showing source PDF page
- [ ] Natural language search returning 5 relevant results

**Nice-to-Have (If Time Permits):**
- [ ] All 5 risk models implemented
- [ ] Real-time simulation mode (drill bit advancing)
- [ ] Historical risk corridor animation
- [ ] Export report feature

### 11.2 Presentation Criteria

**Technical Demonstration:**
1. Show live alert generation as depth advances
2. Demonstrate search: "Lost circulation in Tipam Sandstone"
3. Prove evidence traceability (click alert → see PDF page)
4. Explain 4-pillar confidence framework

**Innovation Highlights:**
- Dynamic offset relevance (not static map)
- Interval-aware geological alignment
- Proactive lead-time warnings (30-60 min)
- 100% air-gapped deployment (national security compliant)

---

## 12. Next Steps (Immediate Actions)

1. **Day 1 (Today):**
   - [ ] Team kickoff meeting
   - [ ] Assign modules to team members
   - [ ] Setup Git repository structure
   - [ ] Initialize Docker development environment

2. **Day 2:**
   - [ ] Complete M1 (Database Schema)
   - [ ] Start M3 (Data Generator)
   - [ ] Frontend team: React project setup

3. **Day 3:**
   - [ ] Seed database with 20 synthetic wells
   - [ ] Backend team: Basic CRUD APIs
   - [ ] ML team: Test OCR on sample PDFs

4. **Daily Standup:**
   - 9:00 AM: Sync progress, blockers
   - 6:00 PM: Demo working features

---

## 13. Document Maintenance

**This implementation plan is a living document.**

### Change Log Format:
```
[Date] - [Team Member] - [Module] - [Change Description]
Example:
[2026-09-28] - Member 2 - M7 - Changed risk threshold from 80% to 85%
```

### Approval Process:
- Minor changes (<5% impact): Team member discretion
- Major changes (new module, architecture): Team consensus required

### Version History:
- v1.0 (2026-09-27): Initial plan
- v1.1: [Pending - after Sprint 1 retrospective]

---

**END OF IMPLEMENTATION PLAN**

---

**Document Prepared By:** SIH 2026 Team  
**Last Updated:** September 27, 2026  
**Status:** Ready for Development  
**Next Review:** After Sprint 1 (Day 5)
