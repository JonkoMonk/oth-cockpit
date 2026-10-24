# Draws dial faces, warning-lamp icons and the gear display as PNG pictures (rendered by Blender,
# so the numbers use a real font).
# Run: blender -b --factory-startup -P dials.py -- <output folder>
#
# A dial runs clockwise from bottom-left (value 0) to bottom-right (full scale): 270 degrees
# (small gauges: 90 degrees, see SMALL_SWEEP), the same sweep the mod turns the needles through.
import math
import os
import sys

import bpy

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.getcwd()
# Linear colours (Blender shows them brighter in the PNG, which is sRGB).
FACE = (0.006, 0.006, 0.007, 1)
INK = (0.85, 0.85, 0.80, 1)
DIM = (0.35, 0.35, 0.33, 1)
RED = (0.80, 0.04, 0.02, 1)
BLUE = (0.05, 0.25, 0.80, 1)
WHITE = (1, 1, 1, 1)
BLACK = (0.0, 0.0, 0.0, 1)
SWEEP = 270
SMALL_SWEEP = 90


def reset(w, h, ortho):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "BLENDER_WORKBENCH"
    s.display.shading.light = "FLAT"
    s.display.shading.color_type = "MATERIAL"
    s.render.resolution_x, s.render.resolution_y = w, h
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGB"
    s.render.film_transparent = False
    s.view_settings.view_transform = "Standard"
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho
    cam.location = (0, 0, 5)
    s.collection.objects.link(cam)
    s.camera = cam
    return s


def mat(color):
    name = "m_%.3f_%.3f_%.3f" % color[:3]
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = color
    return m


def poly(pts, color, z, dx=0.0, dy=0.0):
    me = bpy.data.meshes.new("p")
    me.from_pydata([(x + dx, y + dy, z) for x, y in pts], [], [list(range(len(pts)))])
    ob = bpy.data.objects.new("p", me)
    ob.data.materials.append(mat(color))
    bpy.context.scene.collection.objects.link(ob)
    return ob


def circle(r, n=64, cx=0.0, cy=0.0):
    return [(cx + math.cos(2 * math.pi * i / n) * r, cy + math.sin(2 * math.pi * i / n) * r) for i in range(n)]


def at(angle, r):
    """Point at clockwise angle (radians, 0 = up) and radius r."""
    return (math.sin(angle) * r, math.cos(angle) * r)


def font():
    # Inter (SIL Open Font License), shipped with Blender: clear digits, unlike the default font's "1".
    v = "%d.%d" % bpy.app.version[:2]
    path = os.path.join(os.path.dirname(bpy.app.binary_path), v, "datafiles", "fonts", "Inter.woff2")
    return bpy.data.fonts.get("Inter") or bpy.data.fonts.load(path)


def text(s, x, y, size, color, align="CENTER", bold=False):
    cu = bpy.data.curves.new("t", "FONT")
    cu.font = font()
    cu.body = s
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    if bold:
        cu.offset = 0.004 * size   # a touch heavier
    ob = bpy.data.objects.new("t", cu)
    ob.location = (x, y, 0.02)
    ob.data.materials.append(mat(color))
    bpy.context.scene.collection.objects.link(ob)


def render(file):
    s = bpy.context.scene
    s.render.filepath = os.path.join(OUT, file)
    bpy.ops.render.render(write_still=True)
    print("wrote", s.render.filepath)


def dial(file, top, major, minor, labels, unit, red_from=None, sweep=SWEEP, label_r=0.56, label_size=0.22,
         low=None, center_label=True):
    reset(512, 512, 2.0)

    def angle_of(f):
        return math.radians(-sweep / 2 + sweep * f)

    def tick(f, r_out, length, width, color):
        a = angle_of(f)
        c, s = math.cos(a), math.sin(a)
        pts = []
        for rr, w in ((r_out - length, -width), (r_out, -width), (r_out, width), (r_out - length, width)):
            x, y = at(a, rr)
            pts.append((x + c * w, y - s * w))
        poly(pts, color, 0.01)

    def arc(f0, f1, r_in, r_out, color, steps=48):
        for i in range(steps):
            a0, a1 = angle_of(f0 + (f1 - f0) * i / steps), angle_of(f0 + (f1 - f0) * (i + 1) / steps)
            poly([at(a0, r_in), at(a0, r_out), at(a1, r_out), at(a1, r_in)], color, 0.005)

    poly(circle(1.5, 96), FACE, 0)   # fills the whole picture
    poly(circle(0.99, 96), (0.10, 0.10, 0.11, 1), 0.001)
    poly(circle(0.96, 96), FACE, 0.002)
    if red_from is not None:
        arc(red_from / top, 1.0, 0.70, 0.76, RED)
    if low is not None:
        arc(0.0, 0.25, 0.70, 0.76, low)
    v = 0.0
    while v <= top + 1e-6:
        f = v / top
        is_major = abs(v / major - round(v / major)) < 1e-6
        color = RED if red_from is not None and v >= red_from - 1e-6 else INK
        tick(f, 0.92, 0.16 if is_major else 0.08, 0.022 if is_major else 0.012, color)
        v += minor
    for value, label in labels:
        x, y = at(angle_of(value / top), label_r)
        text(label, x, y, label_size, RED if red_from is not None and value >= red_from else INK)
    if unit:
        text(unit, 0, -0.45 if center_label else 0.25, 0.12 if center_label else 0.2, DIM)
    poly(circle(0.07, 32), (0.05, 0.05, 0.05, 1), 0.03)
    render(file)


def small_gauge(file, left, right, label, ticks=5, low=None):
    """Quarter-sweep gauge: needle pivot in the middle, scale across the top. low: colour of the low-end zone."""
    dial(file, 1.0, 1.0 / (ticks - 1), 1.0 / (ticks - 1) / 2, [(0.0, left), (1.0, right)], label,
         red_from=None, sweep=SMALL_SWEEP, label_r=0.66, label_size=0.2, low=low, center_label=False)


def icons(file, cells):
    """Row of square icons, white on near-black. cells: list of draw functions taking (cx)."""
    n = len(cells)
    reset(128 * n, 128, float(n))
    s = bpy.context.scene
    s.camera.data.sensor_fit = "HORIZONTAL"
    poly([(-n, -1), (n, -1), (n, 1), (-n, 1)], (0.01, 0.01, 0.01, 1), 0)
    for i, draw in enumerate(cells):
        draw(-n / 2 + 0.5 + i)
    render(file)


def icon_handbrake(cx):
    poly(circle(0.36, 48, cx), WHITE, 0.01)
    poly(circle(0.29, 48, cx), BLACK, 0.011)
    text("P", cx, 0, 0.42, WHITE)


def icon_headlights(cx):
    # Lamp body: a "D" shape with three beams to the left.
    pts = [(cx - 0.02, -0.22), (cx + 0.10, -0.22)]
    pts += [(cx + 0.10 + math.sin(math.radians(a)) * 0.22, math.cos(math.radians(a)) * -0.22) for a in range(0, 181, 15)]
    pts += [(cx - 0.02, 0.22)]
    poly(pts, WHITE, 0.01)
    for y in (-0.15, 0.0, 0.15):
        poly([(cx - 0.36, y - 0.03), (cx - 0.08, y - 0.03), (cx - 0.08, y + 0.03), (cx - 0.36, y + 0.03)], WHITE, 0.01)


def icon_lowrange(cx):
    text("L", cx - 0.12, 0.08, 0.5, WHITE)
    text("4WD", cx, -0.27, 0.2, WHITE)


def icon_engine(cx):
    # Battery: box with two terminals and + / -.
    poly([(cx - 0.32, -0.22), (cx + 0.32, -0.22), (cx + 0.32, 0.18), (cx - 0.32, 0.18)], WHITE, 0.01)
    poly([(cx - 0.27, -0.17), (cx + 0.27, -0.17), (cx + 0.27, 0.13), (cx - 0.27, 0.13)], BLACK, 0.011)
    for x in (-0.18, 0.18):
        poly([(cx + x - 0.06, 0.18), (cx + x + 0.06, 0.18), (cx + x + 0.06, 0.26), (cx + x - 0.06, 0.26)], WHITE, 0.01)
    text("-  +", cx, -0.02, 0.26, WHITE)


def gear_digits(file, labels):
    n = len(labels)
    reset(128 * n, 128, float(n))
    poly([(-n, -1), (n, -1), (n, 1), (-n, 1)], (0.01, 0.01, 0.01, 1), 0)
    for i, label in enumerate(labels):
        text(label, -n / 2 + 0.5 + i, 0.0, 0.8, WHITE)
    render(file)


os.makedirs(OUT, exist_ok=True)
# DingDing: engine limit 5000 rpm (VPVehicleController.engine.maxRpm).
dial("tacho.png", 6000, 1000, 500, [(i * 1000, str(i)) for i in range(7)], "x1000 r/min", red_from=4500)
dial("speedo.png", 140, 20, 10, [(i * 20, str(i * 20)) for i in range(8)], "km/h", label_r=0.54, label_size=0.19)
small_gauge("fuel.png", "E", "F", "FUEL", low=RED)
small_gauge("temp.png", "-20", "40", "°C", low=BLUE)
icons("lamps.png", [icon_handbrake, icon_headlights, icon_lowrange, icon_engine])
gear_digits("gears.png", ["R", "N", "1", "2", "3", "4", "5", "6"])
