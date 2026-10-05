"""Build original, low-poly-but-detailed GLB wellsite visualization assets.

These assets are representational engineering geometry, not depictions of
equipment documented at any specific well. All dimensions are display scale.
Run: python scripts/build_surface_wellhead.py
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "models"
MATERIALS = [
    {"name": "Galvanized structural steel", "pbrMetallicRoughness": {"baseColorFactor": [0.47, 0.54, 0.55, 1], "metallicFactor": 0.72, "roughnessFactor": 0.34}},
    {"name": "Graphite equipment steel", "pbrMetallicRoughness": {"baseColorFactor": [0.13, 0.18, 0.20, 1], "metallicFactor": 0.68, "roughnessFactor": 0.4}},
    {"name": "Safety orange coating", "pbrMetallicRoughness": {"baseColorFactor": [0.91, 0.39, 0.12, 1], "metallicFactor": 0.24, "roughnessFactor": 0.48}},
    {"name": "Concrete pad", "pbrMetallicRoughness": {"baseColorFactor": [0.38, 0.42, 0.41, 1], "metallicFactor": 0.05, "roughnessFactor": 0.86}},
    {"name": "Painted off-white", "pbrMetallicRoughness": {"baseColorFactor": [0.73, 0.76, 0.73, 1], "metallicFactor": 0.2, "roughnessFactor": 0.52}},
]


class Model:
    def __init__(self):
        self.groups: list[list[tuple[float, float, float]]] = [[] for _ in MATERIALS]

    def triangle(self, mat: int, a, b, c):
        ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
        vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
        normal = (uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx)
        length = math.sqrt(sum(n*n for n in normal)) or 1
        normal = tuple(n/length for n in normal)
        for point in (a, b, c):
            self.groups[mat].append(tuple(point))
            self.groups[mat].append(normal)

    def quad(self, mat: int, a, b, c, d):
        self.triangle(mat, a, b, c)
        self.triangle(mat, a, c, d)

    def box(self, mat: int, low, high):
        x0, y0, z0 = low
        x1, y1, z1 = high
        faces = [
            ((x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0)),
            ((x1,y0,z1),(x1,y0,z0),(x1,y1,z0),(x1,y1,z1)),
            ((x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)),
            ((x1,y0,z0),(x0,y0,z0),(x0,y1,z0),(x1,y1,z0)),
            ((x0,y1,z1),(x1,y1,z1),(x1,y1,z0),(x0,y1,z0)),
            ((x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)),
        ]
        for face in faces:
            self.quad(mat, *face)

    def cylinder(self, mat: int, start, end, radius: float, sides: int = 12):
        dx, dy, dz = end[0]-start[0], end[1]-start[1], end[2]-start[2]
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length == 0:
            return
        axis = (dx/length, dy/length, dz/length)
        helper = (0, 0, 1) if abs(axis[1]) > 0.92 else (0, 1, 0)
        u = (axis[1]*helper[2]-axis[2]*helper[1], axis[2]*helper[0]-axis[0]*helper[2], axis[0]*helper[1]-axis[1]*helper[0])
        ul = math.sqrt(sum(v*v for v in u)) or 1
        u = tuple(v/ul for v in u)
        v = (axis[1]*u[2]-axis[2]*u[1], axis[2]*u[0]-axis[0]*u[2], axis[0]*u[1]-axis[1]*u[0])
        ring_a, ring_b = [], []
        for i in range(sides):
            angle = 2*math.pi*i/sides
            offset = tuple(radius*(math.cos(angle)*u[k] + math.sin(angle)*v[k]) for k in range(3))
            ring_a.append(tuple(start[k]+offset[k] for k in range(3)))
            ring_b.append(tuple(end[k]+offset[k] for k in range(3)))
        for i in range(sides):
            j = (i+1) % sides
            self.quad(mat, ring_a[i], ring_a[j], ring_b[j], ring_b[i])
            self.triangle(mat, start, ring_a[j], ring_a[i])
            self.triangle(mat, end, ring_b[i], ring_b[j])

    def beam(self, a, b, radius=0.06, mat=0):
        self.cylinder(mat, a, b, radius, 8)

    def wellhead(self, detailed: bool):
        # The same centered tree anchors the surface interpretation and local
        # subsurface trajectory; offset tiers retain identical wellhead origin.
        self.box(3, (-1.3, -0.28, -1.3), (1.3, 0.02, 1.3))
        self.box(1, (-0.6, 0.02, -0.6), (0.6, 0.32, 0.6))
        for y, radius, height, mat in [(0.32, .48, .58, 0), (.91, .34, .28, 1), (1.20, .52, .16, 2), (1.37, .29, .62, 0), (2.00, .42, .16, 2), (2.16, .24, .58, 1), (2.76, .38, .16, 2)]:
            self.cylinder(mat, (0,y,0), (0,y+height,0), radius, 16)
            # Machined flange bolts provide readable scale cues at field zoom.
            if y in (.32, 1.37, 2.16):
                bolt_r = radius * .78
                for i in range(8):
                    a = 2 * math.pi * i / 8
                    x, z = bolt_r * math.cos(a), bolt_r * math.sin(a)
                    self.cylinder(4, (x,y+height*.38,z), (x,y+height*.66,z), .045, 6)
        for side in (-1, 1):
            self.beam((side*.26,1.52,0),(side*1.28,1.52,0),.15,1)
            self.box(2,(side*1.18-.12,1.36,-.3),(side*1.48+.12,1.68,.3))
            self.beam((side*.25,2.34,0),(side*.88,2.34,0),.09,0)
        self.cylinder(0,(0,2.92,0),(0,4.25,0),.12,12)
        if not detailed:
            return
        # Flowline and instrumentation stubs belong to the representational
        # assembly and are not claims about measured/installed equipment.
        for side in (-1, 1):
            self.beam((side*.32,2.47,.08),(side*1.72,2.47,.08),.075,0)
            self.box(1,(side*1.55-.20,2.27,-.18),(side*1.98,2.68,.28))
        self.box(1,(-2.8,.02,-2.6),(2.8,.15,2.6))
        self.box(4,(-2.55,.15,-2.34),(2.55,.28,2.34))
        # Four-valve manifold and short pipework around the tree.
        for x in (-1.85,1.85):
            self.beam((x,.30,-1.2),(x,.30,1.2),.09,1)
            for z in (-.9,0,.9):
                self.cylinder(2,(x,.30,z),(x,.62,z),.065,8)
        for y in (.64,1.26,2.08,2.85):
            self.cylinder(1,(0,y,-.78),(0,y,.78),.055,8)

    def active_rig(self):
        self.wellhead(True)
        # Four-legged land derrick with tapered mast, structural tiers and
        # alternating diagonal cross bracing.
        base_y, top_y = .28, 29.0
        base = [(-3.5,base_y,-3.5),(3.5,base_y,-3.5),(3.5,base_y,3.5),(-3.5,base_y,3.5)]
        top = [(-1.1,top_y,-1.1),(1.1,top_y,-1.1),(1.1,top_y,1.1),(-1.1,top_y,1.1)]
        for i in range(4):
            self.beam(base[i],top[i],.15,0)
            self.beam((base[i][0]*.84,.3,base[i][2]*.84),base[i],.18,2)
        levels = [4.3,8.3,12.3,16.3,20.3,24.3,27.2]
        for n,y in enumerate(levels):
            t=(y-base_y)/(top_y-base_y)
            corners=[(base[i][0]*(1-t)+top[i][0]*t,y,base[i][2]*(1-t)+top[i][2]*t) for i in range(4)]
            for i in range(4):
                self.beam(corners[i],corners[(i+1)%4],.085,1)
                if n < len(levels)-1:
                    yn=levels[n+1]; tn=(yn-base_y)/(top_y-base_y)
                    upper=[(base[j][0]*(1-tn)+top[j][0]*tn,yn,base[j][2]*(1-tn)+top[j][2]*tn) for j in range(4)]
                    self.beam(corners[i],upper[(i+1)%4] if n%2 else upper[i],.06,0)
        for i in range(4):
            self.beam(top[i],top[(i+1)%4],.11,0)
        # Crown block, mast cap, traveling block and top-drive assembly.
        self.box(1,(-1.0,28.8,-1.0),(1.0,29.55,1.0))
        self.box(2,(-1.25,29.55,-1.25),(1.25,29.82,1.25))
        self.box(1,(-.72,21.0,-.72),(.72,22.8,.72))
        self.box(4,(-1.12,20.45,-1.12),(1.12,20.85,1.12))
        self.cylinder(0,(0,.05,0),(0,20.5,0),.10,12)
        # Pipe rack and a short visible stand of drill pipe.
        for z in (-1.2,-.6,0,.6,1.2):
            self.cylinder(0,(1.72,.5,z),(1.72,5.5,z),.045,8)
        # Raised drill floor/substructure with support columns and perimeter rail.
        self.box(1,(-5.2,4.0,-4.7),(5.2,4.35,4.7))
        self.box(4,(-4.85,4.35,-4.35),(4.85,4.52,4.35))
        for x in (-4.5,-2.25,2.25,4.5):
            for z in (-3.7,3.7): self.beam((x,.3,z),(x,4.0,z),.10,1)
        for z in (-4.35,4.35):
            self.beam((-4.8,5.1,z),(4.8,5.1,z),.045,2)
            for x in (-4.8,4.8): self.beam((x,4.35,z),(x,5.1,z),.04,0)
        # Drawworks and power/control cabins, at ground scale on the pad.
        self.box(1,(4.3,.3,-2.5),(7.8,2.5,1.1))
        self.box(4,(4.55,2.5,-2.25),(7.4,3.7,.85))
        self.box(1,(-8.7,.3,-3.6),(-5.2,2.1,-.4))
        self.box(4,(-8.45,2.1,-3.35),(-5.45,3.6,-.65))
        # Two low profile fluid tanks and connecting surface lines.
        for z in (-6.8,-5.2):
            self.box(1,(-4.5,.25,z),(3.6,1.5,z+1.0))
            for x in (-3.8,-1.6,.6,2.8): self.beam((x,1.5,z+.5),(x,1.72,z+.5),.035,0)
        self.beam((3.6,.55,-5.7),(5.2,.55,-2.0),.08,0)
        # Access stairs: stringers and regular treads, kept small at field zoom.
        for side in (-1,1):
            x=side*4.25
            self.beam((x,.3,4.8),(x,3.8,6.8),.09,1)
            self.beam((x+side*.7,.3,4.8),(x+side*.7,3.8,6.8),.09,1)
            for n in range(9):
                y=.45+n*.35; z=4.9+n*.20
                self.beam((x,y,z),(x+side*.7,y,z),.05,2)
        # Safety rails, mast floodlight arms and guyed support cues.
        for z in (-3.9,3.9):
            for y in (4.72,5.0): self.beam((-4.5,y,z),(4.5,y,z),.035,2 if y==4.72 else 0)
        for x in (-3.3,3.3):
            self.beam((x,5.0,-3.5),(x,5.0,3.5),.035,0)
        for x in (-2.9,2.9):
            self.beam((x,27.6,-3.6),(x,27.6,3.6),.045,1)
            for z in (-3.6,3.6): self.box(2,(x-.12,27.4,z-.12),(x+.12,27.9,z+.12))

    def offshore_rig(self):
        """Illustrative offshore drilling unit; not an as-built platform."""
        # Compact deck panels leave a central opening for the wellhead.
        self.box(1,(-6.4,.0,-6.0),(-1.0,.48,6.0))
        self.box(1,(1.0,.0,-6.0),(6.4,.48,6.0))
        self.box(1,(-1.0,.0,-6.0),(1.0,.48,-1.0))
        self.box(1,(-1.0,.0,1.0),(1.0,.48,6.0))
        # Short support legs terminate at the sea-surface datum. They are a
        # visual support cue and do not encode water depth or seabed location.
        for x in (-5.0,5.0):
            for z in (-4.5,4.5):
                self.box(0,(x-.34,-2.1,z-.34),(x+.34,.05,z+.34))
                self.beam((x-.34,-1.45,z),(x+.34,.1,z),.08,2)
                self.beam((x+.34,-1.45,z),(x-.34,.1,z),.08,0)
        # Derrick over the verified wellhead anchor. Geometry is intentionally
        # representational and not a claim about the installed offshore rig.
        base_y, top_y = .55, 24.0
        base=[(-2.45,base_y,-2.45),(2.45,base_y,-2.45),(2.45,base_y,2.45),(-2.45,base_y,2.45)]
        top=[(-.78,top_y,-.78),(.78,top_y,-.78),(.78,top_y,.78),(-.78,top_y,.78)]
        levels=[4.0,7.5,11.0,14.5,18.0,21.5]
        for i in range(4): self.beam(base[i],top[i],.13,0)
        for n,y in enumerate(levels):
            t=(y-base_y)/(top_y-base_y)
            corners=[tuple(base[i][k]*(1-t)+top[i][k]*t for k in range(3)) for i in range(4)]
            corners=[(p[0],y,p[2]) for p in corners]
            for i in range(4):
                self.beam(corners[i],corners[(i+1)%4],.075,1)
                if n < len(levels)-1:
                    yn=levels[n+1]; tn=(yn-base_y)/(top_y-base_y)
                    upper=[(base[j][0]*(1-tn)+top[j][0]*tn,yn,base[j][2]*(1-tn)+top[j][2]*tn) for j in range(4)]
                    self.beam(corners[i],upper[(i+1)%4] if n%2 else upper[i],.052,0)
        for i in range(4): self.beam(top[i],top[(i+1)%4],.1,0)
        self.box(1,(-.8,23.8,-.8),(.8,24.4,.8))
        self.box(2,(-1.0,24.4,-1.0),(1.0,24.65,1.0))
        # Drilling floor, pipe stands, compact control cabin and perimeter rails.
        self.box(4,(-3.4,4.4,-3.1),(3.4,4.62,3.1))
        self.box(1,(3.2,.5,-2.4),(5.4,2.5,1.4))
        self.box(4,(3.4,2.5,-2.2),(5.2,3.5,1.2))
        for z in (-5.5,5.5):
            self.beam((-6.0,.85,z),(6.0,.85,z),.045,2)
            for x in (-6.0,6.0): self.beam((x,.48,z),(x,.85,z),.04,0)
            # Intermediate stanchions and a second handrail make the deck
            # perimeter read as industrial structure at close zoom.
            for x in (-4.5,-3.0,-1.5,0,1.5,3.0,4.5):
                self.beam((x,.48,z),(x,.88,z),.035,0)
            self.beam((-6.0,.68,z),(6.0,.68,z),.028,4)
        for z in (-1.5,-.75,0,.75,1.5):
            self.cylinder(0,(2.0,.55,z),(2.0,4.1,z),.035,8)
        # Modular topside plant: separator skids, pipe runs, and compact
        # machinery. These are representational shapes, not asset inventory.
        self.box(1,(-5.8,.5,-2.4),(-3.2,2.3,-.5))
        for z in (-2.1,-1.7,-1.3,-.9):
            self.beam((-5.45,2.34,z),(-3.55,2.34,z),.045,0)
        for x,z in ((-2.8,-4.8),(-.9,-4.8),(4.5,-4.8),(-2.8,4.8),(4.4,4.8)):
            self.box(1,(x-.72,.5,z-.55),(x+.72,2.25,z+.55))
            self.box(4,(x-.55,2.25,z-.4),(x+.55,2.38,z+.4))
            self.beam((x-.46,2.38,z-.3),(x+.46,2.38,z-.3),.035,2)
        # Crane pedestal, lattice tower, braced boom, pendant and hook.
        self.box(1,(-5.7,.5,2.0),(-4.6,1.5,3.1))
        crane_base=(-5.15,1.5,2.55); crane_top=(-5.15,7.8,2.55)
        self.beam(crane_base,crane_top,.13,1)
        for y in (2.2,3.4,4.6,5.8,7.0,7.8):
            self.beam((-5.55,y,2.55),(-4.75,y,2.55),.05,0)
        for index,y in enumerate((2.2,3.4,4.6,5.8,7.0)):
            next_y=y+1.2
            self.beam((-5.55,y,2.55),(-4.75,next_y,2.55),.038,2)
            self.beam((-4.75,y,2.55),(-5.55,next_y,2.55),.038,0)
        self.beam(crane_top,(-1.15,7.8,2.55),.11,2)
        self.beam((-5.15,7.8,2.55),(-1.15,7.8,2.55),.07,1)
        self.beam((-1.15,7.8,2.55),(-1.15,5.4,2.55),.035,0)
        self.beam((-1.15,5.4,2.55),(-1.36,5.4,2.55),.055,2)
        # Compact helideck on a raised cantilever: a useful scale cue rather
        # than a claim about the actual platform layout at this coordinate.
        self.beam((4.8,2.0,4.2),(6.7,2.0,5.8),.15,1)
        self.box(4,(5.4,2.0,4.6),(9.4,2.32,8.6))
        self.beam((5.55,2.34,4.75),(9.25,2.34,8.45),.045,2)
        self.beam((9.25,2.34,4.75),(5.55,2.34,8.45),.045,2)
        self.beam((5.4,2.4,4.6),(9.4,2.4,4.6),.035,0)
        self.beam((9.4,2.4,4.6),(9.4,2.4,8.6),.035,0)
        self.beam((9.4,2.4,8.6),(5.4,2.4,8.6),.035,0)
        self.beam((5.4,2.4,8.6),(5.4,2.4,4.6),.035,0)

    def write(self, path: Path, name: str):
        binary=bytearray(); views=[]; accessors=[]; meshes=[]; nodes=[]
        def append(payload: bytes,target: int):
            while len(binary)%4: binary.append(0)
            offset=len(binary); binary.extend(payload)
            views.append({"buffer":0,"byteOffset":offset,"byteLength":len(payload),"target":target})
            return len(views)-1
        triangles=0
        for mi,vertices in enumerate(self.groups):
            if not vertices: continue
            positions=[v for i,v in enumerate(vertices) if i%2==0]
            normals=[v for i,v in enumerate(vertices) if i%2==1]
            flat_pos=[c for p in positions for c in p]; flat_norm=[c for n in normals for c in n]
            pv=append(struct.pack(f"{len(flat_pos)}f",*flat_pos),34962)
            nv=append(struct.pack(f"{len(flat_norm)}f",*flat_norm),34962)
            indices=list(range(len(positions))); iv=append(struct.pack(f"{len(indices)}I",*indices),34963)
            pa=len(accessors); accessors.append({"bufferView":pv,"componentType":5126,"count":len(positions),"type":"VEC3","min":[min(p[a] for p in positions) for a in range(3)],"max":[max(p[a] for p in positions) for a in range(3)]})
            na=len(accessors); accessors.append({"bufferView":nv,"componentType":5126,"count":len(normals),"type":"VEC3"})
            ia=len(accessors); accessors.append({"bufferView":iv,"componentType":5125,"count":len(indices),"type":"SCALAR"})
            meshes.append({"name":f"{name} · material {mi}","primitives":[{"attributes":{"POSITION":pa,"NORMAL":na},"indices":ia,"material":mi,"mode":4}]})
            nodes.append({"mesh":len(meshes)-1}); triangles += len(indices)//3
        gltf={"asset":{"version":"2.0","generator":"NWIS original representational surface geometry"},"scene":0,"scenes":[{"nodes":list(range(len(nodes)))}],"nodes":nodes,"meshes":meshes,"materials":MATERIALS,"buffers":[{"byteLength":len(binary)}],"bufferViews":views,"accessors":accessors}
        chunk=json.dumps(gltf,separators=(",",":")).encode()
        while len(chunk)%4: chunk+=b" "
        while len(binary)%4: binary.append(0)
        size=12+8+len(chunk)+8+len(binary)
        path.write_bytes(struct.pack("<4sII",b"glTF",2,size)+struct.pack("<I4s",len(chunk),b"JSON")+chunk+struct.pack("<I4s",len(binary),b"BIN\0")+binary)
        print(f"{path.name}: {path.stat().st_size:,} bytes, {triangles:,} triangles")


def create(path: str, name: str, tier: str):
    model=Model()
    if tier=="active": model.active_rig()
    elif tier=="offshore": model.offshore_rig()
    else: model.wellhead(tier=="selected")
    model.write(OUT/path,name)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    create("active_surface_rig.glb","Representational land drilling installation","active")
    create("offshore_surface_rig.glb","Representational offshore drilling unit","offshore")
    create("selected_surface_wellhead.glb","Representational selected offset wellhead","selected")
    create("offset_wellhead.glb","Representational offset wellhead marker","light")


if __name__=="__main__": main()
