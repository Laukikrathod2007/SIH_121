# SIH 26121 — Indian Government Data Ecosystem: DGH NDR & Regulatory Standards

## 1. Executive Summary
This document investigates the centralized data infrastructure and regulatory reporting frameworks established by the Government of India, focusing on the Directorate General of Hydrocarbons (DGH), the **National Data Repository (NDR)**, Open Acreage Licensing Policy (OALP) data workflows, and national data sovereignty regulations governing subsurface and drilling records.

---

## 2. The National Data Repository (NDR)
- **Governing Body:** Directorate General of Hydrocarbons (DGH), Ministry of Petroleum and Natural Gas (MoPNG).
- **Physical Facility:** DGH Headquarters, OIDB Bhawan, Sector 73, Noida, Uttar Pradesh.
- **Core Mission:** A state-of-the-art government facility established to house, preserve, and curate all upstream E&P data generated across the sedimentary basins of India.
- **Data Holdings in NDR:**
  1. *Seismic Data:* Hundreds of thousands of line-kilometers of 2D and 3D pre-stack and post-stack seismic data.
  2. *Well Data:* Complete digital records for over **18,000+ wells** drilled in India, including wireline/LWD logs (LAS, DLIS), well completion reports (WCRs), core analysis, and geological formation tops.
  3. *Production & Reservoir Data:* Monthly production records, reservoir pressure histories, and fluid PVT reports.
  4. *GIS Subsurface Layers:* Spatial maps of block boundaries, wellheads, pipelines, and basin outlines.

`[VERIFIED: DGH NDR Portal: https://ndr.dghindia.gov.in]`

---

## 3. Statutory Data Submission Mandates

Under the Petroleum and Natural Gas (Safety in Mines) Rules and contractual PSC/RSC terms, all upstream operators (including OIL and ONGC) are legally required to submit standardized well data to DGH:

```
[OPERATOR RIG EXECUTION]
       │
       ├── Daily Drilling Telemetry Summary
       ├── Final Well Completion Report (WCR) (Within 30–60 days of rig release)
       ├── Digital Well Logs (LAS / DLIS format)
       └── Directional Wellbore Trajectory (M-I-A Survey Tables)
       │
       ▼ (Secure Digital Submission Portal)
[DGH NATIONAL DATA REPOSITORY (NDR)]
Curated, quality-checked, and integrated into Master Geodetic Database
```

### Strategic Implications for NWIS:
- Because OIL must format WCRs and directional surveys according to DGH regulatory standards, **historical well documentation possesses structured underlying templates**, even when stored as PDFs.
- An AI extraction engine calibrated to DGH-standard WCR structures will generalize across all OIL assets with high extraction accuracy.

---

## 4. OSDU Forum Alignment in India
- **Open Group OSDU Forum:** Global consortium creating an open-source, vendor-neutral subsurface and well data platform standard.
- **Indian Adoption:** Both ONGC and DGH have initiated exploratory and pilot programs to evaluate OSDU-compliant cloud repositories for national data storage.
- **NWIS Alignment:** Designing the internal data schemas of NWIS to map directly to OSDU Well, Wellbore, and WellLog data models ensures future-proof integration into India's emerging national digital data architecture.

---

## 5. Data Sovereignty & National Security Governance

Upstream oil and gas data in India is subject to stringent sovereign security classifications:

1. **Strategic National Asset Classification:** Subsurface geographical and energy reserve data is classified as sensitive strategic data under the Ministry of Defence and MoPNG guidelines.
2. **Geographical Border Sensitivity:** Oil India's primary operational area (Upper Assam and Arunachal Pradesh) is located in proximity to international borders. Exact wellbore coordinates, seismic grids, and critical energy infrastructure cannot be transmitted to public, non-sovereign third-party cloud servers outside India.
3. **Data Residency Mandate:** All production data, operational telemetry, and historical archives must reside within data centers located physically within the territory of India (MeitY-empaneled cloud providers or on-premise private clouds at Duliajan/Noida).
4. **Implication for AI/LLM Architecture:** **NWIS cannot rely on commercial public AI APIs that store, cache, or train on proprietary operational data outside Indian borders.** The production vision of NWIS must utilize locally hosted, open-weights models (e.g. LLaMA-3, Mistral, Qwen) or dedicated MeitY-certified private enterprise endpoints.
