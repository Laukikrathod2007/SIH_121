import bpy

mat = bpy.data.materials.get("EarthMaterial")
print("DIAG_START")
if mat is None:
    print("No EarthMaterial found")
else:
    nt = mat.node_tree
    print("Nodes:")
    for n in nt.nodes:
        print(f"  {n.name} ({n.bl_idname})")
    print("Links:")
    for l in nt.links:
        print(f"  {l.from_node.name}.{l.from_socket.name} -> {l.to_node.name}.{l.to_socket.name}")
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf:
        print("BSDF Emission Strength:", bsdf.inputs["Emission Strength"].default_value)
        print("BSDF Emission Color input is_linked:", bsdf.inputs["Emission Color"].is_linked)
        print("BSDF Base Color input is_linked:", bsdf.inputs["Base Color"].is_linked)

earth = bpy.data.objects.get("Earth")
print("Earth materials:", [m.name if m else None for m in earth.data.materials])
print("Earth material_slots:", [(s.material.name if s.material else None, s.link) for s in earth.material_slots])

view_layer = bpy.context.scene.view_layers[0]
print("Camera:", bpy.context.scene.camera.name if bpy.context.scene.camera else None)
print("View transform:", bpy.context.scene.view_settings.view_transform)
print("Look:", bpy.context.scene.view_settings.look)
print("Exposure:", bpy.context.scene.view_settings.exposure)
print("Gamma:", bpy.context.scene.view_settings.gamma)
print("DIAG_END")
