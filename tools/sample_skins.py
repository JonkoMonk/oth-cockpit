# Samples a car's livery textures at candidate UVs (to find spots that are plain paint in every skin).
# Run: blender -b --factory-startup -P sample_skins.py -- <car folder> <car>
import glob
import os
import sys

import bpy

folder, car = sys.argv[sys.argv.index("--") + 1:][:2]
cands = [(u / 20, v / 20) for u in range(1, 20) for v in range(1, 20)]
imgs = {}
for path in sorted(glob.glob(os.path.join(folder, f"{car}_*.png"))):
    name = os.path.basename(path)[len(car) + 1:-4]
    if not (name.startswith("skin") or name in ("masks", "AO_Dirty", "lights")):
        continue
    im = bpy.data.images.load(path)
    imgs[name] = (im.size[0], im.size[1], list(im.pixels))


def px(name, u, v):
    w, h, p = imgs[name]
    x, y = min(int(u * w), w - 1), min(int(v * h), h - 1)   # Blender pixels: bottom row first, like UV v
    i = (y * w + x) * 4
    return tuple(round(c, 2) for c in p[i:i + 3])


skins = [n for n in imgs if n.startswith("skin")]
for u, v in cands:
    m = px("masks", u, v)
    if not (m[2] > 0.8 and m[0] < 0.2 and m[1] < 0.2):   # blue = paint
        continue
    cols = [px(s, u, v) for s in skins]
    print(f"uv ({u:.2f},{v:.2f}) ao {px('AO_Dirty', u, v)} " + " ".join(f"{s}={c}" for s, c in zip(skins, cols)))
