# v2 cockpit builder (game style, one character per car): exports Car_<game name>.glb from the car's
# entry in cars_v2.py, then (optionally) renders game-look previews.
# Run: blender -b --factory-startup -P build_car_v2.py -- <assets folder> <cars folder> <car> [--preview <folder>] [--nofit]
#   (--nofit: leave the instrument clusters where the layout put them; the instrument check still prints)
#   (also works with the bpy Python module:  python build_car_v2.py <assets> <cars> <car> [--preview <folder>])
# The assets folder must already hold the dial faces from dials_v2style.py and lamps.png / gears.png.
import os
import sys

import bpy

sys.dont_write_bytecode = True   # no __pycache__ (it would hold full folder paths)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cars_v2  # noqa: E402
import kit as K  # noqa: E402
import parts as P  # noqa: E402
import styles_v2  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
P.ASSETS, cars_folder, car = args[0], args[1], args[2]
preview = args[args.index("--preview") + 1] if "--preview" in args else None
cfg = cars_v2.CARS[car]
bpy.ops.wm.read_factory_settings(use_empty=True)
P._mats.clear()
styles_v2.MATS.clear()
k = K.Kit(car, os.path.join(cars_folder, car))
L = styles_v2.build(k, cfg)
print(f"LAYOUT: eye {tuple(round(v, 3) for v in L.eye)}, dash face z {L.face_z:.3f} top {L.face_top:.3f} bottom "
      f"{L.face_bottom:.3f}, dash top {L.top_y:.3f}, wheel {tuple(round(v, 3) for v in L.wc)} r {L.wheel_r:.3f} "
      f"tilt {L.tilt}, line over the rim at the dash face {L.sight_y(L.face_z):.3f}")
import fit_v2  # noqa: E402
if "--nofit" not in args:
    for group, lo, hi in getattr(L, "clusters", []):
        fit_v2.slide(group, L.eye, {k.body.name}, lo, hi)
    # Then the wheel a few cm up or down where it hides the least, and the clusters once more for that wheel.
    if cfg.get("fit_wheel", True):
        fit_v2.fit_wheel(L.eye, {k.body.name})
        for group, lo, hi in getattr(L, "clusters", []):
            fit_v2.slide(group, L.eye, {k.body.name}, lo, hi)
    if cfg.get("nudge", True):
        fit_v2.nudge(L.eye, {k.body.name}, reach=cfg.get("nudge_reach", 0.03))
fit_v2.report(L.eye, {k.body.name})
k.frame_covers(L.eye)
k.export(L.eye, P.ASSETS, game_name=cfg["game"])
if preview:
    import preview_v2
    from parts import Rx, Ry
    shots = {"user": (None, Rx(6), 85)}
    if os.environ.get("V2_ALL_SHOTS"):
        shots.update({"side": (None, Ry(50 * -cfg.get("side", -1)) @ Rx(26), 75)})
    preview_v2.render(k, os.path.join(cars_folder, car), L.eye, preview, shots,
                      samples=int(os.environ.get("V2_SAMPLES", "32")), res=float(os.environ.get("V2_RES", "1.0")))
