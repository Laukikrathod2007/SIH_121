# NWIS Module 02 — Backend Intelligence Core

> **PS Outcomes ii, iii, iv, v, vi:** Geospatial relevance, searchable knowledge base, geological correlation, predictive risk analytics, and real-time early warnings.

## Architecture

4-engine intelligence pipeline:

```
ACTIVE BIT POSITION (depth d_t)
         │
         ├─ ENGINE 1: DORS (5-Factor Offset Relevance Scoring)
         │   S_spatial + S_formation + S_depth + S_trajectory + S_hazard
         │   → Ranked list of top-N most relevant offset wells
         │
         ├─ ENGINE 2: Stratigraphic Depth Correlator
         │   d_strat = TVD(d) − Top_TVD(Formation_k)
         │   → Eliminates "Trajectory Trap" — MD≠TVD for directional wells
         │
         ├─ ENGINE 3: Historical Risk Corridor Engine
         │   R_H(t) = 0.45·P_history + 0.35·A_sensor + 0.20·M_ML
         │   → Clusters offset events into depth corridors
         │   → Issues 15–50m lookahead early warning
         │
         └─ ENGINE 4: 4-Pillar Confidence Evaluator
             Evidence Strength + Sensor Anomaly + Data Quality + Audit Status
             → Transparent, decoupled confidence (no black box!)
```

## Quick Start

```powershell
cd c:\Users\LAUKIK\Desktop\SIH121\modules\02_nwis_backend

# Install deps
pip install -r requirements.txt

# Step 1: Generate synthetic testbed data (Assam-Arakan Basin, 12 wells)
python run_server.py --gen

# Step 2: Validate all engines
python run_server.py --validate

# Step 3: Start server
python run_server.py
```

Server starts at: **http://localhost:8002**  
API Docs: **http://localhost:8002/docs**

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v2/wells` | List all wells |
| `GET` | `/api/v2/map/wells` | GIS map data (lat/lon + metadata) |
| `GET` | `/api/v2/analyze/{well_id}?depth=2800` | **Full intelligence analysis** |
| `GET` | `/api/v2/offset_rank/{well_id}?depth=2800` | DORS ranking only |
| `GET` | `/api/v2/corridors/{well_id}?depth=2800` | Risk corridors |
| `GET` | `/api/v2/formations/{well_id}` | Formation tops |
| `GET` | `/api/v2/events?hazard_type=MUD_LOSS&formation=Tipam` | Search events |
| `GET` | `/api/v2/telemetry/{well_id}?depth=2800` | Live telemetry |
| `GET` | `/api/v2/health` | Health check |

## Synthetic Testbed

| Parameter | Value |
|---|---|
| Wells | 12 (Nahorkatiya, Moran, Baghjan, Hugrijan fields) |
| Formation Tops | 97 (Assam-Arakan authentic stratigraphy) |
| Drilling Events | 39 (authentic incidents with IADC NPT codes) |
| Telemetry | 3,600 1-Hz records with anomaly injection |
| Well Types | Vertical (50%), J-Type (35%), S-Type (15%) |

## Authentic Assam-Arakan Stratigraphy

| Formation | Typical Depth | Hazard Profile |
|---|---|---|
| Alluvium | 100–200m | N/A |
| Tipam Sandstone | 400–1200m | **Lost Circulation** (vugular) |
| Girujan Clay | 1200–1600m | **Wellbore Instability**, Stuck Pipe |
| Barail Sandstone | 1600–2200m | **Kick** (gas bearing) |
| Barail Coal-Shale | 2200–2500m | **Stuck Pipe** (swelling clays) |
| Kopili | 2500–2900m | **Lost Circulation** (fractured) |
| Sylhet Limestone | 2900–3200m | **Kick + Mud Loss** (prolific) |

## Project Structure

```
02_nwis_backend/
├── run_server.py              ← START HERE
├── server.py                  ← FastAPI application
├── orchestrator.py            ← Master analysis coordinator
├── data_store.py              ← Singleton data loader
├── requirements.txt
├── engines/
│   ├── dors_engine.py         ← 5-factor DORS scoring
│   ├── stratigraphic_correlator.py  ← TVD / d_strat alignment
│   └── risk_corridor_engine.py      ← R_H(t) + 4-pillar confidence
├── models/
│   └── schemas.py             ← Pydantic data models
└── data/
    └── synthetic/
        ├── generate_testbed.py  ← Basin testbed generator
        ├── wells.json
        ├── trajectories.json
        ├── formation_tops.json
        ├── drilling_events.json
        └── telemetry_stream.json
```
