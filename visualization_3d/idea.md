# NWIS 3D Visualization — Idea & Reference Document

This is the running source of truth for what the 3D visualization is
supposed to represent and how it should look/feel. Updated as the user adds
more direction — do not lose or contradict anything recorded here without
being told to.

## The core interaction concept (not 3 independent renders — one connected flow)

This is **not** three separate static scenes. It's one connected,
user-driven narrative where each scene is the "drill-down" result of an
action in the previous one:

1. **Scene 1 — Global Earth view.** A rotating globe showing well locations
   highlighted worldwide (every real Oil India Limited well location, not
   just Assam — sourced from real data, not invented). This is the entry
   point.
2. **User selects a radius** (the same "user-defined radius" control as
   Module 2's map) → the view transitions from the global globe into...
3. **Scene 2 — Assam terrain (detailed, realistic).** Only built in detail
   for the Assam region, because that's the only region we actually have
   real offset-well data for. Elsewhere on the globe, wells are shown as
   real, correctly-located markers on the Scene 1 globe, but do NOT get
   their own detailed terrain scene — only Assam does.
4. **User selects a well to compare** (an offset well) → the view
   transitions from the terrain surface down into...
5. **Scene 3 — Underground view.** Subsurface formations, wellbores, and
   the stratigraphic correlation between the active well and the selected
   offset well.

So the real information architecture is: **Scene 1 (global) → radius
selection → Scene 2 (Assam terrain) → well selection → Scene 3
(underground/correlation)**. Each transition is a camera move driven by a
real user choice, not an arbitrary cut.

## Visual reference: maplable.com

Referenced directly (`assets/frames/*.png`, extracted from the user's own
screen recordings of the site) rather than guessed. Confirmed real,
consistent style across all reference frames:

- **Not photorealistic satellite imagery.** A stylized DARK globe: muted
  grey/charcoal landmasses with subtle terrain shading, deep near-black
  navy ocean — not blue.
- **A thin, bright cyan/teal atmosphere rim glow** exactly at the horizon
  silhouette (a Fresnel-driven effect, bright right at the grazing edge,
  fading quickly).
- **Small glowing dot markers** (not large geometric shapes) scattered at
  real locations — mostly cyan, a few orange/red/yellow for
  variety/status. This is the correct reference for how well markers
  should look on the Scene 1 globe, not the oversized glowing cones the
  first draft used.
- **Thin curved great-circle arc lines** in bright cyan connecting distant
  points (a flight-path/data-link visual), plus some plain white/grey
  thinner connector lines.
- **A pulsing green dot** for an active/selected point — directly
  relevant to how our "active well" marker should behave.
- **Sparse white starfield** in the black space beyond the globe's
  silhouette.
- **Small circular white "pin" markers** with icons for points of
  interest, plus a small "+" crosshair marker style.
- Real place labels (city/country names) rendered directly on the globe
  surface at appropriate zoom levels.

**What this means technically:** the globe needs REAL, geographically
correct landmass/coastline data (the user has explicitly required
"location and land must be correct" so Assam and real offset wells can be
located accurately on it) — but stylized with a dark desaturated color
grade rather than rendered as photorealistic satellite texture. Real
geography + stylized dark shading + cyan Fresnel rim + glowing point
markers, not a literal photo-Earth.

## Scope correction from the original spec

The original 3-scene spec (Earth → Assam terrain → underground, with a
fixed 7-field-marker set: Upper Assam x3, Mumbai Offshore x2, Rajasthan x1,
KG Basin x1) was a **fixed cinematic sequence** with invented marker
counts/positions. The corrected, current understanding:

- Scene 1's well markers should be **real Oil India Limited well
  locations** researched from real sources, not an invented count per
  region.
- Only Assam gets a Scene 2 terrain build-out, because that's the only
  region with real offset-well data behind it (matches the rest of this
  project's real-data-only discipline — see `logger/04_STEP_BY_STEP_IMPLEMENTATION_LOG.md`).
  Other OIL regions are real markers on the Scene 1 globe only.
- The camera moves are **interaction-driven** (radius selection, well
  selection), not a fixed timeline the viewer just watches.

## Assets provided by the user

`assets/` contains the user's own reference screen recordings and
screenshots of maplable.com (`Screen Recording *.mp4`,
`Screenshot *.png`), and extracted frames under `assets/frames/` (pulled
via ffmpeg since video can't be read directly). These are the actual
visual reference — refer back to them, don't just rely on this written
description, when making material/shader decisions.

## Status log (append here as more direction comes in)

- 2026-09-29: Initial idea captured (this document). Scene 1 rebuild in
  progress to match the maplable.com dark-globe aesthetic with real
  landmass geography and real OIL well locations.
- 2026-09-29: Scene 1 v2 built and rendered (`scripts/scene1_earth.py`,
  `renders/scene1_v3_*.png`, `renders/scene1_v4_frame45.png`). Real bugs
  found and fixed via actual render inspection (not assumed correct from
  code):
  - Starfield: a fresh Blender ColorRamp's two endpoints are both fully
    opaque by default; the ramp had bright/dark reversed, clamping nearly
    the whole sky to white instead of black. Fixed.
  - Sun lamp: a hand-picked rotation euler didn't reliably aim the light at
    the globe (a Sun's direction is local -Z, independent of location).
    Fixed by computing the aim rotation properly. Given the reference's
    evenly-lit stylized look (not a hard day/night terminator), the globe
    now leans on material self-emission for readability rather than
    depending on the sun angle.
  - Atmosphere rim shell (the cyan Fresnel glow): its transparency mix used
    the ColorRamp's Alpha output, which is constant 1.0 by default -- this
    made the "atmosphere" shell fully opaque everywhere, rendering as a
    solid black disc hiding the entire Earth sphere except right at the
    true grazing edge. Fixed by keying transparency off the ramp's Color
    output instead, which actually varies with the Fresnel factor.
  - Earth texture orientation: real well markers are placed via
    `latlon_to_xyz()` (standard spherical convention), but the day/night
    textures were fed through `Generated` texture coordinates with default
    Flat projection, which does not produce a matching equirectangular
    mapping -- confirmed via a 5-point calibration-marker render (real
    continents rendered correctly, but Assam's marker landed over
    Greenland). A hand-derived atan2/asin UV from `Generated` also failed
    (heavy banding -- `Generated` isn't a clean unit-sphere direction
    vector for this mesh). Fixed by using the UV sphere's own built-in UV
    map (`TexCoord.UV`), which is a clean native equirectangular unwrap;
    re-calibration confirmed it lines up with `latlon_to_xyz()` with zero
    rotation offset needed.
  - Camera path: straight-line XYZ interpolation between the wide opening
    position and the close Assam position cut a chord that swung close
    past the surface mid-transition (frame 45 originally rendered as a
    near-ground-level flyover of Arctic Canada, not a smooth zoom). Fixed
    by slerping the camera's direction from the globe center across
    several keyframes while independently easing the radius inward, so the
    camera-to-surface distance never drops below a safe minimum until the
    final approach.
  - Real OIL locations now on the globe (field-cluster-level
    approximations, not survey-precise, labeled as such in the script):
    Assam/Arunachal cluster (Duliajan HQ, Nahorkatiya, Moran, Baghjan) as
    the warm/active markers, plus Rajasthan (Bhaghewala), Andaman Basin
    (Vijaypuram), KG Basin, Mahanadi Basin, and Kerala-Konkan as cyan
    markers -- verified by render that the Assam marker lands correctly at
    the real India/Myanmar/China border region near the Himalayas.
  - Remaining polish, not yet done: the reference's sparse bright starfield
    reads much more subtly here (current Voronoi stars are present but
    understated); no pulsing "active marker" animation or great-circle arc
    lines yet (both called out in the maplable.com reference above); no
    real place labels; full-quality Cycles render (512 samples/4K) not
    attempted, still only cheap preview-quality checks. Scene 2, Scene 3,
    and the actual connected/interactive radius-selection and
    well-selection triggers (as opposed to a fixed camera animation) are
    not started.
