# Domain Glossary & Technical Terminology Reference
### Petroleum Engineering, Directional Survey Mathematics, Drilling Physics, and AI/ML Definitions
**Standards:** SPE (Society of Petroleum Engineers) Technical Nomenclature | **IADC** Lexicon

---

## 1. Directional Drilling & Subsurface Geodesy

* **Measured Depth (MD):** The actual physical distance along the wellbore path from the surface reference datum (Kelly Bushing) to any downhole point. Measured in meters or feet of drill pipe.
* **True Vertical Depth (TVD):** The vertical distance from the horizontal plane of the surface datum to any downhole point, disregarding wellbore inclination and curvature.
* **True Vertical Depth Subsea (TVDSS):** True Vertical Depth referenced to Mean Sea Level (MSL), eliminating variations in rig Kelly Bushing elevations across different terrain.
* **True Stratigraphic Depth (TSD):** Depth measured perpendicular or normalized to the geological formation plane, accounting for regional structural dip and bed tilt.
* **Dimensionless Stratigraphic Index ($\xi$):** The normalized penetration coordinate ($\xi \in [0.0, 1.0]$) representing the relative position of the drill bit between the formation top ($\xi = 0$) and base ($\xi = 1$).
* **Minimum Curvature Method:** The SPE-standard numerical algorithm used to calculate 3D Cartesian coordinates $(TVD, North, East)$ between discrete directional survey stations by modeling the wellbore as a smooth circular arc in three-dimensional space.
* **Dogleg Severity (DLS):** A normalized measure of the overall curvature of a wellbore path, typically expressed in degrees per 30 meters or degrees per 100 feet.
* **Azimuth ($A$):** The horizontal angle of the wellbore trajectory measured clockwise relative to true north ($0^\circ$ to $360^\circ$).
* **Inclination ($I$):** The angular deviation of the wellbore trajectory from true vertical ($0^\circ$ = vertical, $90^\circ$ = horizontal).

---

## 2. Drilling Physics, Hydraulics & Operational Parameters

* **Rate of Penetration (ROP):** The speed at which the drill bit deepens the wellbore, measured in meters per hour ($\text{m/hr}$) or feet per hour ($\text{ft/hr}$).
* **Weight on Bit (WOB):** The downward mechanical axial force applied to the drill bit by the heavy drill collars and BHA, measured in thousands of pounds ($\text{klbs}$) or kilonewtons ($\text{kN}$).
* **Standpipe Pressure (SPP):** The total gauge pressure recorded at the surface standpipe required to circulate drilling fluid down the drillstring, through the bit nozzles, and up the annulus.
* **Equivalent Circulating Density (ECD):** The effective downhole fluid density resulting from static mud hydrostatic pressure plus dynamic annular frictional pressure drops while circulating.
* **Lost Circulation Material (LCM):** Specialized solid bridging agents (calcium carbonate, walnut shells, mica flakes, synthetic fibers) pumped downhole to seal permeable thief zones or natural fractures.
* **Non-Productive Time (NPT):** Time during well construction when planned drilling progress is halted due to equipment failure, hole complications, or well control operations.
* **Shut-In Drillpipe Pressure (SIDPP):** The stabilized surface pressure recorded on the drill pipe after closing the BOP rams following a kick, directly reflecting the formation underbalance.
* **Shut-In Casing Pressure (SICP):** The surface pressure recorded on the casing annulus after shut-in, reflecting the composite hydrostatic head of mud and the lighter formation influx.
* **Jordan-Shirley $d$-Exponent ($d_{cs}$):** A normalized drilling parameter used to detect abnormal pore pressure by identifying negative deviations from normal compaction trends in shales.
* **Bottom Hole Assembly (BHA):** The lower portion of the drillstring comprising the bit, stabilizer, mud motor or rotary steerable system (RSS), MWD/LWD tools, and heavy drill collars.

---

## 3. Upstream Data Standards & Protocols

* **WITSML:** *Wellsite Information Transfer Standard Markup Language.* An XML/SOAP/REST open standard governed by Energistics for transferring real-time drilling, trajectory, and subsurface data.
* **WITS Level 0:** *Wellsite Information Transfer Specification.* A legacy point-to-point ASCII serial/TCP stream protocol used for 1 Hz surface sensor broadcasts.
* **PPDM:** *Professional Petroleum Data Management.* The global industry-standard relational data model for master upstream E&P information (wells, fields, operators, facilities).
* **OSDU:** *Open Subsurface Data Universe.* An open-source, standards-based data platform facilitating cloud-native subsurface workflows and data interoperability.
* **IADC:** *International Association of Drilling Contractors.* Authoritative body establishing standard operational codes for Daily Drilling Reports and NPT categorization.

---

## 4. Artificial Intelligence, Data Science & Geospatial Terms

* **DORS:** *Dynamic Offset Relevance Scoring.* The proprietary 5-factor mathematical framework implemented in NWIS unifying spatial, formation, depth, trajectory, and hazard density into a single relevance metric.
* **Agentic RAG:** *Retrieval-Augmented Generation with Agentic Workflow.* An architecture combining semantic dense vector search, hard geological metadata filtering, and strict source citation grounding.
* **SentenceTransformers (`all-MiniLM-L6-v2`):** A lightweight transformer model mapping sentences and domain narratives to 384-dimensional dense vector embeddings.
* **HNSW:** *Hierarchical Navigable Small World.* A high-dimensional vector indexing algorithm providing ultra-fast Approximate Nearest Neighbor (ANN) search in pgvector.
* **Isolation Forest:** An unsupervised machine learning algorithm that isolates anomalies by randomly partitioning feature values into binary search trees.
* **XGBoost:** *Extreme Gradient Boosting.* An optimized distributed gradient boosting library implementing supervised decision tree ensembles for multi-class hazard classification.
* **Haversine Formula:** A spherical trigonometric equation used to calculate great-circle distances between pairs of latitude and longitude coordinates across the Earth's surface.
