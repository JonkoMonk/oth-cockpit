# Measures the inside of a car body with rays (game coordinates), to size the cockpit parts.
# Run: blender -b --factory-startup -P measure.py -- <car folder> <car>
import os
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True   # no __pycache__ (it would hold full folder paths)
sys.path.insert(0, os.path.dirname(__file__))
import carref  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
folder, car = args[:2]
X = float(args[2]) if len(args) > 2 else -0.38
bpy.ops.wm.read_factory_settings(use_empty=True)
body = carref.load_body(car, folder)
dg = bpy.context.evaluated_depsgraph_get()
bvh = BVHTree.FromObject(body, dg)
B2U = carref.U2B3.inverted()


def hit(origin, direction):
    o = carref.U2B3 @ Vector(origin)
    d = (carref.U2B3 @ Vector(direction)).normalized()
    loc, _, _, dist = bvh.ray_cast(o, d)
    if loc is None:
        return None
    g = B2U @ loc
    return (round(g.x, 3), round(g.y, 3), round(g.z, 3)), round(dist, 3)


def show(label, origin, direction):
    print(f"{label:34s} from {origin} dir {direction}: {hit(origin, direction)}")


print("== cabin profile along z (x = -0.38 driver line, 0 centre) ==")
for x in (X, 0.0):
    for z in (-1.2, -0.8, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 0.8):
        up = hit((x, 1.2, z), (0, 1, 0))
        down = hit((x, 1.2, z), (0, -1, 0))
        print(f"x {x:5.2f} z {z:5.2f}: roof {up[0][1] if up else None}  floor {down[0][1] if down else None}")
print("== side walls (from centre line, rays left/right) ==")
for y in (0.7, 0.9, 1.1, 1.3, 1.5, 1.7, 1.9):
    for z in (-0.6, -0.2, 0.2):
        l = hit((0, y, z), (-1, 0, 0))
        r = hit((0, y, z), (1, 0, 0))
        print(f"y {y:4.2f} z {z:5.2f}: left x {l[0][0] if l else None}  right x {r[0][0] if r else None}")
print("== forward (windscreen / cowl / front) from driver line ==")
for y in (0.7, 0.9, 1.1, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9):
    f = hit((X, y, -0.2), (0, 0, 1))
    print(f"y {y:4.2f}: front z {f[0][2] if f else None}")
print("== backward ==")
for y in (0.9, 1.3, 1.7):
    b = hit((X, y, -0.2), (0, 0, -1))
    print(f"y {y:4.2f}: back z {b[0][2] if b else None}")
