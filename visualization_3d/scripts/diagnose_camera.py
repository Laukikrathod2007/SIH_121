import bpy, math

scene = bpy.context.scene
scene.frame_set(90)
bpy.context.view_layer.update()
cam = scene.camera
earth = bpy.data.objects.get("Earth")

cam_loc = cam.matrix_world.translation
earth_loc = earth.matrix_world.translation
dist_to_origin = math.sqrt(sum(c * c for c in cam_loc))
dist_to_earth_center = (cam_loc - earth_loc).length

print("DIAG_START")
print("camera raw .location:", tuple(cam.location))
print("camera world matrix translation:", tuple(cam_loc))
print("distance from world origin:", dist_to_origin)
print("distance from earth center:", dist_to_earth_center)
print("earth radius (approx from bound box):", max(earth.dimensions) / 2)
print("camera rotation_euler:", tuple(cam.rotation_euler))
print("camera constraints:", [(c.name, c.type, getattr(c, 'target', None)) for c in cam.constraints])
print("DIAG_END")
