# PS 121 — Curated Competitor Repositories & Domain Benchmarks

This document indexes all **12 high-value competitor and domain benchmark codebases** downloaded, verified on disk, and retained in `research/competitors/` for **PS 121 (SIH 26121 — eRTMAC-NWIS)**.

---

## 1. Active Direct Competitors (SIH 26121 / eRTMAC-NWIS)

| Repository Name | Clone Location | Source URL | Latest Commit | Primary Tech Stack | Key Architectural Focus |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **invo-coder19-Drill-IQ** | `research/competitors/direct/invo-coder19-Drill-IQ` | `https://github.com/invo-coder19/Drill-IQ.git` | 2026-09-27 | React 19, Vite, TypeScript, TanStack Router | Modern frontend UI with interactive well map and offset relevance scoring. |
| **pallavi-eRTMAC-NWIS** | `research/competitors/direct/pallavi-eRTMAC-NWIS` | `https://github.com/pallavi-a11y/eRTMAC-NWIS.git` | 2026-09-27 | FastAPI, Qdrant, pypdfium2, Qwen2.5-VL, OpenCV | Two-pass Vision-Language Model extraction, OpenCV table detection, and strict RAG score floor. |
| **dhanwanth-eRTMAC-NWIS** | `research/competitors/direct/dhanwanth-eRTMAC-NWIS` | `https://github.com/dhanwanth-dh/eRTMAC--NWIS-Nearby-Wells-Intelligence-Offset-Decision-Support.git` | 2026-09-26 | FastAPI, Scikit-learn, XGBoost, Joblib, React 19 | 5-Model XGBoost hazard suite (`xgb_mud_loss`, `xgb_stuck_pipe`, etc.), Isolation Forest, and 4-step actionable recommendations. |
| **PetrolQ** | `research/competitors/direct/PetrolQ` | `https://github.com/thor11223344/PetrolQ.git` | 2026-09-24 | FastAPI, PostgreSQL, PostGIS, pgvector, MapLibre GL | PostGIS spatial queries (`ST_DWithin`), offline MapLibre raster tiles, Saaty AHP weighted RAG, and Eaton PPFG. |
| **vidhiii1711-eRTMAC-NWIS** | `research/competitors/direct/vidhiii1711-eRTMAC-NWIS` | `https://github.com/vidhiii1711/eRTMAC-NWIS.git` | 2026-09-23 | Node.js, Express, React, Tailwind CSS, MongoDB | Live Vercel deployment (Team DrillX), 20+ parameter telemetry time-series, and decision audit logging. |
| **tech-nitin-wellwise** | `research/competitors/direct/tech-nitin-wellwise` | `https://github.com/tech-nitin/wellwise.git` | 2026-09-22 | JavaScript, Three.js, GSAP, CSS2DRenderer | Three.js 3D subsurface geological layer rendering with OrbitControls and depth-anchored callout annotations. |
| **SIH_2026_PLANNS** | `research/competitors/direct/SIH_2026_PLANNS` | `https://github.com/n3ssdub3y/SIH_2026_PLANNS.git` | 2026-09-22 | FastAPI, Flask, ChromaDB, NetworkX, FastDTW | FastDTW telemetry anomaly detector, NetworkX knowledge graph, and hazard-specific feature weights. |
| **rudrachauhan12999-eRTMAC-NWIS**| `research/competitors/direct/rudrachauhan12999-eRTMAC-NWIS` | `https://github.com/rudrachauhan12999/eRTMAC-NWIS.git` | 2026-09-20 | FastAPI, Motor, MongoDB, React, Vite | Modular REST API with dedicated routers for `/alerts`, `/documents`, `/events`, `/formations`, `/risk`, `/telemetry`. |
| **Physics0070-nwis** | `research/competitors/direct/Physics0070-nwis` | `https://github.com/Physics0070/nwis.git` | 2026-09-08 | FastAPI, PostgreSQL, SQLAlchemy, Alembic, React | Production PostgreSQL schema with Alembic migrations, telemetry sample replay, and `EngineerAction` feedback model. |
| **suryanshkota07-AROH** | `research/competitors/direct/suryanshkota07-AROH` | `https://github.com/suryanshkota07-oss/AROH-drilling-intelligence.git` | 2026-08-29 | FastAPI, Python, NumPy, Pydantic | Deterministic 5-factor analog well matching (`WEIGHTS`) and forward depth risk projection (`risk_ahead.py`). |

---

## 2. Advanced Drilling Domain & Benchmark Repositories

| Repository Name | Clone Location | Source URL | Latest Commit | Tech Stack | Benchmark Relevance |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **DDR_UTAH_FORGE** | `research/competitors/drilling/DDR_UTAH_FORGE` | `https://github.com/djimrastephane/DDR_UTAH_FORGE.git` | 2026-03-12 | Python, PyMuPDF, OpenCV, NetworkX, ChromaDB | 108 code files; deep PDF layout parsing, OCR confidence scoring, morphological table fallback, and phase causality tracking. |
| **DrillMind** | `research/competitors/direct/DrillMind` | `https://github.com/ArokyaMatthew/DrillMind.git` | 2026-06-02 | FastAPI, rank-bm25, ChromaDB, PyTorch LSTM | Multi-agent specialist architecture (`DrillingAgent`, `HistoricalAgent`, `SafetyAgent`) and Reciprocal Rank Fusion (RRF $k=60$). |
| **volve-drilling** / **spwla_volve** | `research/competitors/drilling/volve-drilling` | `https://github.com/f0nzie/volve-drilling.git` | 2026-01-20 | Python, WITSML XML, LAS | Standard WITSML 1.3.1 trajectory surveys and 24-well LAS log curves for validation benchmarking. |

---

## 3. Preserved Research Integrity
All retained repositories are stored in `research/competitors/` and remain strictly read-only and unmodified to preserve provenance and reproduce analysis results.
