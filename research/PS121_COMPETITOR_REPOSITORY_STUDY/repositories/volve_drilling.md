# Competitor / Domain Dataset Audit: volve-drilling & SPWLA Volve

## 1. Repository Metadata
- **Repository**: `volve-drilling` / `spwla_volve`
- **URL**: `https://github.com/f0nzie/volve-drilling.git` & `https://github.com/andymcdgeo/spwla_volve.git`
- **Owner**: f0nzie / andymcdgeo (Equinor Open Data Release)
- **Project**: Volve Field Open Drilling & Well Log Benchmark
- **Category**: Well Data / WITSML Benchmark
- **Relevance**: High (Primary public ground-truth dataset used across drilling ML benchmarks)
- **Primary Content**: 24 wells (`15/9-F-1` through `15/9-F-15D`), WITSML XML files, Well Picks (`Well_picks_Volve_v1.dat`), LAS/DLIS logs, and Jupyter notebooks.

---

## 2. Dataset & Technical Structure
```
[Volve Benchmark Repository]
   ├── WITSML XML Records (`witsml/Norway-Statoil-NO 15_$47$_9-F-4/`)
   │     ├── Wellbore trajectory surveys (MD, Inclination, Azimuth)
   │     ├── Time-indexed drilling parameters (ROP, WOB, RPM, Torque, SPP)
   │     └── Mud log records & lithology descriptions
   ├── Well Formation Tops (`Well_picks_Volve_v1.dat`)
   │     └── Stratigraphic marker depths (Hordaland, Rogaland, Balder, Sele, Lista, Shetland, Chalk, Draupne, Hugin)
   └── Log Curves (SPWLA Volve LAS files: GR, NPHI, RHOB, DT, RT)
```

---

## 3. Verified Capabilities & Domain Utility
- **Standard Reference for Well Synchronization**: Contains 24 closely spaced offset wells with complex 3D trajectories (s-shape, J-shape, horizontal), providing the ideal benchmark for testing minimum curvature trajectory interpolation and stratigraphic thickness normalization.
- **WITSML Schema Ground Truth**: Provides standard WITSML 1.3.1 / 1.4.1.1 XML structures used by real rig-site data acquisition systems.

---

## 4. Key Takeaways for PS 121
- Competitors that use the Volve dataset often only parse the Alpaca text summaries (`bengsoon/volve_alpaca`) rather than utilizing the rich underlying 3D directional surveys and log curves.
- PS 121 can leverage this standard WITSML structure alongside OIL Assam-Arakan field data to build an industry-standard telemetry ingestion and trajectory synchronization engine.
