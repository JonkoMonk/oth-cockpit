# Contact sheet of all exported car bodies (3/4 view from the front left, with names), to plan the cockpits.
# Run: blender -b --factory-startup -P overview.py -- <cars folder> <out png>
import math
import os
import sys

import bpy
from mathutils import Matrix

sys.dont_write_bytecode = True   # no __pycache__ (it would hold full folder paths)
sys.path.insert(0, os.path.dirname(__file__))
import carref  # noqa: E402

folder, out = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
cars = sorted(d for d in os.listdir(folder) if os.path.exists(os.path.join(folder, d, f"{d}_body_LOD0.obj")))
COLS, STEP_X, STEP_Z = 6, 6.5, 7.0
for i, car in enumerate(cars):
    ob = carref.load_body(car, os.path.join(folder, car))
    gx, gz = (i % COLS) * STEP_X, -(i // COLS) * STEP_Z
    # Turn each car 35 degrees so the front and the left side show; then move it to its grid cell.
    turn = Matrix.Rotation(math.radians(-35), 4, "Y")
    ob.matrix_world = carref.U2B @ Matrix.Translation((gx, 0, gz)) @ turn @ carref.U2B.inverted() @ ob.matrix_world
    cage = os.path.join(folder, car, f"{car}_rollcage_LOD0.obj")
    cu = bpy.data.curves.new("t", "FONT")
    cu.body = car
    cu.size = 0.7
    cu.align_x = "CENTER"
    t = bpy.data.objects.new("t", cu)
    scene.collection.objects.link(t)
    carref.place(t, (gx, 0.0, gz + 3.0))   # lying flat in front of the car, readable from the camera
    m = bpy.data.materials.new("txt")
    m.diffuse_color = (0, 0, 0, 1)
    t.data.materials.append(m)
    print(car, "cage" if os.path.exists(cage) else "")

scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "TEXTURE"
scene.render.resolution_x, scene.render.resolution_y = 2400, 1500
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = COLS * STEP_X + 2
cx = (COLS - 1) * STEP_X / 2
rows = math.ceil(len(cars) / COLS)
cz = -(rows - 1) * STEP_Z / 2
look = Matrix(((-1, 0, 0), (0, 0, -1), (0, -1, 0)))
# In front of the grid looking back, 30 degrees down.
rot = Matrix.Rotation(math.radians(180), 3, "Y") @ Matrix.Rotation(math.radians(30), 3, "X")
carref.place(cam, (cx, 25, cz + 43.3), rot @ look)
world = bpy.data.worlds.new("w")
world.color = (0.6, 0.62, 0.65)
scene.world = world
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("wrote", out)
