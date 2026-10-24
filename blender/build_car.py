# Generic cockpit builder: one car from its entry in cars_config.py, with the styles from styles.py and
# the automatic body measurements (kit.py). Exports Car_<game name>.glb and preview pictures.
# Run: blender -b --factory-startup -P build_car.py -- <assets folder> <cars folder> <car>
import os
import sys

import bpy

sys.dont_write_bytecode = True   # no __pycache__ (it would hold full folder paths)
sys.path.insert(0, os.path.dirname(__file__))
import cars_config  # noqa: E402
import kit as K  # noqa: E402
import parts as P  # noqa: E402
import styles  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
P.ASSETS, cars_folder, car = args[0], args[1], args[2]
cfg = cars_config.CARS[car]
bpy.ops.wm.read_factory_settings(use_empty=True)
P._mats.clear()
styles.MATS.clear()
k = K.Kit(car, os.path.join(cars_folder, car))
L = styles.build(k, cfg, P.ASSETS)
k.export(L.eye, P.ASSETS, game_name=cfg["game"])
k.previews(L.eye, P.ASSETS, K.standard_shots(L.eye))
