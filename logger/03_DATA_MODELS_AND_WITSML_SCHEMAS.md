# SIH 26121 — eRTMAC-NWIS: Data Models & WITSML Schemas

This document defines the data structures and schema mapping used in NWIS, fully compatible with Energistics WITSML (Wellsite Information Transfer Standard Markup Language) and OSDU standards.

---

## 1. Entity Relationship Overview

```text
  +------------------+         1:N         +----------------------+
  |      wells       | ------------------< |     trajectories     |
  | (Surface info,   |                     | (MD, TVD, Incl, Az)  |
  |  KB, Field, Loc) |                     +----------------------+
  +--------+---------+
           |
           | 1:N                           +----------------------+
           +-----------------------------< |    formation_tops    |
           |                               | (Fm name, Top, Base) |
           |                               +----------------------+
           |
           | 1:N                           +----------------------+
           +-----------------------------< |   drilling_events    |
           |                               | (Hazard, Depth, LCM) |
           |                               +----------------------+
           |
           | 1:N                           +----------------------+
           +-----------------------------< |   telemetry_records  |
           |                               | (ROP, WOB, Flow, SPP)|
           |                               +----------------------+
           |
           | 1:N                           +----------------------+
           +-----------------------------< |   source_documents   |
                                           | (PDF, Page, Chunks)  |
                                           +----------------------+
```

---

## 2. Core JSON Data Schemas

### 2.1 Well Entity (`wells.json`)
```json
{
  "well_id": "OIL-EXP-07",
  "name": "Nahorkatiya Well #07",
  "operator": "Oil India Limited",
  "field": "Nahorkatiya",
  "block": "Assam-Arakan Basin Block A",
  "latitude": 27.2845,
  "longitude": 95.3412,
  "elevation_kb_m": 128.5,
  "total_depth_md_m": 3850.0,
  "total_depth_tvd_m": 3620.0,
  "profile_type": "Directional-J",
  "status": "HISTORICAL_OFFSET"
}
```

### 2.2 Formation Tops (`formation_tops.json`)
```json
{
  "well_id": "OIL-EXP-07",
  "formation_name": "Tipam Sandstone",
  "formation_code": "TIPAM_SAND",
  "lithology": "Coarse Sandstone interbedded with Grey Shale",
  "top_md_m": 2980.0,
  "top_tvd_m": 2890.0,
  "base_md_m": 3450.0,
  "base_tvd_m": 3310.0,
  "pore_pressure_gradient_ppg": 10.2,
  "fracture_gradient_ppg": 14.8
}
```

### 2.3 Normalized Drilling Event (`drilling_events.json`)
```json
{
  "event_id": "EVT-OIL-W03-089",
  "well_id": "OIL-EXP-03",
  "event_type": "MUD_LOSS",
  "hazard_category": "Lost Circulation",
  "depth_start_md_m": 3238.0,
  "depth_end_md_m": 3260.0,
  "formation": "Tipam Sandstone",
  "severity": "CRITICAL",
  "loss_rate_bbl_hr": 45.0,
  "observed_signals": "Sudden pit volume decrease (-18 bbl), SPP dropped by 220 psi",
  "root_cause": "Sub-hydrostatic permeable fault zone encountered with 11.4 ppg mud",
  "npt_hours": 14.5,
  "historical_mitigation": "Pumped 30 bbl high-viscosity LCM pill (nut plug + mica blend), reduced pump rate from 2100 lpm to 1550 lpm, conditioned mud to 10.8 ppg.",
  "outcome": "Circulation restored successfully. Casing lowered and cemented without further losses.",
  "source_document": "DDR_OIL_W03_2023.pdf",
  "source_page": 42,
  "document_paragraph": 3,
  "extraction_confidence": 0.96
}
```

### 2.4 Real-Time Telemetry Data Frame (`telemetry_stream.json`)
```json
{
  "timestamp": "2026-09-25T11:00:00Z",
  "well_id": "OIL-ACTIVE-X01",
  "measured_depth_m": 3220.0,
  "true_vertical_depth_m": 3110.5,
  "bit_formation": "Tipam Sandstone",
  "rop_m_hr": 14.2,
  "wob_klbs": 24.5,
  "rpm": 120,
  "torque_kn_m": 28.5,
  "standpipe_pressure_psi": 2850,
  "flow_in_lpm": 1850,
  "flow_out_lpm": 1520,
  "pit_volume_bbl": 412.0,
  "mud_weight_in_ppg": 11.2,
  "mud_weight_out_ppg": 11.1,
  "gas_units": 45
}
```

---

## 3. WITSML Standard Mapping

| NWIS Data Field | WITSML Standard Object | WITSML XML Element |
|---|---|---|
| Well Metadata | `well` | `well.nameLegal`, `well.field`, `well.wellLocation` |
| Trajectory Points | `trajectory` | `trajectory.trajectoryStation.md`, `tvd`, `incl`, `azi` |
| Formations | `stratigraphicColumn` | `formationMarker.name`, `mdTop`, `tvdTop` |
| Real-time Telemetry | `log` / `mudLog` | `log.logCurveInfo.curve[mnem='ROP']`, `torque`, `flowIn` |
| Drilling Operations | `opsReport` (DDR) | `opsReport.activity.md`, `opsReport.activity.comments` |
