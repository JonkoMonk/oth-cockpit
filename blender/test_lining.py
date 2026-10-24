# Quick look at the automatic lining of one car (no dash): measure, line, render the driver's views.
# Run: blender -b --factory-startup -P test_lining.py -- <assets folder> <car folder> <car> <eye x> [eye y] [eye z]
import os
import sys

import bpy

sys.dont_write_bytecode = True   # no __pycache__ (it would hold full folder paths)
sys.path.insert(0, os.path.dirname(__file__))
import kit as K  # noqa: E402
import parts as P  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
P.ASSETS, folder, car = args[0], args[1], args[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
k = K.Kit(car, folder)
m0 = k.measure((float(args[3]), 1.4, -0.3))
ex = float(args[3])
eye = (ex, float(args[4]) if len(args) > 4 else m0["ws"]["base_y"] + 0.27,
       float(args[5]) if len(args) > 5 else m0["ws"]["base_z"] - 0.85)
m = k.measure(eye)
liner = P.material("lit:headliner", (0.30, 0.30, 0.29), rough=0.95)
k.auto_lining(m, liner, eye)
k.body_bits(m)
k.previews(eye, P.ASSETS, {"lining_user": (eye, P.Rx(6), 85), "lining_left": (eye, P.Ry(-70) @ P.Rx(5), 75),
                           "lining_back": (eye, P.Ry(160) @ P.Rx(5), 75)})
