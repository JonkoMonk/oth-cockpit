# Reference renders of a car body: side, top, front and the driver's view (for fitting the cockpit).
# Run: blender -b --factory-startup -P view_car.py -- <car folder> <out folder> <car> [headX headY headZ]
import math
import os
import sys

import bpy
from mathutils import Matrix

sys.dont_write_bytecode = True   # no __pycache__ (it would hold full folder paths)
sys.path.insert(0, os.path.dirname(__file__))
import carref  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
folder, out, car = args[:3]
head = tuple(float(a) for a in args[3:6]) if len(args) >= 6 else (-0.28, 1.28, 0.40)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
carref.load_body(car, folder)

# Marker at the driver's eye.
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06)
eye = bpy.context.active_object
carref.place(eye, head)
em = bpy.data.materials.new("eye")
em.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 0, 0, 1)
eye.data.materials.append(em)

sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(40), math.radians(10), math.radians(30))
scene.collection.objects.link(sun)
world = bpy.data.worlds.new("w")
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.6, 0.75, 1)
scene.world = world
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1280, 720

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
scene.camera = cam
# Blender camera local axes -> game (look along game +z, up game +y).
LOOK_FWD = Matrix(((-1, 0, 0), (0, 0, -1), (0, -1, 0)))


def shot(name, pos, rot, ortho=None, fov=80):
    cam.data.type = "ORTHO" if ortho else "PERSP"
    if ortho:
        cam.data.ortho_scale = ortho
    else:
        cam.data.lens_unit = "FOV"
        cam.data.angle = math.radians(fov)
    cam.data.clip_start = 0.02
    carref.place(cam, pos, rot)
    scene.render.filepath = os.path.join(out, f"{car}_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("wrote", scene.render.filepath)


Ry = lambda d: Matrix.Rotation(math.radians(d), 3, "Y")  # noqa: E731  game yaw (left-handed: + turns right)
Rx = lambda d: Matrix.Rotation(math.radians(d), 3, "X")  # noqa: E731  game pitch (+ looks down)
shot("side", (-6, 1.2, 0), Ry(90) @ LOOK_FWD, ortho=5)        # from the left, looking right
shot("top", (0, 8, 0), Rx(90) @ LOOK_FWD, ortho=5)            # from above
shot("front", (0, 1.2, 8), Ry(180) @ LOOK_FWD, ortho=3)       # from the front, looking back
shot("eye", head, Rx(6) @ LOOK_FWD, fov=70)                   # driver's view
eye.hide_render = True
shot("eye_wide", head, Rx(20) @ LOOK_FWD, fov=100)
