# Tiles preview pictures into review sheets (2 x 2 per sheet, with the car name burned in as the file order).
# Run: blender -b --factory-startup -P sheet.py -- <previews folder> <shot name> <out prefix> car1 car2 ...
import os
import sys

import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
folder, shot, out = args[:3]
cars = args[3:]
W, H = 800, 450
for n in range(0, len(cars), 4):
    group = cars[n:n + 4]
    sheet = np.zeros((2 * H, 2 * W, 4), dtype=np.float32)
    for i, car in enumerate(group):
        path = os.path.join(folder, f"{car}_{shot}.png")
        if not os.path.exists(path):
            continue
        img = bpy.data.images.load(path)
        img.scale(W, H)
        px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)
        row, col = 1 - i // 2, i % 2          # Blender pixels start at the bottom
        sheet[row * H:(row + 1) * H, col * W:(col + 1) * W] = px
        bpy.data.images.remove(img)
    out_img = bpy.data.images.new("sheet", 2 * W, 2 * H, alpha=True)
    out_img.pixels = sheet.ravel()
    path = f"{out}_{n // 4 + 1}.png"
    out_img.filepath_raw = path
    out_img.file_format = "PNG"
    out_img.save()
    bpy.data.images.remove(out_img)
    print("wrote", path, "=", ", ".join(group))
