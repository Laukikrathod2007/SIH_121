# NWIS 3D Visualization — Implementation Plan

A cinematic 3-scene Blender sequence (Earth → Assam terrain → underground
wellbores/formations), built via direct Python scripting through the
blender-mcp addon running locally on port 9876. This is a standalone visual
asset for presentation/demo purposes — it does not modify any of the actual
NWIS application code in `modules/` or `frontend/`.

## Connection method

No formal MCP tool for the local blender-mcp server (ahujasid/blender-mcp)
is registered in this Claude session, despite it running locally. Worked
around by talking to it directly: it's a plain JSON-over-TCP socket server
(`{"type": "<command>", "params": {...}}` → `{"status": ..., "result": ...}`),
so `scripts/blender_client.py` connects to `localhost:9876` and sends the
same commands the real MCP tool would, via `execute_blender_code` (runs
arbitrary Python inside the live Blender process — full `bpy`/`bmesh`
access, same as scripting directly in Blender's own console).

## Build order and rationale

Building and rendering all three scenes in one pass, blind, is a bad idea —
the spec has real geometric/material complexity per scene (terrain
subdivision, layered semi-transparent formation volumes, emission
materials, camera animation timing), and Cycles at 512 samples/4K is
expensive enough that iterating after a failed full render wastes real
time. Instead:

1. **Connectivity + capability check** — confirm the socket responds and
   `execute_blender_code` genuinely runs Python inside Blender (not just
   accepting the connection).
2. **Scene 1 (Earth globe) first, in isolation** — simplest scene
   geometrically (one UV sphere + texture + markers + camera move). Render
   a low-sample preview, confirm it's visually correct, before scaling up
   sample count.
3. **Scene 2 (Assam terrain)** — terrain generation, procedural elevation,
   river curve, wellhead cylinders. Preview-render, verify.
4. **Scene 3 (underground)** — the most complex: 5 semi-transparent
   stratified volumes, 4 emission wellbore tubes with per-well colors and
   angles, risk corridor box, stratigraphic tie-lines, labels. Preview
   first.
5. **Full-quality render pass** — once all three scenes are visually
   confirmed correct at preview quality, re-render each at the real spec
   (Cycles, 512 samples, 4K, 30fps) and assemble.

## Real constraint to flag honestly before the full render

512 samples at 4K in Cycles, across 450 total frames (90 + 180 + 240), is a
genuinely large compute job — likely many hours to a day+ depending on the
GPU actually available on this machine (unknown until the connectivity
check reports back `bpy.context` / render device info). Plan: get an actual
per-frame render-time measurement from a single test frame at full
settings before committing to a full unattended multi-hour render, so the
real time cost is known rather than assumed.

## Scene specifications (as given)

### Scene 1 — Earth Globe (3s, ~90 frames @30fps)
- UV sphere, 512 segments, 8K Earth texture
- India highlighted, orange emission `#FF6B35`
- 7 oil field markers as glowing cones: Upper Assam (red ×3), Mumbai
  Offshore (×2), Rajasthan (×1), KG Basin (×1)
- Camera: full-Earth → Assam region zoom
- Starfield background, sun lamp from upper-left

### Scene 2 — Assam Terrain (6s, ~180 frames)
- Terrain plane, 500×500 subdivisions, real Assam coordinate range
  (26.5–28°N, 94.5–96°E), 3× vertical exaggeration
- Brahmaputra river: blue reflective curve
- 3 fields: Nahorkatiya (12 wells), Moran (8 wells), Baghjan (5 wells)
- Wellheads: gold metal cylinders, 50m tall
- Active well NHK-412: red pulsing emission, 1.5× scale, labeled
- Camera: descend + orbit, then dive underground (transition into Scene 3)

### Scene 3 — Underground (8s, ~240 frames)
- Volume: 10km × 10km × 4000m depth, 5× vertical exaggeration
- 5 formation layers (name / depth range / color / opacity):
  1. Girujan Clay — 0–2200m — tan — 0.4
  2. Tipam Sandstone — 2200–2950m — sandy brown — 0.5, slight gold glow
  3. Barail Shale — 2950–3200m — dark gray — 0.6
  4. Kopili — 3200–3600m — olive — 0.5
  5. Disang — 3600–4000m — dark slate — 0.7
- 4 wellbores, emission tubes, 30cm diameter:
  - NHK-412: green `#00FF00`, 35° slant, bit at 2845m TVDSS (red pulsing sphere)
  - NHK-089: orange `#FFA500`, 2.3km NE, red warning triangle @2828m "Mud Loss 6.5hrs"
  - NHK-145: blue `#4169E1`, 1.5km SW, vertical
  - MOR-034: purple `#9370DB`, 1.8km SE, 45°, red marker "Severe Loss 24hrs"
- Red risk-corridor box, 0.15 opacity, 2820–2870m depth, 5km radius
- Yellow dashed stratigraphic tie-lines at ξ=0.30
- Gray wireframe grid, every 500m depth
- Scale bars, "5x Vertical Exaggeration" label
- All labels: well names, depths, incidents
- Camera: orbit around the cluster

### Render
Cycles, 512 samples, 4K, 30fps, 17s total (90+180+240 frames)

## Status

- [ ] Connectivity confirmed
- [ ] Scene 1 built + preview-rendered
- [ ] Scene 2 built + preview-rendered
- [ ] Scene 3 built + preview-rendered
- [ ] Full-quality render (pending time-cost measurement)
