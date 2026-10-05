# SIH 26121 — Global Solutions Business Models, Pricing & PSU Procurement Barriers

## 1. Executive Summary
This document conducts a deep-dive commercial investigation into how global oilfield service companies (SLB, Halliburton, Baker Hughes, Corva, Cognite, NOV, Peloton) package, price, and sell their drilling analytics and offset intelligence software. It analyzes why these business models face insurmountable procurement and legal barriers within Indian Public Sector Undertakings (PSUs) like **Oil India Limited (OIL)**, and details the sovereign economic advantage of NWIS.

---

## 2. Business Model & Pricing Taxonomy of Existing Solutions

```
                               GLOBAL SOFTWARE COMMERCIAL MODELS
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ 1. HARDWARE-BUNDLED SAAS     │ 2. ENTERPRISE PER-SEAT / ARR │ 3. APP-STORE PER-RIG / MONTH │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ • SLB (DELFI / DrillPlan)    │ • Halliburton (Landmark)     │ • Corva (Corva Drilling)     │
│ • Baker Hughes (WellLink/DHP)│ • Cognite (Data Fusion)      │ • Nabors (RigCLOUD)          │
│ • Model: Cloud credits + MWD │ • Model: $500k–$2M ARR       │ • Model: $1,500–$3,500 / rig │
│   tool service bundling.     │   contracts + named seats.   │   per month subscription.    │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

---

## 3. Detailed Commercial Breakdown by Major Vendor

### 1. Schlumberger (SLB) — DELFI & Tela Offset Insights
* **Commercial Model:** Consumption-based cloud credits + Named User Subscription on the proprietary DELFI cloud.
* **Estimated Pricing:**
  * Base DELFI access: **$40,000 to $80,000 per named user / year**.
  * Compute & Storage: Billed per gigabyte and cloud core-hour.
  * Tela Insights / DrillPlan module add-on: Additional per-well surcharge ($5,000–$15,000 per well drilled).
* **Hardware Tie-in:** Strongly incentivized when bundled with SLB's proprietary downhole drilling services (PowerDrive RSS, PeriScope MWD/LWD).
* **Customer Target:** Supermajors (ExxonMobil, Chevron, Saudi Aramco, TotalEnergies).

### 2. Halliburton Landmark — DecisionSpace 365 & OpenWells
* **Commercial Model:** Traditional on-premise perpetual license + 20% annual maintenance (AMC), transitioning to DecisionSpace 365 cloud subscription.
* **Estimated Pricing:**
  * OpenWells core reporting: **$25,000 to $50,000 per concurrent seat**.
  * Digital Well Program (DWP) / Landmark Well Plan: **$60,000 to $120,000 per asset team license**.
* **OIL Relationship:** Oil India Limited currently licenses Landmark Well Plan for hydraulics/casing design, but has not adopted Landmark cloud due to on-premise policies.

### 3. Baker Hughes — JewelSuite & Drilling Hazard Prevention (DHP)
* **Commercial Model:** Packaged with Baker Hughes Real-Time Operating Center (RTOC) remote engineering advisory contracts.
* **Estimated Pricing:**
  * Bundled service rate: **$2,500 to $6,000 per rig day** (includes dedicated remote monitoring engineers in Mumbai/Kolkata + software access).
  * Standalone JewelSuite license: **$35,000 to $70,000 per seat / year**.

### 4. Corva — Corva Drilling (The Pure SaaS Model)
* **Commercial Model:** Pure cloud-native SaaS billed on a per-rig, per-month basis.
* **Estimated Pricing:**
  * Standard tier: **$1,500 to $3,500 per active rig / month**.
  * Fleet discount (10+ rigs): ~**$1,200 / rig / month**.
* **Strength:** Vendor-agnostic (ingests WITSML from any MLU).
* **Limitation for India:** Requires streaming unencrypted real-time data to AWS US-East / EU cloud regions.

### 5. Cognite — Cognite Data Fusion (CDF) & Know Your Well
* **Commercial Model:** Enterprise Data Integration Platform license (ARR) based on total ingested data volume and connected assets.
* **Estimated Pricing:**
  * Enterprise subscription: **$500,000 to $2,000,000+ per year**.
* **Deployment Example:** Deployed at Cairn Oil & Gas (Vedanta) under a multi-million dollar private contract; too broad and expensive for a targeted offset well PSU tender.

### 6. NOV — KAIZEN & NOVOS
* **Commercial Model:** Rig-level automation and advisory license billed per operating day or bundled into NOV top-drive/rig equipment leases.
* **Estimated Pricing:** **$500 to $1,500 per rig day**.

---

## 4. Why Global Business Models Fail in Indian PSUs (Oil India Limited)

```
[THE 5 BARRIERS TO WESTERN COMMERCIAL SOFTWARE AT OIL INDIA LIMITED]
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ BARRIER 1: Public Procurement & CVC L1 Tender Rules                                    │
│ • Central Vigilance Commission (CVC) guidelines mandate transparent, competitive       │
│   tendering. Proprietary single-vendor SaaS cannot be sole-sourced without intense     │
│   audit scrutiny. Subscription renewals create continuous administrative friction.     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ BARRIER 2: Subsurface Data Sovereignty & MoPNG Directives                              │
│ • Foreign cloud SaaS (DELFI, Corva) requires exporting raw telemetry and subsurface    │
│   coordinates to US/EU multi-tenant servers. DGH NDR regulations strictly prohibit     │
│   unauthorized cross-border transmission of Indian exploration assets.                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ BARRIER 3: Opaque Multi-Crore Foreign Exchange Exposure                                │
│ • Paying $50,000–$100,000 per seat in USD exposes CPSE budgets to severe currency     │
│   depreciation risk. PSUs mandate fixed INR contracts with defined scope.              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ BARRIER 4: The Mud Logging Unit (MLU) Disconnection                                    │
│ • Service cartels design software to ingest data from their own proprietary downhole   │
│   tools. OIL hires independent Mud Logging Units via open competitive bidding (e.g.    │
│   OIL's 2026 tender for 12+4 MLUs). Software must be 100% vendor-agnostic.           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ BARRIER 5: Lack of Local Assam Basin Customization                                     │
│ • Western software treats stratigraphy as standard Permian/Gulf of Mexico models.     │
│   They do not support Upper Assam specific formations (Tipam, Barail, Kopili) or local │
│   DDR formats (handwritten tour sheets, legacy Moran/Nahorkatiya terminology).         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. The NWIS Business Model: Sovereign & Vendor-Agnostic

NWIS fundamentally disrupts this broken procurement dynamic by offering an architecture designed specifically for the operational and legal constraints of an Indian Maharatna CPSE:

| Feature / Dimension | Global Commercial Cartels | eRTMAC-NWIS Proposed Model |
| :--- | :--- | :--- |
| **Procurement Type** | Multi-year recurring USD SaaS subscription. | **Turnkey Indigenous Asset (Perpetual IP Ownership for OIL).** |
| **Data Hosting** | Multi-tenant US/EU public cloud. | **100% On-Premise Air-Gapped (Duliajan eRTMAC / Rig IPC).** |
| **Currency** | USD ($) with currency exchange volatility. | **INR (₹) with predictable domestic maintenance costs.** |
| **Telemetry Ingestion**| Locked to vendor tools (SLB, BHI). | **Vendor-Agnostic: Open WITS0 / WITSML from any MLU contractor.** |
| **Ongoing Cost** | ₹1.5–₹4 Crore per year in recurring SaaS. | **Zero per-well software royalties; minimal local IT upkeep.** |
| **Compliance** | Violates DGH NDR data residency rules. | **100% Compliant with DGH, MoPNG, and OISD-STD-187.** |

---

## 6. Strategic Takeaway for SIH Evaluation Defense

When the SIH jury asks: *"Why shouldn't Oil India simply buy SLB Tela or Corva?"*

The team delivers the definitive response:
> *"SLB Tela and Corva require multi-crore annual USD subscriptions, lock OIL into foreign cloud platforms violating DGH NDR data sovereignty, and cannot natively parse OIL's legacy scanned DDRs from Moran and Nahorkatiya. NWIS provides OIL with a 100% sovereign, perpetual, vendor-agnostic platform that runs air-gapped inside Duliajan eRTMAC at a fraction of the cost."*
