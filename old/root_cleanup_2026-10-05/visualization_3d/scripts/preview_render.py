"""Quick low-sample preview render of a saved .blend file's current frame,
so it can be visually inspected before committing to a full-quality render.
Usage: blender --background <file>.blend --python preview_render.py -- <frame> <out.png>
"""
import bpy
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
frame = int(argv[0]) if len(argv) > 0 else bpy.context.scene.frame_start
out_path = argv[1] if len(argv) > 1 else "/tmp/preview.png"

scene = bpy.context.scene
scene.frame_set(frame)
scene.cycles.samples = 32
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.filepath = out_path
scene.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
print(f"PREVIEW_SAVED:{out_path}")
