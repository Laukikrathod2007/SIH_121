# PS 121 — Code-Level Gap Analysis

This document provides exact, file-and-line-grounded evidence of technical gaps discovered across the audited competitor repositories, demonstrating why current implementations are insufficient and defining how **PS 121 (SIH 26121)** can build superior, defensible engineering solutions.

---

## Gap 1: Absence of Stratigraphic Normalization & Dip-Aware Depth Scaling
- **Competitors**: All Audited Competitors (`SIH_2026_PLANNS`, `DrillMind`, `PetrolQ`, `pallavi-eRTMAC-NWIS`, `DrillSense`, `DDR_UTAH_FORGE`)
- **Missing Capability**: Cross-well formation thickness scaling and dip-corrected depth correlation ($\xi(d)$).
- **Code Evidence**:
  - `SIH_2026_PLANNS`: `NLP/nwis-sentinel/backend/app/services/similarity_engine.py` Lines 25–40: Linear depth proximity calculation based on raw Measured Depth ($1 - \frac{|\Delta MD|}{500}$).
  - `DrillMind`: `src/drillmind/copilot/context_builder.py` Lines 60–85: Slices historical DDRs within a flat $\pm 100\text{m}$ Measured Depth window.
  - `PetrolQ`: `backend/api/lookahead.py` Lines 15–45: Hardcoded static depth horizons (`Tipam Sandstone: 1200m`, `Barail: 2400m`) in `WELL_FORMATION_HORIZONS`.
- **Current Implementation**: Competitors assume either (a) flat earth horizontal formations where depth is identical across all offset wells, or (b) calculate a simple Euclidean difference in Measured Depth (MD).
- **Why It Is Insufficient**: In real structural basins (such as the Upper Assam Shelf and folded thrust belts), formations dip regionally by $3^\circ$ to $15^\circ$ SE and vary in gross thickness by hundreds of meters. A depth of 2,400m MD in Well A may be in the high-permeability Tipam Sandstone, while in Well B (2 km away) 2,400m MD has already entered the overpressured Barail Coal-Shale. Comparing wells on raw MD leads to catastrophic false-analog matching.
- **PS 121 Opportunity**: Implement dimensionless stratigraphic depth normalization:
  $$\xi(d) = \frac{d_{\text{tvdss}} - Z_{\text{top}}}{Z_{\text{base}} - Z_{\text{top}}}$$
- **Possible Improved Implementation**: Transform all historical offset well incidents, logs, and drilling parameters from raw MD into dimensionless interval coordinate $\xi \in [0.0, 1.0]$. When the active bit penetrates depth $d_{\text{act}}$ with stratigraphic ratio $\xi_{\text{act}} = 0.65$ in the Barail Formation, query offset well events at $\xi_{\text{offset}} \in [0.55, 0.75]$, regardless of whether the offset well penetrated that interval at 2,100m or 2,700m TVDSS.
- **Potential Differentiation**: **Highest possible technical defensibility**. Solves the fundamental geological correlation problem that no competitor has addressed.

---

## Gap 2: Synthesized / Fake Well Logs & Missing Petrophysical LAS Parsing
- **Competitor**: `PetrolQ`
- **Repository**: `research/competitors/direct/PetrolQ`
- **Missing Capability**: Real petrophysical log ingestion and multi-well curve correlation.
- **Code Evidence**: `backend/api/correlate.py` Lines 30–65:
  ```python
  def synthesize_gr_logs(well_id: str, tvd_max: float = 3500.0):
      # Generates synthetic GR log curve based on regional stratigraphy
      depths = np.linspace(100.0, tvd_max, 120)
      if reg == "rajasthan":
          val = 45.0 + 15.0 * np.sin(z / 40.0) + rng.uniform(-5, 5)
      elif reg == "kg":
          val = 68.0 + 10.0 * np.sin(z / 50.0) + rng.uniform(-6, 6)
  ```
- **Current Implementation**: When actual LAS well logs are missing, the backend generates deterministic sine wave data to feed the FastDTW algorithm for frontend demonstration.
- **Why It Is Insufficient**: Demonstrates a mock calculation rather than a real petrophysical correlation. Real drilling engineers immediately recognize artificial sine curves and lose confidence in the decision support platform.
- **PS 121 Opportunity**: Implement a true `lasio` / `dlisio` parsing and petrophysical normalization engine capable of ingesting standard industry log files, extracting Gamma Ray, Resistivity, Sonic (DT), Density, and Caliper curves, and performing FastDTW alignment on real geological signals.
- **Possible Improved Implementation**: Build a unified Log Ingestion Service with automatic curve alias standardization (e.g. mapping `GR`, `GRD`, `CGR` $\to$ Standardized Gamma Ray) and despiking/null-value filtering.
- **Potential Differentiation**: Provides genuine petrophysical correlation grounded in physical subsurface measurements.

---

## Gap 3: Missing Fault-Block Geological Isolation in Geospatial Queries
- **Competitors**: `SIH_2026_PLANNS`, `PetrolQ`, `pallavi-eRTMAC-NWIS`
- **Missing Capability**: Structural fault-block barrier gating during offset well selection.
- **Code Evidence**:
  - `PetrolQ`: `backend/main.py` & `models.py`: Uses PostGIS `ST_DWithin(geom, active_geom, radius)` without structural polygon constraints.
  - `SIH_2026_PLANNS`: `app/services/similarity_engine.py` L45-60: Uses 2D geographic distance with a flat $0.15$ weight factor.
- **Current Implementation**: Offset wells are ranked strictly by surface Euclidean or Great Circle distance.
- **Why It Is Insufficient**: In compartmentalized reservoirs with sealing faults (e.g. Naga Thrust, Jaipur Fault in Assam), an offset well located only 500m away across a sealing fault may have a completely different pore pressure regime, fluid contact, and stress orientation compared to an offset well 3,000m away within the same fault compartment. Treating the 500m well as the primary analog creates severe drilling hazards (unexpected kicks or losses).
- **PS 121 Opportunity**: Implement Structural Fault-Block Partitioning. Store regional fault line polygons and fault sealing attributes in PostGIS (`ST_Crosses`, `ST_Within`).
- **Possible Improved Implementation**: If a candidate offset well's trajectory intersects or lies across a confirmed sealing fault polygon, penalize its similarity score by a structural barrier factor ($\beta_{\text{fault}} = 0.2$), prioritizing offset wells that share the same structural compartment.
- **Potential Differentiation**: Elevates geospatial querying from a generic map distance calculation to a structurally intelligent geological tool.

---

## Gap 4: Forward Lookahead Ahead-of-the-Bit Risk Corridor vs Post-Mortem Search
- **Competitors**: `DrillMind`, `pallavi-eRTMAC-NWIS`, `DrillSense`, `SIH_2026_PLANNS`
- **Missing Capability**: Dynamic forward lookahead risk corridor (+50m to +200m ahead of current bit position).
- **Code Evidence**:
  - `DrillMind`: `src/drillmind/copilot/engine.py`: Answers questions about historical reports post-mortem; does not project ahead of the bit.
  - `pallavi-eRTMAC-NWIS`: `backend/src/hazard_monitor.py`: Scans past documents and lists extracted incidents without real-time trajectory forecasting.
- **Current Implementation**: Users must manually formulate search queries or review past reports in a search box.
- **Why It Is Insufficient**: During active drilling operations, drilling engineers and RTOC supervisors do not have time to manually search historical archives. They need the system to autonomously project what hazards lie in the next 100 meters based on the active well's current TVDSS and trajectory inclination.
- **PS 121 Opportunity**: Build an autonomous Ahead-of-Bit Projection Engine:
  $$\text{Lookahead Corridor} = [d_{\text{tvdss}}, d_{\text{tvdss}} + \Delta z], \quad \Delta z \in [50\text{m}, 200\text{m}]$$
- **Possible Improved Implementation**: As live bit depth updates via WITSML or manual entry, the system automatically correlates the projected corridor with all nearby offset wells, identifies upcoming formation boundaries, mud loss zones, and overpressure transitions, and alerts the driller before the bit enters the hazard zone.
- **Potential Differentiation**: Transforms the system from a passive search engine into an active, predictive decision support copilot.

---

## Gap 5: 1-Click Interactive PDF Bounding-Box Provenance
- **Competitors**: `SIH_2026_PLANNS`, `PetrolQ`, `DrillSense`, `DrillMind`
- **Missing Capability**: Visual PDF rendering with pixel-exact bounding-box highlight overlays on extracted text, tables, and figures.
- **Code Evidence**:
  - `SIH_2026_PLANNS`: `module5_engineering_agent/schemas/models.py`: Returns string chunk text and snippet IDs in JSON.
  - `PetrolQ`: `backend/api/ai_assistant.py`: Returns citation text strings like `"Source: Well-A1_EOWR.pdf, Page 42"`.
- **Current Implementation**: Competitors output plain text responses with markdown citations referencing file names and page numbers.
- **Why It Is Insufficient**: Drilling engineers and company men making high-stakes decisions ($100k+/day rig costs) will not trust a text summary from an LLM unless they can instantly verify the exact original statement, casing tally table, or mud log record with a single click.
- **PS 121 Opportunity**: Store normalized bounding-box coordinates $(x_0, y_0, x_1, y_1)$ during PDF ingestion for every extracted entity, table row, and incident.
- **Possible Improved Implementation**: When an engineer clicks any citation badge in the AI recommendation or hazard card, the UI instantly opens the original PDF page in a synchronized side drawer with the exact sentence, casing specification, or mud loss entry highlighted in glowing amber.
- **Potential Differentiation**: Delivers unmatched operational transparency, auditability, and user trust.
