# Writes the per-vertex normals of a car's body mesh (LOD0) from the game's cars bundle, as
# <Car>_body_LOD0.normals.json next to the OBJ that export_car.py / export_all.py wrote (same vertex order; the OBJ
# has no normals). Used by kit.body_copy (cfg body_cut) so the body copy shades exactly like the game's body.
# Never shipped. Needs Python 3.13 for pylibs' brotli (Blender's: %USERPROFILE%\dev\tools\blender\5.2\python\bin\python.exe).
# Usage: python -I export_body_normals.py <cars bundle> <CarName e.g. DingDing> <out dir>
import json
import os
import sys

sys.path.insert(0, os.path.expandvars(r"%USERPROFILE%\dev\tools\pylibs"))
import UnityPy  # noqa: E402
from UnityPy.helpers.MeshHelper import MeshHandler  # noqa: E402

bundle, car, out = sys.argv[1:4]
env = UnityPy.load(bundle)
for obj in env.objects:
    if obj.type.name == "Mesh" and obj.peek_name() == f"{car}_body_LOD0":
        h = MeshHandler(obj.read())
        h.process()
        # Unity's mesh space = game space without the OBJ's mirrored x (the body transform only scales and moves).
        normals = [[round(n[0], 6), round(n[1], 6), round(n[2], 6)] for n in h.m_Normals]
        path = os.path.join(out, f"{car}_body_LOD0.normals.json")
        with open(path, "w") as f:
            json.dump(normals, f)
        print("wrote", path, len(normals), "normals")
        break
else:
    sys.exit(f"no mesh {car}_body_LOD0 in {bundle}")
