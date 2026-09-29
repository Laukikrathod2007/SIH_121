"""
Scene 1 -- Global Earth view, v2. Rebuilt to match the maplable.com
reference aesthetic (see assets/frames/*.png and idea.md), not a generic
photoreal Earth:
  - Real geography (8K Blue Marble-derived day map, real coastlines) --
    "location and land must be correct" per the user.
  - Stylized DARK color grade (desaturated, darkened) rather than a bright
    photo-Earth, matching the reference's charcoal-grey landmasses / near
    black ocean.
  - Thin bright cyan Fresnel atmosphere rim glow at the horizon.
  - Small glowing dot markers (not large cones) at REAL Oil India Limited
    operational locations across India, researched, not invented:
    Assam/Arunachal (Duliajan HQ + Nahorkatiya/Moran/Baghjan cluster),
    Rajasthan (Bhaghewala/Dandewala), Andaman Basin (Vijaypuram wells),
    KG Basin, Mahanadi Basin, Kerala-Konkan Basin.
  - Procedural starfield.
Run: blender --background --python scene1_earth.py
"""
import bpy, math, os, mathutils, random

PROJECT_DIR = r"C:\Users\LAUKIK\Desktop\SIH121\visualization_3d"
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")
OUT_BLEND = os.path.join(PROJECT_DIR, "scripts", "scene1_earth.blend")
EARTH_RADIUS = 6.371

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.render.resolution_x = 3840
scene.render.resolution_y = 2160
scene.frame_start = 1
scene.frame_end = 90
scene.render.fps = 30
scene.render.film_transparent = False
# AgX (Blender's default) crushes dark values hard, which flattened a
# self-illuminated dark-stylized globe to solid black; Standard keeps this
# UI-style render's midtones legible.
scene.view_settings.view_transform = 'Standard'


def latlon_to_xyz(lat_deg, lon_deg, r):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    x = r * math.cos(lat) * math.cos(lon)
    y = r * math.cos(lat) * math.sin(lon)
    z = r * math.sin(lat)
    return (x, y, z)


def point_quaternion(pos):
    """Rotation that points local +Z outward along pos (for cones/markers on the sphere surface)."""
    mag = math.sqrt(sum(c * c for c in pos))
    direction = mathutils.Vector((pos[0] / mag, pos[1] / mag, pos[2] / mag))
    return mathutils.Vector((0, 0, 1)).rotation_difference(direction)


# =============================================================================
# Earth sphere -- real texture, stylized dark grade, day/night blend
# =============================================================================
bpy.ops.mesh.primitive_uv_sphere_add(segments=512, ring_count=256, radius=EARTH_RADIUS, location=(0, 0, 0))
earth = bpy.context.active_object
earth.name = "Earth"
bpy.ops.object.shade_smooth()

mat = bpy.data.materials.new("EarthMaterial")
nt = mat.node_tree
nodes = nt.nodes
links = nt.links
nodes.clear()

out = nodes.new("ShaderNodeOutputMaterial")
out.location = (900, 0)

day_path = os.path.join(ASSETS_DIR, "8k_earth_daymap.jpg")
night_path = os.path.join(ASSETS_DIR, "2k_earth_nightmap.jpg")
DAYMAP_LOADED = os.path.exists(day_path)
NIGHTMAP_LOADED = os.path.exists(night_path)

tex_coord = nodes.new("ShaderNodeTexCoord")
tex_coord.location = (-1400, 0)

# Use the sphere's OWN UV map (a clean equirectangular unwrap that Blender
# generates for primitive_uv_sphere_add) rather than deriving UV by hand
# from "Generated" coordinates -- that manual atan2/asin approach produced
# heavy banding, meaning "Generated" isn't the clean unit-sphere direction
# vector it would need to be for that math. The UV map's own rotation
# offset relative to latlon_to_xyz()'s convention is solved empirically
# below (EARTH_U_OFFSET), via calibration-marker renders.
EARTH_U_OFFSET = 0.0  # solved via calibration render, see idea.md notes
u_offset_node = nodes.new("ShaderNodeVectorMath")
u_offset_node.operation = 'ADD'
u_offset_node.location = (-1150, 0)
u_offset_node.inputs[1].default_value = (EARTH_U_OFFSET, 0.0, 0.0)
links.new(tex_coord.outputs["UV"], u_offset_node.inputs[0])
earth_uv = u_offset_node

if DAYMAP_LOADED:
    day_tex = nodes.new("ShaderNodeTexImage")
    day_tex.image = bpy.data.images.load(day_path)
    day_tex.location = (-350, 250)
    links.new(earth_uv.outputs["Vector"], day_tex.inputs["Vector"])

    # Stylized dark grade: desaturate + darken the real day texture so it
    # reads as charcoal-grey landmass / near-black ocean (maplable.com
    # reference), not a bright photo-Earth. HSV node: drop saturation and
    # value, keep hue (so land/ocean contrast survives as a grey-scale
    # brightness difference).
    hsv = nodes.new("ShaderNodeHueSaturation")
    hsv.location = (-350, 200)
    hsv.inputs["Saturation"].default_value = 0.35
    hsv.inputs["Value"].default_value = 0.22
    links.new(day_tex.outputs["Color"], hsv.inputs["Color"])

    # Tint slightly toward navy/cyan (multiply by a cool dark blue) so the
    # "ocean" reads dark navy rather than neutral grey, matching reference.
    tint = nodes.new("ShaderNodeMixRGB")
    tint.location = (-150, 200)
    tint.blend_type = 'MULTIPLY'
    tint.inputs["Fac"].default_value = 0.5
    tint.inputs["Color2"].default_value = (0.55, 0.72, 1.0, 1.0)
    links.new(hsv.outputs["Color"], tint.inputs["Color1"])
    styled_color_output = tint.outputs["Color"]
else:
    fallback = nodes.new("ShaderNodeRGB")
    fallback.outputs[0].default_value = (0.12, 0.14, 0.18, 1.0)
    styled_color_output = fallback.outputs[0]

bsdf = nodes.new("ShaderNodeBsdfPrincipled")
bsdf.location = (300, 100)
bsdf.inputs["Roughness"].default_value = 0.75
links.new(styled_color_output, bsdf.inputs["Base Color"])

# Night-side city lights: use the real night map as a low-level emission so
# landmasses stay faintly readable even where the sun doesn't hit, closer to
# the reference's fairly-even global illumination than a hard day/night
# terminator would give.
if NIGHTMAP_LOADED:
    night_tex = nodes.new("ShaderNodeTexImage")
    night_tex.image = bpy.data.images.load(night_path)
    night_tex.location = (-350, -150)
    links.new(earth_uv.outputs["Vector"], night_tex.inputs["Vector"])
    night_boost = nodes.new("ShaderNodeHueSaturation")
    night_boost.location = (-350, -150)
    night_boost.inputs["Saturation"].default_value = 0.6
    night_boost.inputs["Value"].default_value = 1.2
    links.new(night_tex.outputs["Color"], night_boost.inputs["Color"])

# Also give the base color a small emission contribution so the globe
# doesn't rely purely on the sun lamp (reference has fairly uniform
# visibility across the whole visible hemisphere, not a hard terminator).
mix_emit = nodes.new("ShaderNodeMixRGB")
mix_emit.location = (-150, -350)
mix_emit.blend_type = 'ADD'
mix_emit.inputs["Fac"].default_value = 1.0
links.new(styled_color_output, mix_emit.inputs["Color1"])
if NIGHTMAP_LOADED:
    links.new(night_boost.outputs["Color"], mix_emit.inputs["Color2"])
    scale_node = nodes.new("ShaderNodeMixRGB")
else:
    mix_emit.inputs["Color2"].default_value = (0, 0, 0, 1)

links.new(mix_emit.outputs["Color"], bsdf.inputs["Emission Color"])
# Strong self-illumination is intentional: the maplable.com reference reads
# as an evenly-visible stylized globe, not a physically dark-sided render,
# so the globe should stay clearly readable independent of sun angle.
bsdf.inputs["Emission Strength"].default_value = 0.9

links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
earth.data.materials.append(mat)

# =============================================================================
# Atmosphere rim -- thin Fresnel-driven cyan glow shell, the single most
# recognizable element of the maplable.com reference.
# =============================================================================
bpy.ops.mesh.primitive_uv_sphere_add(segments=256, ring_count=128, radius=EARTH_RADIUS * 1.015, location=(0, 0, 0))
atmo = bpy.context.active_object
atmo.name = "AtmosphereRim"
bpy.ops.object.shade_smooth()

atmo_mat = bpy.data.materials.new("AtmosphereRim")
atmo_mat.blend_method = 'BLEND'
ant = atmo_mat.node_tree
an = ant.nodes
al = ant.links
an.clear()
a_out = an.new("ShaderNodeOutputMaterial")
a_out.location = (600, 0)

fresnel = an.new("ShaderNodeFresnel")
fresnel.inputs["IOR"].default_value = 1.25
fresnel.location = (-300, 0)

# Sharpen the Fresnel falloff so the glow is a thin rim, not a broad haze.
ramp = an.new("ShaderNodeValToRGB")
ramp.location = (-100, 0)
ramp.color_ramp.elements[0].position = 0.55
ramp.color_ramp.elements[1].position = 0.92
al.new(fresnel.outputs["Fac"], ramp.inputs["Fac"])

atmo_emit = an.new("ShaderNodeEmission")
atmo_emit.location = (150, 0)
atmo_emit.inputs["Color"].default_value = (0.25, 0.95, 1.0, 1.0)  # bright cyan
atmo_emit.inputs["Strength"].default_value = 6.0
al.new(ramp.outputs["Color"], atmo_emit.inputs["Strength"])

transp = an.new("ShaderNodeBsdfTransparent")
transp.location = (150, -150)
mix_shader = an.new("ShaderNodeMixShader")
mix_shader.location = (350, 0)
# NOTE: a fresh ColorRamp's two endpoints are both fully opaque (alpha=1)
# by default, so its "Alpha" output is a constant 1.0 regardless of Fresnel
# -- that silently made this shell 100% opaque emission everywhere (black
# in the disc center, since only "Color"/luminance varied), hiding the
# whole Earth sphere behind a black disc with only the true edge glowing.
# Key transparency off "Color" (which does vary 0->1) instead.
al.new(ramp.outputs["Color"], mix_shader.inputs["Fac"])
al.new(transp.outputs["BSDF"], mix_shader.inputs[1])
al.new(atmo_emit.outputs["Emission"], mix_shader.inputs[2])
al.new(mix_shader.outputs["Shader"], a_out.inputs["Surface"])
atmo.data.materials.append(atmo_mat)

# =============================================================================
# Real Oil India Limited operational locations -- researched, not invented.
# Coordinates are field-cluster-level approximations (public well-level
# coordinates aren't published), explicitly labeled as such rather than
# presented as survey-precise.
# =============================================================================
oil_locations = [
    # (label, lat, lon, is_assam_cluster)
    ("Duliajan_HQ",        27.3667, 95.3333, True),
    ("Nahorkatiya",        27.2167, 95.3333, True),
    ("Moran",               27.2667, 95.1667, True),
    ("Baghjan",             27.5000, 95.4000, True),
    ("Rajasthan_Bhaghewala", 27.9000, 70.4000, False),
    ("Andaman_Vijaypuram",  11.5000, 92.7000, False),
    ("KG_Basin_Offshore",   16.0000, 82.3000, False),
    ("Mahanadi_Basin",      20.0000, 86.8000, False),
    ("Kerala_Konkan",       12.5000, 74.5000, False),
]

marker_objs = []
for name, lat, lon, is_assam in oil_locations:
    pos = latlon_to_xyz(lat, lon, EARTH_RADIUS * 1.006)
    radius = 0.045 if is_assam else 0.06
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=radius, location=pos)
    dot = bpy.context.active_object
    dot.name = f"Well_{name}"
    bpy.ops.object.shade_smooth()

    dmat = bpy.data.materials.new(f"WellGlow_{name}")
    dnt = dmat.node_tree
    dn = dnt.nodes
    dn.clear()
    d_em = dn.new("ShaderNodeEmission")
    color = (1.0, 0.35, 0.2, 1.0) if is_assam else (0.25, 0.95, 1.0, 1.0)  # active Assam cluster = warm, rest = cyan like reference
    d_em.inputs["Color"].default_value = color
    d_em.inputs["Strength"].default_value = 8.0 if is_assam else 5.0
    d_out = dn.new("ShaderNodeOutputMaterial")
    dnt.links.new(d_em.outputs["Emission"], d_out.inputs["Surface"])
    dot.data.materials.append(dmat)
    marker_objs.append(dot)

# =============================================================================
# Starfield -- procedural, via the World shader (cheap, no external assets).
# =============================================================================
world = bpy.data.worlds.new("StarWorld")
scene.world = world
wn_tree = world.node_tree
wn = wn_tree.nodes
wl = wn_tree.links
wn.clear()

w_coord = wn.new("ShaderNodeTexCoord")
w_noise = wn.new("ShaderNodeTexVoronoi")
w_noise.inputs["Scale"].default_value = 400.0
w_noise.voronoi_dimensions = '3D'
wl.new(w_coord.outputs["Generated"], w_noise.inputs["Vector"])

w_ramp = wn.new("ShaderNodeValToRGB")
# Voronoi "Distance" is near 0 only exactly AT a feature point and larger
# everywhere else; ColorRamp clamps out-of-range values to the nearest
# endpoint, so the endpoint order matters: white must sit at distance=0
# (the star point itself) and black at the (much more common) far side, or
# almost the entire sky clamps to the far endpoint's color.
w_ramp.color_ramp.elements[0].position = 0.0
w_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
w_ramp.color_ramp.elements[1].position = 0.02
w_ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
wl.new(w_noise.outputs["Distance"], w_ramp.inputs["Fac"])

w_bg_base = wn.new("ShaderNodeBackground")
w_bg_base.inputs["Color"].default_value = (0.008, 0.01, 0.02, 1.0)
w_bg_base.inputs["Strength"].default_value = 1.0

w_bg_stars = wn.new("ShaderNodeBackground")
w_bg_stars.inputs["Strength"].default_value = 3.0
wl.new(w_ramp.outputs["Color"], w_bg_stars.inputs["Color"])

w_add = wn.new("ShaderNodeAddShader")
wl.new(w_bg_base.outputs["Background"], w_add.inputs[0])
wl.new(w_bg_stars.outputs["Background"], w_add.inputs[1])

w_out = wn.new("ShaderNodeOutputWorld")
wl.new(w_add.outputs["Shader"], w_out.inputs["Surface"])

# =============================================================================
# Sun lamp
# =============================================================================
SUN_POS = mathutils.Vector((-10, 8, 10))
bpy.ops.object.light_add(type='SUN', location=SUN_POS)
sun = bpy.context.active_object
sun.data.energy = 3.5
# A Sun lamp's direction is its local -Z axis, independent of location, so a
# hand-picked euler doesn't reliably aim it at the globe. Compute the
# rotation that actually points -Z from the sun position toward the origin.
sun_direction = (mathutils.Vector((0, 0, 0)) - SUN_POS).normalized()
sun.rotation_euler = sun_direction.to_track_quat('-Z', 'Y').to_euler()

# =============================================================================
# Camera -- full Earth -> Assam cluster zoom
# =============================================================================
assam_pos = latlon_to_xyz(27.35, 95.35, EARTH_RADIUS)
ZOOM_MULT = 3.4
close_pos = tuple(c * ZOOM_MULT for c in assam_pos)

start_pos = mathutils.Vector((0, -28, 14))
end_pos = mathutils.Vector(close_pos)
start_radius, start_dir = start_pos.length, start_pos.normalized()
end_radius, end_dir = end_pos.length, end_pos.normalized()

bpy.ops.object.camera_add(location=start_pos)
cam = bpy.context.active_object
cam.name = "MainCamera"
scene.camera = cam
constraint = cam.constraints.new(type='TRACK_TO')
constraint.target = earth
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'

bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
# Straight-line XYZ interpolation between the wide start point and the
# close Assam point cuts a chord that swings close past the surface
# mid-transition (confirmed by rendering frame 45 -- it grazed Arctic
# Canada at near-ground level). Instead, slerp the camera's DIRECTION from
# the globe center across several keyframes while independently easing the
# radius inward, so distance-to-surface never drops below the safer of the
# two endpoint distances until the final approach.
FRAME_COUNT = 8
for i in range(FRAME_COUNT):
    t = i / (FRAME_COUNT - 1)
    frame = round(1 + t * (90 - 1))
    direction = start_dir.slerp(end_dir, t).normalized()
    radius = start_radius + (end_radius - start_radius) * (t ** 3)  # ease-in: stays wide, drops late
    cam.location = direction * radius
    cam.keyframe_insert(data_path="location", frame=frame)

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

print("SCENE1_RESULT_START")
print({
    "daymap_loaded": DAYMAP_LOADED,
    "nightmap_loaded": NIGHTMAP_LOADED,
    "objects_created": len(bpy.data.objects),
    "markers_created": len(marker_objs),
    "saved_to": OUT_BLEND,
})
print("SCENE1_RESULT_END")
