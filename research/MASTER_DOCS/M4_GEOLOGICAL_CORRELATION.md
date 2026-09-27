# eRTMAC-NWIS: Module 4 — Geological, Drilling and Reservoir Correlation
# Master Document 4 of 6 — The Most Critical Technical Module

> An AI reading this file can implement Module 4 completely.
> This is the deepest technical module. It answers: HOW do we know our correlation is correct?
> HOW does TVDSS normalization work? HOW does the xi ratio work?
> HOW does the system know which offset well intervals are geologically equivalent?

---

## 1. Why Module 4 Exists: The Core Engineering Problem

Imagine two adjacent wells in the Nahorkatiya field:
  Well NHK-100: Vertical well, drilled in 1995, total depth 3,500 m MD
  Well NHK-200: Deviated well (35 degrees inclination), drilled in 2018, total depth 4,100 m MD

When the active well is drilling at 3,200 m MD and we ask "what happened in NHK-100 near this
depth?", the naive answer is to look at NHK-100 events between 3,150 m and 3,250 m.

THIS IS WRONG FOR TWO REASONS:

Reason 1 — Directional Survey Difference:
  NHK-200 is deviated at 35 degrees. At 3,200 m MD, its True Vertical Depth Subsea (TVDSS)
  is only 2,986 m (= 3,200 * cos(35°) + wellhead elevation correction).
  NHK-100 is vertical. At 3,200 m MD, its TVDSS is approximately 3,115 m.
  Comparing raw MD = comparing different geological horizons.

Reason 2 — Structural Position Difference:
  Even if both wells were vertical, Upper Assam formation dip of 3-15 degrees SE means
  a well 1.5 km to the SE hits the same formation 200-400 m deeper in MD/TVDSS.
  The same Tipam Sandstone formation top that is at 1,400 m TVDSS in NHK-100
  may be at 1,800 m TVDSS in a well 2 km southeast.

Module 4 solves both problems using:
  1. TVDSS conversion (fixes directional survey difference)
  2. Stratigraphic ratio xi (fixes structural position difference)

---

## 2. Step 1: Converting Measured Depth to True Vertical Depth Subsea (TVDSS)

### 2.1 What TVDSS Is

TVDSS = True Vertical Depth Sub-Sea
  It is the vertical distance from Mean Sea Level (MSL) down to the measurement point.
  It removes: wellbore inclination effects, surface elevation variations.
  
Convention: TVDSS is negative above MSL, positive below MSL.
  If wellhead elevation = +85 m above MSL
  If TVD at a measurement point = 3,000 m below wellhead
  Then TVDSS = 3,000 - 85 = 2,915 m (below MSL)

### 2.2 The Minimum Curvature Method (Industry Standard)

Every directional well has a SURVEY FILE — a table of MD, Inclination (INC), and Azimuth (AZ)
measured by downhole survey instruments at regular intervals (every 30-100 m).

The Minimum Curvature Method converts these to 3D Cartesian coordinates:

For each survey station pair (station i to station i+1):
  DL (Dogleg) = arccos(cos(INC_i - INC_i+1) - sin(INC_i)*sin(INC_i+1)*(1 - cos(AZ_i - AZ_i+1)))
  
  If DL != 0:
    RF (Ratio Factor) = (2/DL) * tan(DL/2)
  Else:
    RF = 1  (straight segment)

  delta_MD = MD_i+1 - MD_i
  
  delta_North = (delta_MD/2) * (sin(INC_i)*cos(AZ_i) + sin(INC_i+1)*cos(AZ_i+1)) * RF
  delta_East  = (delta_MD/2) * (sin(INC_i)*sin(AZ_i) + sin(INC_i+1)*sin(AZ_i+1)) * RF
  delta_TVD   = (delta_MD/2) * (cos(INC_i) + cos(INC_i+1)) * RF

  Cumulative: TVD += delta_TVD
  
  TVDSS = TVD - wellhead_elevation_above_MSL

### 2.3 Implementation Using wellborepath Library

  pip install wellborepath  # Open-source Python library for minimum curvature

  from wellborepath import compute_wellbore_path

  survey_df = pd.DataFrame({
      'md': [0, 100, 200, 500, 1000, 1500, 2000, 3000],
      'inc': [0, 2, 8, 20, 30, 35, 35, 35],  # inclination degrees
      'az': [0, 45, 45, 45, 45, 45, 45, 45]  # azimuth degrees
  })

  result = compute_wellbore_path(survey_df['md'], survey_df['inc'], survey_df['az'])
  survey_df['tvd'] = result['tvd']
  survey_df['tvdss'] = survey_df['tvd'] - wellhead_elevation_m

  # Now interpolate TVDSS for any arbitrary MD using scipy
  from scipy.interpolate import interp1d
  md_to_tvdss = interp1d(survey_df['md'], survey_df['tvdss'], kind='linear')
  
  tvdss_at_3200m = md_to_tvdss(3200)  # returns 2986 for a 35-degree deviated well

### 2.4 Fallback for Vertical Wells or Missing Survey Data

  # If no directional survey (most old vertical wells):
  # Assume vertical (TVD = MD), apply elevation correction only
  def md_to_tvdss_vertical(md, wellhead_elevation):
      return md - wellhead_elevation

  # Flag: well.tvd_method = "MINIMUM_CURVATURE" or "VERTICAL_ASSUMPTION"
  # Vertical assumption introduces ~2% error for wells with <3 degree inclination

### 2.5 How to Verify TVDSS Conversion Is Correct

Verification Check 1 — Formation Top Sanity:
  After converting all formation tops to TVDSS, they should be consistent across wells
  within the same field. Tipam Sandstone tops in Nahorkatiya should all be within
  +/-200 m TVDSS of each other (field-scale structure varies but not wildly).
  
  If a converted TVDSS top is >500 m different from neighbors -> flag for review.

Verification Check 2 — Cross-Section Dip Consistency:
  Plot TVDSS tops of the same formation across multiple wells ordered by east-west position.
  Tops should show a systematic deepening to the southeast at 3-15 degrees.
  Anomalous jumps indicate either a fault between wells or a conversion error.

Verification Check 3 — Gas-Oil Contact Depth:
  In producing fields, the gas-oil contact (GOC) and oil-water contact (OWC) are horizontal
  by definition (governed by fluid density). After TVDSS conversion, contacts from different
  wells in the same reservoir should be at the same TVDSS. Mismatch > 10 m = conversion error.

---

## 3. Step 2: The Stratigraphic Depth Ratio Xi (The Core Innovation)

### 3.1 Why TVDSS Alone Is Not Enough

Even after converting to TVDSS, two wells in different structural positions have their
formation tops at different TVDSS values. The Tipam Sandstone might be:
  NHK-100 (structural crest): Tipam top at 1,400 m TVDSS, base at 2,200 m TVDSS
  NHK-300 (structural flank): Tipam top at 1,750 m TVDSS, base at 2,600 m TVDSS

If the active well (NHK-400, new) is at 1,600 m TVDSS and we ask:
"What happened in NHK-300 at the geologically equivalent depth?"

We cannot just search NHK-300 events at 1,600 m TVDSS — the formation isn't even there yet.
We need to find the PROPORTIONALLY EQUIVALENT position WITHIN the Tipam Sandstone.

### 3.2 The Xi Ratio Formula

The stratigraphic depth ratio xi maps a depth position WITHIN a formation to a
normalized 0-1 scale, independent of absolute TVDSS values:

  xi(d, well) = (d_tvdss - Top_formation_tvdss(well)) / Thickness_formation(well)

Where:
  d_tvdss = the TVDSS depth we want to map
  Top_formation_tvdss(well) = TVDSS of the formation top in this specific well
  Thickness_formation(well) = TVDSS thickness of the formation in this specific well
                              = Base_tvdss(well) - Top_tvdss(well)

Result: xi = 0 means "at the very top of the formation"
        xi = 1 means "at the very base of the formation"
        xi = 0.5 means "exactly in the middle of the formation"
        xi < 0 or xi > 1 means "outside this formation" (in adjacent formation)

### 3.3 The Full Correlation Algorithm

Given: Active well A currently at TVDSS depth d_active
       Offset well B with formation top tables loaded

Step 1: Identify which formation d_active is in (active well A):
  for formation in active_well.formation_tops:
      if formation.top_tvdss <= d_active < formation.base_tvdss:
          current_formation = formation.name
          xi_active = (d_active - formation.top_tvdss) / formation.thickness
          break

Step 2: Find the equivalent TVDSS depth in offset well B:
  if current_formation in offset_well_B.formation_tops:
      B_top = offset_well_B.formation_tops[current_formation].top_tvdss
      B_thickness = offset_well_B.formation_tops[current_formation].thickness
      equivalent_tvdss_in_B = B_top + (xi_active * B_thickness)
  else:
      # Formation not penetrated by offset well B — no correlation possible
      equivalent_tvdss_in_B = None

Step 3: Search offset well B NPT events within a correlation window:
  window_m = 50  # +/- 50 m TVDSS around the equivalent depth
  relevant_events = offset_well_B.npt_events.filter(
      depth_tvdss__gte = equivalent_tvdss_in_B - window_m,
      depth_tvdss__lte = equivalent_tvdss_in_B + window_m
  )

Step 4: Compute the Ahead-of-Bit projection (for Module 6 alert):
  lookahead_m = 50  # Project 50 m ahead in TVDSS
  future_tvdss = d_active + lookahead_m
  # Repeat xi calculation for future_tvdss
  # Search all offset wells for events near equivalent_tvdss(future_tvdss)

### 3.4 Concrete Numerical Example

Active well NHK-412 currently drilling at 3,200 m MD -> TVDSS = 2,986 m
Barail Lower Sand formation tops in NHK-412:
  Top: 2,940 m TVDSS
  Base: 3,380 m TVDSS (estimated from offset wells)
  Thickness: 440 m

xi at current depth: (2,986 - 2,940) / 440 = 0.105 (11% into Barail Lower Sand)

Offset well NHK-089 (drilled 2015, structural flank):
  Barail Lower Sand top: 3,180 m TVDSS
  Barail Lower Sand base: 3,640 m TVDSS
  Thickness: 460 m

Equivalent depth in NHK-089: 3,180 + (0.105 * 460) = 3,180 + 48 = 3,228 m TVDSS

Query NPT events in NHK-089 between (3,228 - 50) = 3,178 m and (3,228 + 50) = 3,278 m TVDSS:
RESULT: "Total mud losses at 3,228 m TVDSS (Barail Lower Sand). 45 bbl/hr. Cured with nut plug."

THIS IS THE CORRELATION. NHK-412 at 2,986 m TVDSS is geologically equivalent to
NHK-089 at 3,228 m TVDSS because they are at the same stratigraphic position (xi = 0.105)
within the Barail Lower Sand formation. The raw TVDSS difference is 242 m — raw depth
comparison would have completely missed this event.

---

## 4. Verification: How Do We Know the Correlation Is Correct?

### 4.1 Ground Truth Validation Method

The only reliable validation is cross-checking against known field history.

  Test A — Same Formation, Same Event Type:
  If we correlate NHK-412 at xi=0.5 in Tipam to NHK-089 at xi=0.5 in Tipam,
  and both have recorded "lost circulation" events, the correlation is validated.
  Formula: Correlation_TP_rate = (events found in both wells at same xi +/- 0.1) / total events

  Test B — Stratigraphic Cross-Section:
  Plot correlated formation tops from 10 wells on a structural cross-section (W-E transect).
  They should show a smooth, consistent dip pattern toward the SE (3-15 degrees).
  Sharp discontinuities indicate either a fault (valid geology) or a correlation error.

  Test C — NPT Depth Consistency Across Wells:
  All Lost Circulation events should cluster within the Tipam Sandstone (xi range 0-1).
  All Stuck Pipe events should cluster within the Barail Coal-Shale (xi range 0-1).
  If events appear in wrong formations (xi < 0 or xi > 1) -> formation top table error.

  Test D — The "Blind Prediction" Test:
  For a historical well (not in training data), hide all its NPT events.
  Run the xi correlation against offset wells.
  Predict which formation intervals have highest historical risk.
  Then reveal actual events and check recall.
  Acceptance criterion: 70% of actual NPT events predicted within +/-100 m TVDSS equivalent.

### 4.2 Formation Top Uncertainty Propagation

When formation top data is inferred (not directly drilled) or from LOW confidence OCR extraction,
the xi calculation has uncertainty. Report this to the engineer:

  xi_uncertainty = sqrt((sigma_top/thickness)^2 + (sigma_thickness * (d-top)/thickness^2)^2)
  
  If xi_uncertainty > 0.15 (15% of formation thickness):
      alert_message += "[WARNING: Stratigraphic correlation uncertainty is HIGH. "
                       "Offset well {name} has inferred formation tops — treat with caution.]"

### 4.3 Fault Block Detection

If the xi correlation returns ZERO matching events in an offset well that has extensive NPT history
in adjacent wells, this may indicate a FAULT BLOCK BOUNDARY between the active and offset well.

  Fault detection heuristic:
  If (distance_to_offset < 2km) AND (xi_correlation_score < 0.3) AND
     (offset_well_has_>5_NPT_events_in_this_formation):
     flag_potential_fault_boundary(active_well, offset_well)

In the demo: pre-load a simplified fault polygon for the Moran-Nahorkatiya boundary
based on published structural maps. Wells on opposite sides of this polygon are
grayed out on the map and excluded from the offset ranking.

---

## 5. The Offset Relevance Ranking Engine: Omega(w, z)

Module 4 ranks all candidate offset wells using a multi-criteria score.
This score is recalculated every 30 seconds as the bit depth changes.

### 5.1 The Omega Formula

  Omega(w, z) = w1*S_distance(w) + w2*S_geological(w, z) + w3*S_trajectory(w) + w4*S_completion(w)

Where:
  w = offset well candidate
  z = current active well TVDSS depth
  w1, w2, w3, w4 = configurable weights (default: 0.25, 0.40, 0.20, 0.15)

Score components (all normalized to 0-1):

S_distance(w):
  Euclidean surface distance from active wellhead to offset wellhead.
  Max distance for consideration: 50 km (default, configurable)
  score = 1 - (distance_km / max_distance_km)
  Example: well 5 km away -> score = 1 - 5/50 = 0.90

S_geological(w, z):
  Does offset well w penetrate the same formation currently being drilled in active well?
  Does it have NPT events at the same xi position (+/- 0.15)?
  score = (formation_match_flag * 0.5) + (npt_cluster_match * 0.5)
  
  formation_match_flag: 1.0 if well w has formation tops for current formation; 0.0 if not
  npt_cluster_match: Proportion of events in w within +/-0.15 xi of current position

S_trajectory(w):
  Azimuth similarity between active well and offset well at current depth.
  If both wells are drilled in the same direction, they penetrate similar rock sequences.
  score = cos(azimuth_active - azimuth_offset)  # cos = 1 when same direction, -1 when opposite

S_completion(w):
  Same completion type as active well = higher relevance.
  Both vertical: score = 1.0
  One vertical, one deviated: score = 0.5
  Both deviated, similar inclination (+/- 10 deg): score = 0.9

### 5.2 Demo Display of Omega Reranking

In the demo, the sidebar panel shows a ranked list of offset wells:
  Rank | Well Name | Distance | Omega Score | NPT Events at Current Zone
   1   | NHK-089   |  1.8 km  |    0.87     | 3 lost circulation events
   2   | NHK-145   |  3.1 km  |    0.72     | 1 stuck pipe event
   3   | MOR-034   |  8.4 km  |    0.61     | 2 lost circulation events
   ...

As the bit drills from 3,200 m to 3,300 m (Barail Lower to Barail Coal transition),
the Omega scores RECALCULATE and the list REORDERS. The judges see this live.
MOR-034 which has extensive Barail Coal-Shale stuck pipe history rises to Rank 1.
This demonstrates that the system understands geology, not just geography.

---

## 6. The Ahead-of-Bit Historical Risk Corridor

### 6.1 What It Is

At any moment, NWIS projects THREE windows ahead of the current bit depth:
  Window 1 (Proactive):   +50 to +200 m TVDSS ahead — "What is coming?"
  Window 2 (Warning):     +20 to +50 m TVDSS ahead  — "Prepare now"
  Window 3 (Imminent):    0 to +20 m TVDSS ahead    — "Imminent hazard"

For each window, we run the xi correlation against ALL top-ranked offset wells and
aggregate their NPT event histories into a RISK CORRIDOR — a depth-vs-risk chart
showing the historical probability of each hazard type at each upcoming depth.

### 6.2 Risk Corridor Calculation

  def compute_risk_corridor(active_well, current_tvdss, offset_wells):
      lookahead_depths = np.arange(current_tvdss, current_tvdss + 200, 10)  # every 10 m
      corridor = {}

      for future_tvdss in lookahead_depths:
          xi_future = compute_xi(future_tvdss, active_well)
          corridor[future_tvdss] = {
              "lost_circulation": 0,
              "stuck_pipe": 0,
              "gas_kick": 0,
              "events_evidence": []
          }
          for well in offset_wells[:5]:  # Top 5 ranked offsets
              equivalent_depth = xi_to_tvdss(xi_future, well)
              events = query_npt_events(well, equivalent_depth, window=30)
              for event in events:
                  corridor[future_tvdss][event.type] += event.severity
                  corridor[future_tvdss]["events_evidence"].append({
                      "well": well.name,
                      "depth_tvdss": event.depth_tvdss,
                      "description": event.mitigation_applied,
                      "doc_id": event.document_id,
                      "page": event.page_number,
                      "bbox": [event.bbox_x0, event.bbox_y0, event.bbox_x1, event.bbox_y1]
                  })

      return corridor

### 6.3 Risk Corridor Display

On the center panel of the cockpit, a vertical track shows the risk corridor:
  - X-axis: Risk level (0-10, aggregated severity from offset wells)
  - Y-axis: Depth (current bit position at bottom, projects upward as bit advances)
  - Color bands: Green (<3), Amber (3-6), Red (>6)
  - Each event marker: clickable, opens the source DDR PDF viewer

The bit position marker moves DOWN the track in real time as the WebSocket stream advances depth.
When the bit marker approaches an amber/red band -> alert fires in Module 6.

---

## 7. Handling Formations Without Top Data

### 7.1 Missing Formation Tops (Common in Old Wells)

Many pre-2000 OIL wells have no digitized formation top tables. Only operations tables exist.
In this case:

  Strategy 1 — Infer from Lithology Tags:
  If the DDR remarks say "penetrated sand at 3,218 m" and the Barail Lower Sand is the expected
  formation at that depth in this area -> infer: Barail_Lower_Top = 3,218 m MD for this well.
  Confidence = INFERRED.

  Strategy 2 — Statistical Imputation from Neighbors:
  If offset wells within 3 km all have Barail top at 2,900-3,200 m TVDSS,
  assign a missing well's Barail top = median of neighbors. Confidence = IMPUTED.

  Strategy 3 — Structural Dip Extrapolation:
  If the formation dip is known (e.g., 5 degrees SE from seismic), extrapolate the formation
  top from the nearest well with known tops using dip*distance correction.

  Display in UI: Well with INFERRED tops shown with dashed outline on map.
  Warning shown to engineer: "Formation correlation for NHK-025 uses inferred tops.
  Treat risk alerts from this well as lower confidence."

---

## 8. Module 4 API Endpoints

  GET /api/correlation/xi?active_well={id}&depth_tvdss={d}
  Returns: {current_formation, xi_value, offset_well_equivalent_depths: [{well_id, tvdss}]}

  GET /api/correlation/risk_corridor?active_well={id}&depth_tvdss={d}&lookahead_m=200
  Returns: {corridor: [{tvdss, lost_circulation_risk, stuck_pipe_risk, gas_kick_risk, evidence: [...]}]}

  GET /api/offset_ranking?active_well={id}&depth_tvdss={d}
  Returns: {ranked_wells: [{well_id, omega_score, distance_km, npt_events_in_zone}]}

  GET /api/formation_tops/{well_id}
  Returns: {tops: [{formation, depth_md, depth_tvdss, confidence, source_doc_id}]}

---

## 9. Summary: How to Know Module 4 Is Working

The module is working correctly when:

1. TWO WELLS IN SAME FIELD show the same formation at consistent TVDSS depths:
   NHK-100 Tipam top: 1,400 m TVDSS
   NHK-200 Tipam top: 1,380 m TVDSS  (plausible 20 m difference over short distance)
   PASS.

2. STRUCTURAL DIP IS VISIBLE IN DATA:
   Wells ordered W to E show Tipam tops consistently getting deeper eastward.
   Dip rate: ~50-100 m TVDSS per km (consistent with 3-6 degree dip).
   PASS.

3. NPT EVENTS CLUSTER IN CORRECT FORMATIONS:
   After xi conversion, 85%+ of Lost Circulation events have xi in [0, 1] for Tipam.
   After xi conversion, 80%+ of Stuck Pipe events have xi in [0, 1] for Barail_Coal.
   PASS if clustering is observed; FAIL if events appear scattered across formations.

4. BLIND PREDICTION TEST:
   Hide events from one well. Run correlation. Predict hazard zones.
   70%+ of actual events predicted within +/-100 m equivalent TVDSS.
   This is the engineering acceptance criterion.

5. LIVE DEMO: OMEGA LIST REORDERS AS BIT DRILLS:
   As bit advances from Tipam (1,800 m TVDSS) into Barail (3,200 m TVDSS),
   the offset well ranked #1 changes from a well with Tipam history to a
   well with Barail Coal-Shale stuck pipe history.
   This live reranking is the most powerful visual proof that Module 4 works.


---
---
## SECTION 10: MUD WINDOW CHART (Module 4 Addition)

### 10.1 What It Is

The Mud Window (also called the Drilling Margin chart or PP-FG chart) is the most important
single visualization in drilling engineering. It shows three depth-indexed curves:
  - Pore Pressure Gradient (PPG): minimum mud weight needed to prevent fluid influx
  - Fracture Gradient (FG): maximum mud weight before hydraulic fracturing of formation
  - Current Mud Weight: where you actually are right now

The SAFE ZONE (the "mud window") is the green band between PP and FG.
Too light = gas kick or well control incident.
Too heavy = lost circulation (mud fractures the formation).

Geomine has this. We must too — and do it better.

### 10.2 Data Sources for the Mud Window

For offset wells with drilled and documented logs:
  Pore Pressure:
    Method 1 (from DDR d-exponent): Eaton's method
      dc_exp = -log10(ROP / (RPM * WOB_normalized)) * log10(a/b)
      PP_gradient = OBG * (dc_exp_normal / dc_exp_observed)^n
      where n = 1.2 (Eaton exponent for compressional failure), OBG = overburden gradient

    Method 2 (from mud weight when kick occurred): Direct measurement
      If a kick occurred in an offset well at depth D, the mud weight at that time
      is a direct lower bound on pore pressure at D.

  Fracture Gradient:
    Hubbert-Willis method (simple, suitable for young, normally-faulted basins like Assam):
      FG = (PPG + overburden_gradient) / 2
    
    Eaton's method (more accurate):
      FG = OBG * v/(1-v) + PP * (1 - v/(1-v))
      where v = Poisson's ratio (from interval velocity logs)

  Upper Assam Baseline Values (from USGS Bulletin + published PETROTECH papers):
    Overburden gradient: 1.85 – 2.05 g/cc equivalent (increases with depth)
    Normal pore pressure: 1.03 – 1.08 g/cc (hydrostatic for Upper Assam)
    Tipam Sandstone PP: 0.90 – 1.02 g/cc (DEPLETED — BELOW hydrostatic in producing areas!)
    Barail Coal-Shale PP: 1.05 – 1.20 g/cc (near-normal to slightly elevated)
    Kopili Formation PP: 1.15 – 1.40 g/cc (OVERPRESSURED in some structural positions)

### 10.3 Why NWIS Mud Window is Better Than Geomine's

  Geomine shows a mud window. Source of data: unknown (likely manually configured).

  NWIS mud window is:
    1. EXTRACTED from offset DDRs — actual mud weights recorded at each depth.
    2. CORRELATED with xi ratio — mud weights from offset wells are mapped to xi positions
       and displayed at the xi-equivalent depth on the active well's chart.
    3. ANNOTATED with NPT context — each point where an offset well had mud-weight-related
       NPT (kick = too light, LC = too heavy) is shown as a colored dot on the mud window.
    4. DYNAMICALLY UPDATED — as new wells are ingested, the mud window expands with more data.

  This means a drilling engineer can see: "At xi=0.40 in Tipam Sandstone, offset wells used
  1.28-1.35 g/cc mud without losses. At xi=0.60, NHK-089 had losses at 1.36 g/cc — that's
  our fracture gradient upper bound here." This is genuine engineering intelligence.

### 10.4 Mud Window Display

  Chart type: Horizontal depth track (Y-axis = depth, X-axis = mud weight in g/cc or ppg)
  Curves:
    - Red dashed line: Pore Pressure Gradient (from offset d-exponent trends)
    - Orange dashed line: Fracture Gradient (from Eaton/Hubbert-Willis)
    - Green solid line: Current Mud Weight (from live DDR mud report channel)
    - Blue dots: Offset well actual mud weights at xi-equivalent depth
    - Red triangles: Kick events from offset wells at xi-equivalent depth
    - Orange triangles: Lost Circulation events from offset wells at xi-equivalent depth

  When current mud weight approaches either boundary:
    Within 0.05 g/cc of PP: AMBER "Mud weight approaching pore pressure — kick risk"
    Within 0.05 g/cc of FG: AMBER "Mud weight approaching fracture gradient — LC risk"
    Below PP: RED "MUD WEIGHT BELOW PORE PRESSURE — PREPARE FOR WELL CONTROL"
    Above FG: RED "MUD WEIGHT ABOVE FRACTURE GRADIENT — LOST CIRCULATION RISK"

---
---
## SECTION 11: ENGINEER DECISION WORKFLOW

### 11.1 Why This Matters (Geomine Has It — We Must Too)

Geomine has an "approve/reset/reject" workflow. This keeps the engineer in the decision loop
and prevents the system from being a fully autonomous agent making critical decisions.

This is important for TWO reasons:
  1. OISD and DGH regulations require human oversight for critical drilling decisions.
  2. Liability — if an AI recommendation leads to a blowout, the engineer must have
     acknowledged and approved the action. Without approval tracking, liability is unclear.

### 11.2 The Three-Action Workflow

For every AMBER or RED recommendation, the engineer sees THREE buttons:

  [ACKNOWLEDGE AND IMPLEMENT]
    - Engineer confirms they have read the recommendation and are implementing it.
    - System logs: {timestamp, alert_id, action: "ACKNOWLEDGE", user: "Eng_Singh",
                   note: "Reducing mud weight to 1.32 g/cc as recommended"}
    - Alert clears from the priority feed (moves to "Acknowledged" history).
    - Implementation countdown begins (system checks if action was effective after 30 min).

  [ACKNOWLEDGE AND OVERRIDE]
    - Engineer has read the recommendation but is choosing a different course of action.
    - System prompts: "Please log your alternative action:" (free text box, mandatory)
    - System logs: {timestamp, alert_id, action: "OVERRIDE", user: "Eng_Singh",
                   note: "Not reducing mud weight — using LCM pill approach instead"}
    - Alert marks as "OVERRIDDEN" in history.
    - System continues monitoring and re-alerts if situation worsens.

  [ESCALATE TO SENIOR ENGINEER]
    - Alert is flagged for immediate review by the senior engineer on shift.
    - An SMS/email notification fires to the registered shift supervisor.
    - The alert is marked "ESCALATED" and cannot be cleared without supervisor sign-off.
    - Use case: Junior engineer sees a kick indicator but is uncertain — escalates immediately.

### 11.3 Outcome Tracking (Our Advantage Over Geomine)

After an acknowledge action, NWIS monitors the post-action telemetry for 30 minutes.
It then automatically logs the OUTCOME:

  If LC alert was acknowledged and mud was reduced:
    - Did flow delta return to < 50 L/min? -> OUTCOME: EFFECTIVE
    - Did flow delta remain > 100 L/min? -> OUTCOME: PARTIALLY EFFECTIVE — re-alert
    - Did flow delta increase to > 250 L/min? -> OUTCOME: WORSENED — escalate immediately

  Outcome data feeds back into the recommendation engine:
    mitigation_effectiveness_score[mitigation_type][formation] += outcome_score
    This makes recommendations smarter over time — the system learns which mitigations
    actually worked in which formations for this specific OIL operation.

  This is a SELF-IMPROVING recommendation system. Geomine (as presented) does not have this.

---
---
## SECTION 12: NPT COST CALCULATOR

### 12.1 What It Calculates

When an NPT event occurs or is predicted, NWIS shows the financial cost in real time.
This is powerful in two ways:
  1. Engineers see the COST of delay — motivates faster, better decisions.
  2. Management can quantify ROI of the NWIS system itself.

### 12.2 Calculation Method

  OIL rig day rate for Upper Assam operations (from public OIL tender data):
    Operating rig: Rs 8-15 lakh per day (Rs 33,000 - 62,500 per hour)
    Spread cost (all associated services): Rs 20-35 lakh per day total
    
  NPT cost per hour: Rs 80,000 – Rs 1,45,000 per hour (full spread, conservative estimate)

  When an event fires:
    event_start_time = timestamp of first RED/AMBER alert
    current_time = now
    npt_hours = (current_time - event_start_time).total_seconds() / 3600

    npt_cost_current = npt_hours * NPT_COST_PER_HOUR  # Rs
    npt_cost_projected = npt_hours_historical_avg[event_type] * NPT_COST_PER_HOUR

  Historical NPT duration averages for Upper Assam (from USGS + published PETROTECH data):
    Lost Circulation (partial, cured with LCM): 2-8 hours average
    Lost Circulation (total, cement required): 24-72 hours average
    Stuck Pipe (freed with spotting pill): 8-24 hours average
    Stuck Pipe (sidetrack required): 7-21 days average (CATASTROPHIC)
    Gas Kick (controlled): 4-16 hours
    Fishing operation: 3-14 days average

  Display:
    +-------------------------------------------------+
    | NPT COST METER                                  |
    | Event: Partial Lost Circulation                 |
    | Started: 14:32 | Now: 14:58 | Duration: 26 min |
    | Running Cost: Rs 36,000                         |
    | Projected Total (avg LC 5 hrs): Rs 4.1 Lakh    |
    | Savings if resolved in next 30 min: Rs 2.8 Lakh |
    +-------------------------------------------------+

  On the home dashboard (always visible, even without an active event):
    "Historical NPT prevented by NWIS recommendations: 0 events | Rs 0 saved"
    -> This counter increments every time an acknowledged-and-effective alert closes.

---
---
## SECTION 13: DEPTH PROXIMITY RADAR (UI Feature)

### 13.1 What Geomine Has

A "depth proximity radar" — a radar/spider chart showing offset wells arranged in a circle
where distance from center = geological depth proximity to the current active well depth.

### 13.2 Our Implementation (Better)

  Instead of a simple radar, NWIS shows a 3D WELL CORRELATION PANEL:

  Y-axis: Depth in TVDSS (current active well depth centered)
  X-axis: Offset wells ranked by Omega score (left to right)
  Each column: A simplified lithology log of the offset well (formation-colored blocks)
  Current depth line: A horizontal orange line crossing all columns at the xi-equivalent depth

  This is called a "Stick Plot" or "Well Correlation Panel" in the industry.
  It shows, at a glance:
    - Which offset wells are in the same formation at the equivalent depth
    - Which have NPT events near the current horizon (shown as colored event markers)
    - How thick the formations are in each well (structural position effect)
    - Where the bit is in the overall geological sequence (zoom in/out)

  This is FAR more informative than Geomine's radar chart because:
    - It shows WHAT formation each well is in, not just distance
    - It shows NPT events in their geological context
    - It dynamically updates the orange correlation line as bit advances
    - It is the standard visual that subsurface geologists use in their daily work —
      OIL evaluators will immediately recognize it as professional quality

---
---
## SECTION 14: CSV AND JSON EXPORT

Geomine has CSV export of offset records. We must too.

  Exportable datasets:
    1. Offset well ranking (current): CSV with well name, distance, Omega score, NPT events
    2. NPT event history (for a selected well or all wells): CSV with depth, type, severity, mitigation
    3. Risk corridor projection: CSV with depth, LC risk, SP risk, kick risk at each 10m interval
    4. Alert history for this drilling session: JSON with timestamps, triggers, actions, outcomes
    5. Mud window data: CSV with depth, PP gradient, FG estimate, current mud weight

  API endpoints:
    GET /api/export/offset_ranking?well_id={id}&format=csv
    GET /api/export/npt_history?well_id={id}&format=csv
    GET /api/export/risk_corridor?well_id={id}&format=csv
    GET /api/export/alerts?session_id={id}&format=json
