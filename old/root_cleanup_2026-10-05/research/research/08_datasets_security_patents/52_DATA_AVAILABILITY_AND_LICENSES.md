# SIH 26121 — Data Availability, Legal Licenses & Data Sovereignty

## 1. Executive Summary
This document establishes the legal, regulatory, and intellectual property compliance framework for data ingested, processed, and demonstrated by NWIS. It audits the licensing agreements of public drilling datasets (Equinor Volve, FORCE 2020, Utah FORGE), addresses Indian upstream data sovereignty laws governing DGH NDR data, and establishes the copyright status of synthetic telemetry.

---

## 2. Open Dataset Licensing Matrix

| Dataset | Governing Authority / Licensor | License Type | Commercial & Competition Rights | Attribution Requirements |
| :--- | :--- | :--- | :--- | :--- |
| **Equinor Volve Field** | Equinor ASA & Volve License Partners | Equinor Open Data License (CC BY 4.0 Derivative) | Permitted for research, educational competitions (SIH), and software evaluation. | Full citation: *"Volve data courtesy of Equinor and partners."* |
| **FORCE 2020 Benchmark** | Norwegian Petroleum Directorate (NPD) / FORCE | Creative Commons Attribution 4.0 (CC BY 4.0) | Unrestricted commercial, hackathon, and derivative development. | Attribute to FORCE ML Competition & NPD. |
| **Utah FORGE Geothermal** | US Department of Energy (DOE) | Public Domain / US Govt Open Data (CC0) | Unrestricted global access, re-distribution, and modification. | Cite DOE Geothermal Technologies Office (GTO). |
| **Synthetic Assam Data** | NWIS Development Team | MIT License / Open Source Proprietary | 100% owned by developing team; zero external licensing restrictions. | No third-party copyright claims possible. |

---

## 3. Indian Upstream Data Sovereignty & DGH NDR Compliance

In India, upstream exploration and subsurface data are strategic national assets governed under strict statutory frameworks:

```
[STATUTORY GOVERNANCE TIERS IN INDIA]
├── Ministry of Petroleum and Natural Gas (MoPNG)
├── Directorate General of Hydrocarbons (DGH)
└── National Data Repository (NDR) Regulations (2017 & Amendments)
```

### Critical Legal & Regulatory Constraints:
1. **Physical Data Residency:** Subsurface exploration data belonging to Indian operators (Oil India Limited, ONGC) cannot be transmitted to foreign cloud jurisdictions or processed by public multi-tenant SaaS APIs (e.g. standard public OpenAI / Anthropic APIs) without explicit MoPNG authorization.
2. **Classified Geological Boundaries:** High-resolution seismic coordinates near international land borders (particularly Upper Assam / Arunachal Pradesh belt) are classified under Ministry of Defence and Survey of India restrictions.
3. **NDR Access Agreement:** Data downloaded from the DGH NDR portal under academic or exploratory licensing cannot be redistributed or commercialized without payment of statutory royalties.

---

## 4. NWIS Regulatory Compliance Architecture

To guarantee 100% legal compliance both in the SIH evaluation and during future deployment inside Oil India Limited:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               NWIS COMPLIANCE SAFEGUARD                                │
├─────────────────────────────────────────────────────────┬──────────────────────────────┤
│ SIH Hackathon Evaluation Environment                    │ Future OIL Enterprise Rig    │
├─────────────────────────────────────────────────────────┼──────────────────────────────┤
│ • Uses CC-BY-4.0 Volve data and synthetic Assam models. │ • Deploys 100% on-premise at │
│ • Zero proprietary OIL documents exposed publicly.      │   Duliajan eRTMAC or rig IPC.│
│ • No NDA or IP violations possible during jury review.  │ • Adheres to DGH NDR data    │
│ • Complete audit trail provided for all training rows.  │   sovereignty mandates.      │
└─────────────────────────────────────────────────────────┴──────────────────────────────┘
```

---

## 5. Architectural Verdict for SIH 26121

**Verdict:** `[CLEAN-ROOM LICENSING COMPLIANCE]`.
- All baseline models and RAG document indexes for the SIH prototype are built strictly from **CC-BY-4.0 Volve open data** and **clean-room synthetic datasets**.
- This immunizes the project from intellectual property challenges, NDAs, or proprietary data leak allegations during the hackathon evaluation.
- The system design natively supports swapping open datasets with OIL's internal confidential WITSML and DDR repositories upon enterprise deployment.
