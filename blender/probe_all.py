# Measures every exported car's cabin with kit.measure from a rough eye position (for planning).
# Run: blender -b --factory-startup -P probe_all.py -- <cars folder> [car ...]
import os
import sys

import bpy

sys.dont_write_bytecode = True   # no __pycache__ (it would hold full folder paths)
sys.path.insert(0, os.path.dirname(__file__))
import kit as K  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
folder = args[0]
cars = args[1:] or sorted(d for d in os.listdir(folder) if os.path.exists(os.path.join(folder, d, f"{d}_body_LOD0.obj")))
for car in cars:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    k = K.Kit(car, os.path.join(folder, car))
    # Rough eye: find the windscreen from inside the middle of the car, then sit behind it.
    m0 = k.measure((-0.4, 1.4, -0.3))
    ws = m0["ws"]
    eye = (-0.4, ws["base_y"] + 0.25, ws["base_z"] - 0.85)
    m = k.measure(eye)
    print(f"== {car}: eye {tuple(round(v, 2) for v in eye)} floor {m['floor']:.2f} roof {m['roof']:.2f} rear {m['rear']:.2f} "
          f"hood {m['hood']:.2f} | screen y {m['ws']['base_y']:.2f}..{m['ws']['top_y']:.2f} z {m['ws']['base_z']:.2f}..{m['ws']['top_z']:.2f} "
          f"half {m['ws']['half_w']:.2f} | belt {m['belt']:.2f} top {m['win_top']:.2f} windows "
          + " ".join(f"[{w[0]:.2f}..{w[1]:.2f}]" for w in m["windows"])
          + f" | rear glass {tuple(round(v, 2) for v in m['rear_glass']) if m['rear_glass'] else None}")
