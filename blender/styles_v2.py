# Cockpits in the GAME'S OWN STYLE (v2), one character per car.
# Same pipeline as styles.py (kit.measure -> styles.Layout -> parts), but:
#   - flat matte colours (no chrome, no fine print), few and chunky parts, small rounded edges;
#   - every car gets its own character from cars_v2.py: dash, cluster, wheel, seats, colours and
#     "features" (signature parts such as the Panda's fabric shelf or the Unimog's lever forest).
# All coordinates are GAME coordinates (x right, y up, z forward; see parts.py).
# Moving parts carry the same glTF extras as before (drive/axis/a0/a1/zero/full, lamp, display,
# backlight, move=slide), so the mod needs no change except for anything marked NEW below.
import math

import bpy

import parts as P
import styles
from parts import Rx, Ry, Rz

MATS = {}


def M(name, rgb, rough=0.9):
    """Flat matte colour. rgb is sRGB 0..1 (what you'd pick in a paint program)."""
    key = f"lit:v2_{name}"
    if key not in MATS:
        MATS[key] = P.material(key, tuple(c ** 2.2 for c in rgb), rough=rough)
    return MATS[key]


DEFAULT_COLORS = dict(
    dash=(0.24, 0.23, 0.25), pad=(0.24, 0.23, 0.25), panel=(0.20, 0.20, 0.23), dark=(0.16, 0.16, 0.18),
    metal=(0.74, 0.74, 0.76), rubber=(0.22, 0.22, 0.23), seat=(0.36, 0.25, 0.19), seat2=(0.48, 0.34, 0.25),
    liner=(0.86, 0.82, 0.74), door=(0.36, 0.25, 0.19), wood=(0.58, 0.36, 0.20), carpet=(0.30, 0.24, 0.20),
    rim=(0.16, 0.16, 0.18), spoke=(0.74, 0.74, 0.76), knob=(0.16, 0.16, 0.18), knob2=(0.85, 0.25, 0.18),
    knob3=(0.95, 0.75, 0.20), accent=(0.98, 0.70, 0.30),
)


class B:
    """Everything one build needs."""

    def __init__(self, k, L, cfg, m):
        self.k, self.L, self.cfg, self.m = k, L, cfg, m
        c = dict(DEFAULT_COLORS, **cfg.get("colors", {}))
        self.c = {n: M(n, v) for n, v in c.items()}
        self.scheme = cfg.get("dials", "black")
        self.feat = set(cfg.get("features", ()))

    def mat(self, key):
        """A colour name from the palette, or 'paint' (the car's own paint)."""
        return self.k.paint if key == "paint" else self.c[key]

    def dash_uv(self):
        L = self.L
        return self.k.uv("dash (hood)", (0, L.ws["base_y"] - 0.2, L.ws["base_z"] + 0.5), (0, 1, 0))


# ---------------------------------------------------------------- small helpers

class cluster:
    """`with cluster(b):` around the code that makes one instrument cluster (dials, lamps, gear display and
    their housing). After the steering wheel is built, fit_v2.slide moves each cluster up or down to where
    the wheel hides the least of it, staying between lo and hi (game y; default: the dash face)."""

    def __init__(self, b, lo=None, hi=None):
        self.b, self.lo, self.hi = b, lo, hi

    def __enter__(self):
        self.before = set(bpy.data.objects)
        return self

    def __exit__(self, *exc):
        if exc[0] is None:
            L = self.b.L
            group = [o for o in bpy.data.objects if o not in self.before]
            lo = L.face_bottom if self.lo is None else self.lo
            hi = L.top_y if self.hi is None else self.hi
            L.clusters = getattr(L, "clusters", []) + [(group, lo, hi)]
        return False


def _rim_line(b, z):
    """The inside of the upper rim as the driver sees it, projected onto the plane at depth z:
    sorted (x, y) points from the eye over the rim's inner edge."""
    L = b.L
    ex, ey, ez = L.eye
    wx, wy, wz = L.wc
    t = math.radians(L.tilt)
    ri = L.wheel_r - b.cfg.get("rim_thick", 0.017)
    pts = []
    for i in range(61):
        a = math.pi * i / 60
        px, h = wx + ri * math.cos(a), ri * math.sin(a)
        py, pz = wy + h * math.cos(t), wz + h * math.sin(t)
        s = (z - ez) / (pz - ez)
        pts.append((ex + (px - ex) * s, ey + (py - ey) * s))
    return sorted(pts)


def opening_y(b, x, r, z, margin=0.012):
    """Highest centre height for a round instrument of outer radius r at (x, depth z) that stays completely
    inside the upper opening of the steering wheel (the rim never crosses it). Outside the rim's width it
    returns the height of the line over the rim's top instead (the instrument is beside the wheel)."""
    line = _rim_line(b, z)
    best = None
    for i in range(9):
        u = x - r + 2 * r * i / 8
        if not line[0][0] <= u <= line[-1][0]:
            continue
        for (x0, y0), (x1, y1) in zip(line, line[1:]):
            if x0 <= u <= x1:
                ry = y0 + (y1 - y0) * (u - x0) / max(x1 - x0, 1e-9)
                break
        y = ry - margin - math.sqrt(max(r * r - (u - x) ** 2, 0))
        best = y if best is None else min(best, y)
    return best if best is not None else b.L.sight_y(z) + r + margin


def hub_y(b, z):
    """Height at depth z of the line from the eye over the top of the wheel hub (and level spokes)."""
    L = b.L
    ex, ey, ez = L.eye
    t = math.radians(L.tilt)
    h = b.cfg.get("hub_r", 0.055) * (1.5 if b.cfg.get("hub") == "big" else 1.0) + 0.02
    if b.cfg.get("hub") == "bar":
        h = 0.06
    py, pz = L.wc[1] + h * math.cos(t), L.wc[2] + h * math.sin(t)
    return ey + (py - ey) * (z - ez) / (pz - ez)


def gauge(b, kind, x, y, r, z, parent=None, ring="metal"):
    """Flat dial: ring, face (glow: backlight), needle on a pivot the mod turns. kind: tacho/speedo/fuel/temp."""
    drives = {"tacho": ("rpm", 135, -135, 6000, 0), "speedo": ("speed", 135, -135, 140, 0),
              "fuel": ("fuel", 45, -45, 1.0, 0), "temp": ("temp", 45, -45, 40, -20)}
    drive, a0, a1, full, zero = drives[kind]
    P.place(P.torus(kind + "_ring", r + 0.006, 0.006, b.mat(ring), n=28, m=6, parent=parent), (x, y, z))
    face = P.disc(kind + "_face", r, P.material("glow:" + kind, image=f"v2_{kind}_{b.scheme}.png", rough=0.9),
                  n=32, parent=parent)
    P.place(face, (x, y, z))
    face["backlight"] = 1
    piv = P.empty("needle_" + kind, (x, y, z - 0.004), parent=parent, drive=drive, axis="z", a0=a0, a1=a1,
                  zero=zero, full=full)
    P.prism(kind + "_needle", [(-0.0035, -r * 0.1), (-0.0015, r * 0.82), (0.0015, r * 0.82), (0.0035, -r * 0.1)],
            "z", -0.0015, 0.0015, b.c["accent"] if b.scheme == "eighties" else M("needle", (0.98, 0.45, 0.20)),
            parent=piv)
    P.place(P.cylinder(kind + "_cap", r * 0.15, 0.006, b.c["dark"], n=12, z0=-0.006, parent=piv))


LAMP_CELLS = {"handbrake": 0, "headlights": 1, "lowrange": 2, "engine": 3}
LAMP_COLOURS = {"handbrake": (0.9, 0.06, 0.03), "engine": (0.9, 0.06, 0.03), "headlights": (0.10, 0.85, 0.20),
                "lowrange": (1.0, 0.55, 0.0)}


def lamps(b, xs, y, z, parent=None, r=0.014):
    """Round warning lamps (icons from lamps.png); the mod switches their glow."""
    for name, x in xs.items():
        cell = LAMP_CELLS[name]
        d = P.disc("lamp_" + name, r, P.material("glow:lamp_" + name, LAMP_COLOURS[name], image="lamps.png"), n=16,
                   parent=parent, uv_rect=(cell / 4 + 0.03, 0.03, (cell + 1) / 4 - 0.03, 0.97))
        P.place(d, (x, y, z))
        d["lamp"] = name


def gear_display(b, x, y, z, parent=None, size=0.04):
    P.box("gear_window", (x - size * 0.75, y - size * 0.65, z - 0.002), (x + size * 0.75, y + size * 0.65, z + 0.004),
          b.c["dark"], parent=parent)
    g = P.quad("gear_display", size, size, P.material("glow:gear", (1.0, 0.55, 0.05), image="gears.png"), parent=parent)
    P.place(g, (x, y, z - 0.004))   # 2 mm in front of its window (closer flickers)
    g["display"] = "gear"
    g["cells"] = 8


def dial_set(b, cx, big_y, small_y, z, r=0.075, small=0.034, spread=None, outer=0.24, parent=None, ring="metal",
             lamps_y=None):
    """Rev counter + speedo side by side, fuel + temp further out, lamps and gear display between them."""
    spread = spread or r + 0.012
    gauge(b, "tacho", cx - spread, big_y, r, z, parent, ring)
    gauge(b, "speedo", cx + spread, big_y, r, z, parent, ring)
    gauge(b, "fuel", cx - outer, small_y, small, z, parent, ring)
    gauge(b, "temp", cx + outer, small_y, small, z, parent, ring)
    ly = small_y if lamps_y is None else lamps_y
    lamps(b, {"handbrake": cx - 0.15, "engine": cx - 0.105, "headlights": cx + 0.105, "lowrange": cx + 0.15}, ly, z,
          parent)
    gear_display(b, cx, ly, z, parent)


# ---------------------------------------------------------------- dash

def dash(b):
    k, L, cfg = b.k, b.L, b.cfg
    style = cfg.get("dash", "painted_pad")
    w = L.wall - 0.005
    ft, fb, fz, top, front = L.face_top, L.face_bottom, L.face_z, L.top_y, L.dash_front
    face_mat = k.paint if style in ("painted", "painted_pad", "flat") else b.c["dash"]
    uv = b.dash_uv() if face_mat is k.paint else None
    if style == "shelf":
        # Fiat Panda: no dash, a full-width fabric hammock under a thin top rail.
        P.prism("dash_top", [(fz + 0.06, ft - 0.02), (fz + 0.04, ft + 0.02), (front, top), (front, ft - 0.02)],
                "x", -w, w, b.c["dash"])
        P.prism("shelf_tray", [(fz - 0.10, fb + 0.02), (fz - 0.10, fb + 0.06), (fz - 0.08, fb + 0.06), (fz - 0.06, fb + 0.03),
                               (fz + 0.10, fb + 0.03), (fz + 0.10, fb + 0.02)], "x", -w + 0.02, w - 0.02, b.c["seat2"])
        P.box("shelf_rail", (-w + 0.02, fb + 0.055, fz - 0.115), (w - 0.02, fb + 0.075, fz - 0.095), b.c["dash"])
        P.box("shelf_back", (-w, fb - 0.02, fz + 0.10), (w, ft - 0.02, fz + 0.13), b.c["dash"])
    elif style == "flat":
        # Utility: a plain painted steel panel with a shelf on top (Land Rover Series, military trucks).
        P.box("dash_face", (-w, fb, fz), (w, ft, fz + 0.03), k.paint, uv=uv)
        P.prism("dash_shelf", [(fz - 0.10, ft), (fz - 0.10, ft + 0.02), (front, top), (front, ft)], "x", -w, w, k.paint, uv=uv)
        P.box("shelf_lip", (-w + 0.01, ft + 0.02, fz - 0.10), (w - 0.01, ft + 0.05, fz - 0.085), k.paint, uv=uv)
    else:
        P.prism("dash_body", [(fz + 0.02, fb - 0.02), (fz, fb), (fz, ft), (fz + 0.03, ft + 0.02), (front, top),
                              (front + 0.02, fb - 0.02)], "x", -w, w, face_mat, uv=uv)
        if style in ("painted_pad", "plastic", "wood"):
            pad = b.c["pad"]
            P.prism("crash_pad", [(fz + 0.01, ft - 0.03), (fz - 0.022, ft - 0.016), (fz - 0.03, ft + 0.008),
                                  (fz - 0.014, ft + 0.03), (fz + 0.03, min(ft + 0.04, top)), (front - 0.01, top - 0.002),
                                  (front, top - 0.002), (front, ft - 0.03)], "x", -w + 0.005, w - 0.005, pad)
        if style == "wood":
            P.box("wood_band", (-w + 0.02, fb + 0.06, fz - 0.008), (w - 0.02, fb + 0.13, fz + 0.001), b.c["wood"])
    if front - 0.1 > fz + 0.06:
        P.box("dash_under", (-w, fb - 0.035, fz + 0.01), (w, fb - 0.02, front - 0.1), b.c["dark"])
    P.box("firewall", (-w, L.floor, front), (w, fb, front + 0.04), k.paint,
          uv=k.uv("firewall", (0, L.ws["base_y"] - 0.2, L.ws["base_z"] + 0.5), (0, 1, 0)))
    for s in (-1, 1):   # kick panels close the footwell corners
        P.box(f"kick_{s}", (min(s * (w - 0.06), s * w), L.floor, fz + 0.05), (max(s * (w - 0.06), s * w), fb, front),
              k.paint, uv=k.uv("kick", (0, L.floor + 0.15, L.eye[2]), (s, 0, 0)))
    # Glovebox on the passenger side (a plain door, in the dash colour).
    if cfg.get("glovebox", True) and style not in ("shelf",):
        gx0, gx1 = L.mx(0.22, min(w - 0.08, 0.66))
        cy = (ft + fb) / 2
        P.box("glovebox", (gx0, cy - 0.09, fz - 0.012), (gx1, cy + 0.07, fz + 0.002), face_mat,
              uv=uv if face_mat is k.paint else None)
        hx = (gx0 + gx1) / 2
        P.box("glove_latch", (hx - 0.025, cy + 0.04, fz - 0.018), (hx + 0.025, cy + 0.052, fz - 0.012), b.c["metal"])


def centre_stack(b):
    """Radio block and a couple of knobs in the middle (unless the instruments live there)."""
    L, cfg = b.L, b.cfg
    if cfg.get("cluster") == "center" or cfg.get("radio", True) is False or cfg.get("dash") == "shelf":
        return
    fz, cy = L.face_z, (L.face_top + L.face_bottom) / 2
    radio = cfg.get("radio", "block")
    P.box("radio", (-0.11, cy - 0.04, fz - 0.026), (0.11, cy + 0.05, fz + 0.002), b.c["dark"])
    if radio == "pushbutton":   # 1950s: chrome-ish grille and five big buttons
        for i in range(5):
            P.box(f"radio_btn{i}", (-0.08 + i * 0.034, cy - 0.032, fz - 0.04), (-0.058 + i * 0.034, cy - 0.012, fz - 0.026),
                  b.c["metal"])
        P.box("radio_window", (-0.08, cy + 0.0, fz - 0.028), (0.08, cy + 0.03, fz - 0.026), b.c["accent"])
    else:
        P.box("radio_window", (-0.07, cy + 0.0, fz - 0.028), (0.07, cy + 0.03, fz - 0.026), b.c["accent"])
        for x in (-0.088, 0.088):
            P.place(P.cylinder(f"radio_knob{x}", 0.012, 0.016, b.c["metal"], n=10, z0=-0.016), (x, cy + 0.012, fz - 0.026))
    for i, x in enumerate((-0.07, 0.0, 0.07)):   # heater knobs
        P.place(P.cylinder(f"heater_knob{i}", 0.014, 0.018, b.c["knob"], n=10, z0=-0.018), (x, cy - 0.09, fz))


# ---------------------------------------------------------------- instruments

def instruments(b):
    k, L, cfg = b.k, b.L, b.cfg
    style = cfg.get("cluster", "binnacle")
    dx, fz = L.dx, L.face_z
    ring = cfg.get("ring", "metal")
    r = cfg.get("dial_r", 0.075)
    if style in ("binnacle", "wide", "tubes"):
        # Recessed panel in front of the driver, padded brow above: big dials read through the wheel.
        width = {"binnacle": 0.34, "wide": 0.42, "tubes": 0.32}[style]
        cz = fz - 0.05
        top = min(L.face_top + 0.015, L.top_y - 0.03)
        bottom = top - 0.28
        surround = k.paint if cfg.get("dash", "painted_pad") in ("painted", "painted_pad") else b.c["dash"]
        suv = b.dash_uv() if surround is k.paint else None
        P.box("binn_surround", (dx - width - 0.02, bottom - 0.02, cz + 0.004), (dx + width + 0.02, top + 0.02, fz + 0.01),
              surround, uv=suv)
        P.box("cluster_panel", (dx - width, bottom, cz - 0.002), (dx + width, top, cz + 0.004), b.c["panel"])
        P.prism("binn_brow", [(cz - 0.05, top + 0.02), (cz - 0.055, top + 0.035), (cz - 0.03, top + 0.05),
                              (fz + 0.03, top + 0.055), (fz + 0.03, top + 0.02)], "x", dx - width - 0.03, dx + width + 0.03,
                b.c["pad"])
        # The whole big dial (ring included) below the line over the rim: read through the wheel's opening.
        sp = r + 0.012
        big_y = min(opening_y(b, dx - sp, r + 0.012, cz), opening_y(b, dx + sp, r + 0.012, cz), top - 0.075 - r)
        big_y = max(big_y, bottom + r + 0.02, hub_y(b, cz) + r + 0.015)
        fz_ = cz - 0.003
        if style == "tubes":   # Lada Niva: three deep tubes, speedo in the middle
            for i, (kind, x, rr) in enumerate((("tacho", dx - 0.17, 0.062), ("speedo", dx, 0.075), ("fuel", dx + 0.17, 0.05))):
                P.place(P.cylinder(f"tube{i}", rr + 0.012, 0.06, b.c["dark"], n=20, z0=-0.06), (x, big_y + 0.01, cz))
                gauge(b, kind, x, big_y + 0.01, rr, fz_ + 0.0, ring=ring)
            gauge(b, "temp", dx + 0.27, top - 0.05, 0.03, fz_, ring=ring)
            lamps(b, {"handbrake": dx - 0.27, "engine": dx - 0.23, "headlights": dx + 0.06, "lowrange": dx + 0.10}, top - 0.04, fz_)
            gear_display(b, dx - 0.06, top - 0.04, fz_)
        else:
            dial_set(b, dx, big_y, top - 0.04, fz_, r=r, outer=width - 0.08, ring=ring)
        return
    if style == "pod":
        # Pod on top of the dash, read over the wheel (Defender, Bronco).
        z = fz - 0.04
        y0 = max(L.sight_y(z) + 0.02, L.face_top - 0.10)
        pod = P.empty("binnacle", (dx, y0 + 0.09, z), Rx(18))
        pm = k.paint if cfg.get("pod_mat") == "paint" else b.c["dash"]
        puv = b.dash_uv() if pm is k.paint else None
        P.box("pod_housing", (-0.20, -0.10, 0.0), (0.20, 0.11, 0.10), pm, parent=pod, uv=puv)
        P.box("pod_visor", (-0.21, 0.11, -0.065), (0.21, 0.13, 0.10), b.c["pad"], parent=pod)
        dial_set(b, 0.0, 0.012, -0.062, -0.002, r=0.062, small=0.027, spread=0.072, outer=0.158, parent=pod, ring=ring,
                 lamps_y=0.085)
        return
    if style == "center":
        # Instruments in the middle of a flat dash (Land Rover Series, Unimog, Forward Control).
        cz = fz - 0.004
        cy = (L.face_top + L.face_bottom) / 2 + 0.04
        P.box("center_panel", (-0.26, cy - 0.13, cz - 0.004), (0.26, cy + 0.11, fz + 0.01), b.c["panel"])
        gauge(b, "speedo", -0.10, cy, 0.08, cz - 0.007, ring=ring)
        gauge(b, "tacho", 0.075, cy + 0.025, 0.05, cz - 0.007, ring=ring)
        gauge(b, "fuel", 0.18, cy + 0.04, 0.032, cz - 0.007, ring=ring)
        gauge(b, "temp", 0.18, cy - 0.05, 0.032, cz - 0.007, ring=ring)
        lamps(b, {"handbrake": -0.21, "engine": -0.17, "headlights": 0.0, "lowrange": 0.045}, cy - 0.10, cz - 0.007)
        gear_display(b, 0.11, cy - 0.10, cz - 0.007)
        return
    if style == "single":
        # One big round speedometer in front of the driver, small ones beside it (1940s-50s).
        cz = fz - 0.004
        cy = min(L.face_top - 0.12, max(L.sight_y(cz) + 0.02, (L.face_top + L.face_bottom) / 2))
        P.place(P.cylinder("speedo_bowl", 0.115, 0.03, b.c["panel"], n=28, z0=-0.03), (dx, cy, fz))
        gauge(b, "speedo", dx, cy, 0.10, cz - 0.03, ring=ring)
        gauge(b, "tacho", dx + L.m(-0.19), cy + 0.03, 0.045, cz - 0.004, ring=ring)
        gauge(b, "fuel", dx + L.m(0.18), cy + 0.045, 0.034, cz - 0.004, ring=ring)
        gauge(b, "temp", dx + L.m(0.18), cy - 0.045, 0.034, cz - 0.004, ring=ring)
        lamps(b, {"handbrake": dx - 0.05, "engine": dx - 0.015, "headlights": dx + 0.02, "lowrange": dx + 0.055},
              cy + 0.13, cz - 0.004, r=0.012)
        gear_display(b, dx + L.m(-0.19), cy - 0.065, cz - 0.004, size=0.032)
        return
    if style in ("row", "oval"):
        # A row of dials on a panel (row: square military panel; oval: 60s chrome-edged band, Bronco).
        cz = fz - 0.004
        cy = min(L.face_top - 0.08, max(L.sight_y(cz) + 0.045, (L.face_top + L.face_bottom) / 2 + 0.05))
        if style == "oval":
            P.place(P.cylinder("oval_band", 0.10, 0.02, b.c["panel"], n=24, z0=-0.02), (dx, cy, fz))
            band = bpy.data.objects["oval_band"]
            band.scale = (2.9, 1.0, 1.0)   # Blender x = -game x; stretch sideways
            P.place(P.torus("oval_trim", 0.10, 0.006, b.c["metal"], n=32, m=6), (dx, cy, fz - 0.02))
            bpy.data.objects["oval_trim"].scale = (2.9, 1.0, 1.0)
        else:
            P.box("gauge_panel", (dx - 0.31, cy - 0.10, cz - 0.004), (dx + 0.31, cy + 0.075, fz + 0.01), b.c["panel"])
        z = cz - 0.024 if style == "oval" else cz - 0.007
        gauge(b, "speedo", dx - 0.07, cy, 0.062, z, ring=ring)
        gauge(b, "tacho", dx + 0.07, cy, 0.062, z, ring=ring)
        gauge(b, "fuel", dx - 0.205, cy, 0.04, z, ring=ring)
        gauge(b, "temp", dx + 0.205, cy, 0.04, z, ring=ring)
        ly = cy - 0.085 if style == "row" else cy + 0.10
        lamps(b, {"handbrake": dx - 0.24, "engine": dx - 0.20, "headlights": dx + 0.20, "lowrange": dx + 0.24}, ly, z, r=0.012)
        gear_display(b, dx, ly, z, size=0.032)
        if style == "row":
            for i, x in enumerate((-0.12, -0.08, 0.08, 0.12)):   # toggle switches
                P.cbox(f"toggle{i}", (0.01, 0.01, 0.03), b.c["metal"], centre=(dx + x, ly, cz - 0.02))
        return
    if style == "box":
        # A small instrument box sitting on the dash (Fiat Panda, VW Iltis).
        z = fz - 0.10 if cfg.get("dash") == "shelf" else fz - 0.05
        y0 = max(L.sight_y(z) + 0.015, L.face_top - 0.06)
        pod = P.empty("instrument_box", (dx, y0 + 0.07, z), Rx(12))
        P.box("box_housing", (-0.16, -0.075, 0.0), (0.16, 0.085, 0.09), b.c["dash"], parent=pod)
        P.box("box_visor", (-0.17, 0.085, -0.05), (0.17, 0.10, 0.09), b.c["pad"], parent=pod)
        gauge(b, "speedo", -0.055, 0.0, 0.06, -0.002, pod, ring)
        gauge(b, "tacho", 0.075, 0.015, 0.045, -0.002, pod, ring)
        gauge(b, "fuel", 0.12, -0.045, 0.022, -0.002, pod, ring)
        gauge(b, "temp", 0.04, -0.05, 0.022, -0.002, pod, ring)
        lamps(b, {"handbrake": -0.13, "engine": -0.13, "headlights": 0.13, "lowrange": 0.13}, 0.05, -0.002, pod, r=0.01)
        bpy.data.objects["lamp_engine"].location.z += 0.03       # stack the two lamps on each side
        bpy.data.objects["lamp_lowrange"].location.z += 0.03
        gear_display(b, 0.13, -0.045, -0.002, pod, size=0.026)
        return
    raise ValueError(f"cluster style {style}")


# ---------------------------------------------------------------- wheel, pedals, levers

WHEELS = {
    "t": ((0, 180, 270), 0.024), "two": ((0, 180), 0.03), "droop": ((-22, 202), 0.028), "three": ((-12, 192, 270), 0.026),
    "four": ((-6, 186, 245, 295), 0.03), "banjo": ((20, 60, 120, 160, 250, 290), 0.009), "single": ((235,), 0.04),
    "bus": ((0, 180), 0.045),
}


def wheel(b):
    k, L, cfg = b.k, b.L, b.cfg
    spokes, sw = WHEELS[cfg.get("wheel", "droop")]
    R = L.wheel_r
    wh = P.empty("steering_wheel", L.wc, Rx(L.tilt), drive="steer", axis="z", a0=270, a1=-270, zero=-1, full=1)
    P.torus("wheel_rim", R, cfg.get("rim_thick", 0.017), b.c["rim"], n=36, m=8, parent=wh)
    hub = cfg.get("hub_r", 0.055)
    length = R - hub * 0.6
    for i, a in enumerate(spokes):
        sp = P.cbox(f"wheel_spoke{i}", (length, sw, 0.009), b.c["spoke"],
                    centre=(hub * 0.6 + length / 2, 0, 0.016 + 0.0015 * i), parent=wh)
        P.place(sp, rot=Rz(a))
    P.cylinder("wheel_hub", hub, 0.032, b.c["dark"], n=16, z0=-0.006, parent=wh, r1=hub * 0.75)
    if cfg.get("hub") == "bar":   # wide padded horn bar (70s/80s American)
        P.cbox("horn_bar", (0.26, 0.075, 0.03), b.c["dark"], centre=(0, 0, -0.008), parent=wh)
    elif cfg.get("hub") == "big":   # 90s padded centre
        P.place(P.cylinder("wheel_pad", hub * 1.5, 0.03, b.c["dark"], n=16, z0=-0.02, parent=wh))
    if cfg.get("horn"):
        P.place(P.disc("horn_badge", hub * 0.55, b.c[cfg["horn"]], n=16, parent=wh), (0, 0, -0.0068))
    col_len = max(0.08, (L.face_z - L.wc[2]) / math.cos(math.radians(L.tilt)) - 0.03)
    P.place(P.cylinder("column", 0.032, col_len, b.c["dark"], n=12, z0=0.03, r1=0.04), L.wc, Rx(L.tilt))
    P.place(P.cbox("stalk", (0.14, 0.014, 0.014), b.c["dark"], centre=(-0.07 * -L.side, 0, 0)),
            (L.dx + 0.04 * L.side, L.wc[1] - 0.045, L.wc[2] + 0.11), Rx(L.tilt) @ Rz(12 * L.side))


def pedals_levers(b):
    k, L, cfg = b.k, b.L, b.cfg
    # Pivot far enough from the firewall that a fully pressed pad (18 degrees: ~12 cm forward) stays clear of
    # it, and high enough that the pad hangs 10 cm over the floor.
    py = max(L.face_bottom - 0.03, L.floor + 0.24)
    pz = min(L.face_z + 0.22, L.dash_front - 0.20)
    arm = py - L.floor - 0.10
    peds = (("clutch", -0.13, 0.065), ("brake", 0.0, 0.075), ("throttle", 0.14, 0.05))
    if cfg.get("automatic"):
        peds = (("brake", -0.04, 0.10), ("throttle", 0.13, 0.05))
    for name, off, w in peds:
        k.pedal(name, (L.dx + off, py, pz), name, w, arm=arm)
    tunnel_top = L.floor + cfg.get("tunnel_h", 0.20)
    lz = L.eye[2] + 0.30
    shifter = cfg.get("shifter", "floor")
    if shifter == "floor":
        k.lever("gear_lever", (L.m(-0.02), tunnel_top, lz), cfg.get("gear_len", 0.42), 15, 0.036, b.c["knob"], drive="gear")
    elif shifter == "column":
        P.empty("gear_lever", (L.dx + L.m(0.06), L.wc[1] - 0.06, L.wc[2] + 0.12), drive="gear", axis="x", a0=0, a1=0,
                zero=0, full=1)
        k.beam("column_shift_arm", (L.dx + L.m(0.06), L.wc[1] - 0.06, L.wc[2] + 0.12),
               (L.dx + L.m(0.28), L.wc[1] - 0.02, L.wc[2] + 0.02), 0.014, 0.014, b.c["metal"])
        P.place(P.ball("column_shift_knob", 0.02, b.c["knob"]), (L.dx + L.m(0.28), L.wc[1] - 0.02, L.wc[2] + 0.02))
    if cfg.get("transfer", True):
        k.lever("transfer_lever", (L.m(0.09), tunnel_top, lz - 0.08), 0.32, 15, 0.028, b.c["knob2"], drive="lowrange")
    for i, (x, col) in enumerate(cfg.get("extra_levers", ())):   # decor levers (diff locks, PTO, range)
        k.lever(f"extra_lever{i}", (L.m(x), tunnel_top, lz - 0.12 - 0.03 * i), 0.28, 12, 0.024, b.c[col], boot=0.035,
                shaft_r=0.009)
    hb = cfg.get("handbrake", "lever")
    if hb == "lever":
        k.lever("handbrake_lever", (L.m(-0.15), tunnel_top, L.eye[2] + 0.05), 0.32, -8, 0.032, b.c["knob"],
                drive="handbrake", a1=-30, boot=0.04, shaft_r=0.014)
    elif hb == "pull":
        h = P.empty("handbrake_handle", (L.dx + L.m(0.30), L.face_bottom + 0.04, L.face_z - 0.004), drive="handbrake",
                    move="slide", axis="z", a0=0, a1=-0.11, zero=0, full=1)
        P.cbox("handbrake_shaft", (0.014, 0.014, 0.16), b.c["metal"], centre=(0, 0, 0.065), parent=h)
        P.cbox("handbrake_grip", (0.10, 0.028, 0.032), b.c["knob"], centre=(0, 0, -0.02), parent=h)


# ---------------------------------------------------------------- seats, doors, floor

def seat_pattern(b, name, x0, x1, y0, y1, z, parent=None, along="y"):
    """Insert on a seat back facing +z: plain, stripes, tartan (checks) or ribs (corduroy)."""
    pat = b.cfg.get("seat_pattern", "plain")
    P.box(name, (x0, y0, z), (x1, y1, z + 0.012), b.c["seat2"], parent=parent)
    e = 0.002   # the pattern stays 2 mm inside the insert's edges: flush sides flicker
    if pat == "stripes":
        for i in range(3):
            yy = y0 + (y1 - y0) * (0.25 + 0.2 * i)
            P.box(f"{name}_stripe{i}", (x0 + e, yy, z + 0.012), (x1 - e, yy + 0.03, z + 0.016), b.c["accent"], parent=parent)
    elif pat == "tartan":
        nx, ny = 4, 6
        for i in range(nx):
            for j in range(ny):
                if (i + j) % 2 == 0:
                    xa, ya = x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny
                    P.box(f"{name}_chk{i}_{j}", (xa + e, ya + e, z + 0.012), (xa + (x1 - x0) / nx - e, ya + (y1 - y0) / ny - e, z + 0.015),
                          b.c["seat"], parent=parent)
    elif pat == "ribs":
        n = 6
        for i in range(n):
            xa = x0 + (x1 - x0) * (i + 0.15) / n
            P.box(f"{name}_rib{i}", (xa, y0 + e, z + 0.012), (xa + (x1 - x0) * 0.6 / n, y1 - e, z + 0.02), b.c["seat2"], parent=parent)


def seats(b):
    k, L, cfg, m = b.k, b.L, b.cfg, b.m
    style = cfg.get("seats", "bucket")
    ey, ez = L.eye[1], L.eye[2]
    cushion = max(L.floor + 0.30, ey - cfg.get("seat_below_eye", 0.78))
    back_z = ez - cfg.get("back_behind_eye", 0.36)
    seat, dark = b.c["seat"], b.c["dark"]
    if style == "bench":
        w = L.wall - 0.05
        P.box("bench_frame", (-w, L.floor, back_z), (w, cushion - 0.12, ez - 0.05), dark)
        P.prism("bench_cushion", [(back_z - 0.02, cushion - 0.12), (back_z - 0.02, cushion), (ez + 0.02, cushion + 0.02),
                                  (ez + 0.07, cushion - 0.03), (ez + 0.05, cushion - 0.12)], "x", -w, w, seat)
        bk = P.empty("bench_backframe", (0, cushion, back_z - 0.02), Rx(-8))
        P.box("bench_back", (-w + 0.005, 0.0, -0.13), (w - 0.005, 0.58, 0.0), seat, parent=bk)
        for i, x in enumerate((-w * 0.5, w * 0.5)):
            seat_pattern(b, f"bench_panel{i}", x - w * 0.38, x + w * 0.38, 0.08, 0.52, 0.0, parent=bk)
        return
    for side, sx in (("driver", L.dx), ("passenger", -L.dx)):
        if style == "deckchair":
            # Panda: a tube frame with fabric slung across it.
            for xx in (sx - 0.22, sx + 0.22):
                k.beam(f"{side}_tube_low{xx}", (xx, cushion - 0.02, ez + 0.05), (xx, cushion - 0.03, back_z), 0.025, 0.025,
                       b.c["metal"])
                k.beam(f"{side}_tube_up{xx}", (xx, cushion - 0.03, back_z), (xx, cushion + 0.60, back_z - 0.08), 0.025, 0.025,
                       b.c["metal"])
            P.prism(f"{side}_sling_seat", [(back_z + 0.02, cushion - 0.06), (back_z + 0.02, cushion - 0.03),
                                           (ez + 0.05, cushion), (ez + 0.05, cushion - 0.03)], "x", sx - 0.21, sx + 0.21, seat)
            bk = P.empty(f"{side}_backframe", (sx, cushion - 0.03, back_z), Rx(-7))
            P.box(f"{side}_sling_back", (-0.21, 0.02, -0.02), (0.21, 0.60, 0.0), b.c["seat2"], parent=bk)
            continue
        P.box(f"{side}_frame", (sx - 0.20, L.floor, back_z + 0.05), (sx + 0.20, cushion - 0.12, ez - 0.02), dark)
        P.prism(f"{side}_cushion", [(back_z + 0.02, cushion - 0.12), (back_z + 0.02, cushion), (ez + 0.02, cushion + 0.02),
                                    (ez + 0.08, cushion - 0.02), (ez + 0.06, cushion - 0.12)], "x", sx - 0.24, sx + 0.24, seat)
        P.prism(f"{side}_cushion_in", [(back_z + 0.06, cushion + 0.002), (back_z + 0.06, cushion + 0.014),
                                       (ez - 0.02, cushion + 0.032), (ez - 0.02, cushion + 0.02)], "x", sx - 0.16, sx + 0.16,
                b.c["seat2"])
        bk = P.empty(f"{side}_backframe", (sx, cushion, back_z + 0.02), Rx(-7))
        P.box(f"{side}_back", (-0.235, 0.0, -0.14), (0.235, 0.62, 0.0), seat, parent=bk)
        seat_pattern(b, f"{side}_back_in", -0.16, 0.16, 0.08, 0.54, 0.0, parent=bk)
        if style == "headrest":
            P.box(f"{side}_headrest", (-0.13, 0.66, -0.12), (0.13, 0.84, -0.02), seat, parent=bk)
            for j, px in enumerate((-0.07, 0.07)):
                P.box(f"{side}_post{j}", (px - 0.008, 0.60, -0.08), (px + 0.008, 0.66, -0.06), b.c["metal"], parent=bk)
    if cfg.get("rear_bench", True) and L.eye[2] - m["rear"] > 1.3:
        w = L.wall - 0.06
        rz = back_z - 0.55
        P.prism("rear_bench_cushion", [(rz - 0.45, cushion - 0.14), (rz - 0.45, cushion - 0.04), (rz + 0.05, cushion - 0.02),
                                       (rz + 0.08, cushion - 0.14)], "x", -w, w, seat)
        P.prism("rear_bench_back", [(rz - 0.50, cushion - 0.06), (rz - 0.42, cushion - 0.04), (rz - 0.47, cushion + 0.48),
                                    (rz - 0.56, cushion + 0.48)], "x", -w, w, seat)
        P.box("rear_bench_frame", (-w, L.floor, rz - 0.42), (w, cushion - 0.14, rz + 0.04), dark)


def doors(b):
    k, L, cfg, m = b.k, b.L, b.cfg, b.m
    if cfg.get("door_cards", True) is False:
        return
    wins = m["windows"]
    door = max(wins, key=lambda w: w[1]) if wins else (L.eye[2] - 0.6, L.eye[2] + 0.5, m["belt"], m["win_top"])
    z0, z1 = door[0] + 0.05, min(door[1], L.face_z) - 0.02
    belt = m["belt"]
    for s in (-1, 1):
        side = "L" if s < 0 else "R"
        y0, y1 = L.floor + 0.15, belt - 0.10
        # The card leans with the door (the lining's cross-section), just inside the door panel.
        prof = k.wall_profile(y0, y1, s) if k.section_z else [(y0, k.wall()), (y1, k.wall())]

        def wall(y, prof=prof):
            return k.prof_x(prof, y) - 0.015

        outline = [(s * (wall(y) - 0.02), y) for y, _ in prof] + [(s * wall(y), y) for y, _ in reversed(prof)]
        P.prism(f"door_card_{side}", outline, "z", z0, z1, b.c["door"])
        if cfg.get("door_insert"):
            w_ = wall(belt - 0.23)
            i0, i1 = sorted((s * (w_ - 0.026), s * (w_ - 0.02)))
            P.box(f"door_insert_{side}", (i0, belt - 0.30, z0 + 0.05), (i1, belt - 0.16, z1 - 0.05), b.c[cfg["door_insert"]])
        w_ = min(wall(belt - 0.33), wall(belt - 0.28))
        a0, a1 = sorted((s * (w_ - 0.08), s * (w_ - 0.02)))
        P.box(f"armrest_{side}", (a0, belt - 0.33, z0 + 0.10), (a1, belt - 0.28, (z0 + z1) / 2 + 0.05), b.c["dark"])
        w_ = min(wall(belt - 0.22), wall(belt - 0.20))
        h0, h1 = sorted((s * (w_ - 0.035), s * (w_ - 0.02)))
        P.box(f"door_handle_{side}", (h0, belt - 0.22, z1 - 0.16), (h1, belt - 0.20, z1 - 0.06), b.c["metal"])


def floor(b):
    k, L, cfg, m = b.k, b.L, b.cfg, b.m
    w = L.wall + 0.02
    uv = k.uv("floor (lower side)", (0, L.floor + 0.15, L.eye[2]), (-1, 0, 0))
    P.box("floor", (-w, L.floor - 0.04, m["rear"]), (w, L.floor + 0.005, L.dash_front), k.paint, uv=uv)
    mat_ = b.c["carpet"] if cfg.get("carpet") else b.c["rubber"]
    mw = min(0.22, abs(L.dx) - 0.03)
    for i, x in enumerate((L.dx, -L.dx)):
        P.box(f"floor_mat{i}", (x - mw, L.floor + 0.005, L.eye[2] + 0.05), (x + mw, L.floor + 0.015, L.dash_front - 0.08), mat_)
    if cfg.get("tunnel", True):
        th = cfg.get("tunnel_h", 0.20)
        P.prism("tunnel", [(-0.17, L.floor + 0.005), (-0.11, L.floor + th), (0.11, L.floor + th), (0.17, L.floor + 0.005)],
                "z", L.eye[2] - 0.45, L.dash_front - 0.02, mat_ if cfg.get("carpet") else k.paint,
                uv=None if cfg.get("carpet") else uv)


def visors_mirror(b):
    L, ws = b.L, b.L.ws
    for i, x in enumerate((L.dx, -L.dx)):
        P.place(P.cbox(f"sun_visor{i}", (0.38, 0.018, 0.16), b.c["door"]), (x, ws["top_y"] - 0.03, ws["top_z"] - 0.12), Rx(-15))
    P.cbox("mirror_stem", (0.02, 0.06, 0.02), b.c["dark"], centre=(0, ws["top_y"] - 0.03, ws["top_z"] - 0.06))
    P.place(P.cbox("mirror", (0.22, 0.06, 0.03), b.c["dark"]), (0.0, ws["top_y"] - 0.08, ws["top_z"] - 0.07),
            Ry(8 * L.side * -1))


# ---------------------------------------------------------------- signature features

def features(b):
    k, L, cfg, m = b.k, b.L, b.cfg, b.m
    f = b.feat
    ws, fz, ft, fb = L.ws, L.face_z, L.face_top, L.face_bottom
    w = L.wall - 0.005
    cy = (ft + fb) / 2
    if "grab_bar" in f:   # chrome-less passenger grab bar on the dash (FJ40, Bronco, G-Class)
        gx0, gx1 = L.mx(0.24, min(w - 0.08, 0.64))
        gy = ft - 0.02
        k.beam("grab_bar", (gx0, gy, fz - 0.07), (gx1, gy, fz - 0.07), 0.026, 0.026, b.c["metal"] if "grab_dark" not in f else b.c["dark"])
        for i, gx in enumerate((gx0 + 0.015, gx1 - 0.015)):
            P.box(f"grab_post{i}", (gx - 0.014, gy - 0.014, fz - 0.07), (gx + 0.014, gy + 0.014, fz), b.c["metal"] if "grab_dark" not in f else b.c["dark"])
    if "vent_flaps" in f:   # Land Rover: two vent flaps under the windscreen with big handles
        for i, x in enumerate((-0.34, 0.34)):
            P.box(f"vent_flap{i}", (x - 0.16, ws["base_y"] - 0.07, ws["base_z"] - 0.06), (x + 0.16, ws["base_y"] - 0.02,
                  ws["base_z"] - 0.05), b.c["dash"] if cfg.get("dash") != "flat" else k.paint)
            P.box(f"vent_handle{i}", (x - 0.03, ws["base_y"] - 0.06, ws["base_z"] - 0.075), (x + 0.03, ws["base_y"] - 0.035,
                  ws["base_z"] - 0.06), b.c["dark"])
    if "toggles" in f:   # a row of chunky toggle switches in the middle
        for i in range(5):
            x = -0.12 + i * 0.06
            P.box(f"toggle_plate{i}", (x - 0.018, cy - 0.12, fz - 0.006), (x + 0.018, cy - 0.08, fz), b.c["dark"])
            P.cbox(f"toggle_bat{i}", (0.01, 0.01, 0.035), b.c["metal"], centre=(x, cy - 0.10, fz - 0.02))
    if "cb_radio" in f:   # 70s/80s America: CB set under the dash with its microphone on a hook
        cx = L.m(-0.12) if L.side < 0 else L.m(-0.12)
        P.box("cb_radio", (cx - 0.11, fb - 0.10, fz - 0.02), (cx + 0.11, fb - 0.04, fz + 0.14), b.c["dark"])
        P.box("cb_dial", (cx - 0.06, fb - 0.08, fz - 0.024), (cx + 0.02, fb - 0.06, fz - 0.02), b.c["accent"])
        P.place(P.cylinder("cb_knob", 0.012, 0.02, b.c["metal"], n=10, z0=-0.02), (cx + 0.06, fb - 0.07, fz - 0.02))
        P.cbox("cb_mic", (0.05, 0.075, 0.03), b.c["dark"], centre=(cx + 0.16, fb - 0.02, fz - 0.03))
    if "pine_freshener" in f:   # the little paper tree hanging from the mirror
        my, mz = ws["top_y"] - 0.17, ws["top_z"] - 0.07
        P.cbox("freshener_string", (0.003, 0.06, 0.003), b.c["metal"], centre=(0.0, my + 0.05, mz))
        tree = [(-0.025, -0.04), (0.025, -0.04), (0.012, -0.01), (0.02, -0.01), (0.006, 0.015), (0.012, 0.015),
                (0.0, 0.035), (-0.012, 0.015), (-0.006, 0.015), (-0.02, -0.01), (-0.012, -0.01)]
        P.prism("freshener_tree", [(x, my + y) for x, y in tree], "z", mz - 0.002, mz + 0.002, M("pine", (0.25, 0.62, 0.30)))
    if "inclinometer" in f:   # dash-top tilt gauge (Toyota 4WD meter); decor face, static
        pod = P.empty("incl_pod", (0.0, ft + 0.06, fz + 0.05), Ry(12 * L.side) @ Rx(15))
        P.box("incl_housing", (-0.10, -0.045, 0.0), (0.10, 0.045, 0.07), b.c["dash"], parent=pod)
        P.box("incl_visor", (-0.105, 0.045, -0.035), (0.105, 0.058, 0.07), b.c["pad"], parent=pod)
        for i, x in enumerate((-0.048, 0.048)):
            P.place(P.disc(f"incl_face{i}", 0.036, P.material("glow:incl", image="v2_incl.png", rough=0.9), n=28,
                           parent=pod), (x, 0.0, -0.002))
    if "military_radio" in f:   # Volvo Sugga / Iltis: a radio set on the passenger side
        rx = L.m(0.42)
        P.box("mil_radio", (rx - 0.17, fb - 0.20, fz - 0.24), (rx + 0.17, fb - 0.01, fz - 0.02), M("olive", (0.33, 0.36, 0.24)))
        P.box("mil_radio_face", (rx - 0.15, fb - 0.18, fz - 0.245), (rx + 0.15, fb - 0.03, fz - 0.24), b.c["dark"])
        for i, x in enumerate((-0.10, -0.03, 0.04, 0.11)):
            P.place(P.cylinder(f"mil_knob{i}", 0.016, 0.02, b.c["metal"], n=10, z0=-0.02), (rx + x, fb - 0.13, fz - 0.245))
        P.box("mil_radio_dial", (rx - 0.12, fb - 0.08, fz - 0.248), (rx + 0.02, fb - 0.05, fz - 0.245), b.c["accent"])
        P.cbox("mil_handset", (0.05, 0.16, 0.05), b.c["dark"], centre=(rx + 0.20, fb - 0.08, fz - 0.10))
    if "fire_extinguisher" in f:
        ex = L.m(0.30)
        P.place(P.cylinder("extinguisher", 0.045, 0.30, M("red", (0.85, 0.20, 0.16)), n=12, z0=0.0),
                (ex, L.floor + 0.05, L.eye[2] + 0.35), Rx(-90))
    if "roll_cage" in f:   # tubes along the pillars and across the roof behind the front seats
        cz_ = L.eye[2] - 0.45
        hw = L.wall - 0.06
        for s in (-1, 1):
            k.beam(f"cage_up{s}", (s * hw, L.floor + 0.05, cz_), (s * hw, m["roof"] - 0.07, cz_ + 0.02), 0.04, 0.04, b.c["cage"] if "cage" in b.c else b.c["dark"])
            k.beam(f"cage_side{s}", (s * hw, m["roof"] - 0.07, cz_ + 0.02), (s * (ws["half_w"] - 0.02), ws["top_y"] - 0.04,
                   ws["top_z"] - 0.10), 0.04, 0.04, b.c["cage"] if "cage" in b.c else b.c["dark"])
        k.beam("cage_cross", (-hw, m["roof"] - 0.07, cz_ + 0.02), (hw, m["roof"] - 0.07, cz_ + 0.02), 0.04, 0.04,
               b.c["cage"] if "cage" in b.c else b.c["dark"])
    if "engine_cover" in f:   # cab-over trucks and vans: engine box between the seats
        P.prism("engine_cover", [(-0.20, L.floor), (-0.18, L.floor + 0.38), (0.18, L.floor + 0.38), (0.20, L.floor)],
                "z", L.eye[2] - 0.15, fz + 0.05, b.c["dash"])
        P.box("engine_cover_pad", (-0.17, L.floor + 0.38, L.eye[2] - 0.1), (0.17, L.floor + 0.41, fz), b.c["seat"])
    if "canvas_roof" in f:   # canvas top: hoops across under the (khaki) headliner
        for i in range(3):
            z = L.eye[2] + 0.2 - i * 0.55
            k.beam(f"hoop{i}", (-L.wall + 0.04, m["roof"] - 0.05, z), (L.wall - 0.04, m["roof"] - 0.05, z), 0.03, 0.03, b.c["dark"])
    if "curtain" in f:   # camper van: checked curtain behind the front seats
        cz_ = L.eye[2] - 0.55
        for i in range(8):
            x = -L.wall + 0.05 + i * (2 * L.wall - 0.1) / 8
            P.box(f"curtain{i}", (x, m["belt"] - 0.1, cz_ - (0.02 if i % 2 else 0.0)),
                  (x + (2 * L.wall - 0.1) / 8, m["roof"] - 0.06, cz_ - (0.02 if i % 2 else 0.0) + 0.012),
                  b.c["accent"] if i % 2 else b.c["seat2"])
        k.beam("curtain_rail", (-L.wall + 0.04, m["roof"] - 0.05, cz_), (L.wall - 0.04, m["roof"] - 0.05, cz_), 0.02, 0.02,
               b.c["metal"])
    if "diff_switches" in f:   # G-Class: three chunky diff-lock buttons in the middle
        for i in range(3):
            x = -0.05 + i * 0.05
            P.box(f"diff_btn{i}", (x - 0.018, fb + 0.03, fz - 0.03), (x + 0.018, fb + 0.066, fz), M("diffbtn", (0.95, 0.78, 0.25)))
    if "console" in f:   # 80s-90s: a console between the seats with a cup well
        P.box("console", (-0.12, L.floor + 0.2, L.eye[2] - 0.35), (0.12, L.floor + 0.42, L.eye[2] + 0.2), b.c["dash"])
        P.box("console_lid", (-0.115, L.floor + 0.42, L.eye[2] - 0.34), (0.115, L.floor + 0.45, L.eye[2] - 0.05), b.c["seat"])
    if "overhead_console" in f:   # luxury wagon: overhead console with a compass window
        P.box("overhead", (-0.14, m["roof"] - 0.07, ws["top_z"] - 0.40), (0.14, m["roof"] - 0.01, ws["top_z"] - 0.12), b.c["dash"])
        P.box("overhead_window", (-0.05, m["roof"] - 0.075, ws["top_z"] - 0.30), (0.05, m["roof"] - 0.07, ws["top_z"] - 0.22),
              b.c["accent"])
    if "dash_tray" in f:   # a work truck's open tray on the passenger side of the dash top
        tx0, tx1 = L.mx(0.20, w - 0.08)
        P.box("tray_floor", (tx0, ft + 0.005, fz - 0.02), (tx1, ft + 0.012, fz + 0.12), b.c["rubber"])
        P.box("tray_lip", (tx0, ft + 0.012, fz - 0.025), (tx1, ft + 0.04, fz - 0.012), b.c["dash"])
    if "winch_lever" in f:   # Power Wagon: PTO lever for the front winch, by the gear lever
        k.lever("winch_lever", (L.m(0.17), L.floor + cfg.get("tunnel_h", 0.20), L.eye[2] + 0.18), 0.40, 18, 0.03,
                b.c["knob3"], boot=0.04, shaft_r=0.011)
    if "fj_bits" in f:   # FJ40 / FJ45: closed copies of the hood box and the wipers (measured by hand)
        P.prism("hood_box", [(0.416, 1.356), (0.416, 1.462), (0.43, 1.477), (0.485, 1.477), (0.498, 1.462),
                             (0.498, 1.356)], "x", -0.617, -0.316, b.c["dark"])
        for i, (x0, x1) in enumerate(((-0.584, -0.150), (-0.044, 0.391))):
            P.box(f"wiper_blade{i}", (x0, 1.536, 0.392), (x1, 1.568, 0.418), b.c["dark"])
        for i, (x0, x1) in enumerate(((-0.043, -0.307), (0.498, 0.234))):
            k.beam(f"wiper_arm{i}", (x0, 1.39, 0.418), (x1, 1.555, 0.418), 0.014, 0.012, b.c["dark"])
    if "wood_lining" in f:   # woodie: wooden roof bows
        for i in range(3):
            z = L.eye[2] + 0.1 - i * 0.5
            k.beam(f"wood_bow{i}", (-L.wall + 0.04, m["roof"] - 0.04, z), (L.wall - 0.04, m["roof"] - 0.04, z), 0.05, 0.025,
                   b.c["wood"])


# ---------------------------------------------------------------- the whole cockpit

def soften(skip_prefix=("lining_", "body_bits", "wiper_copies", "header")):
    """One small rounded edge on every closed part, like the game's own models."""
    for ob in list(bpy.context.scene.objects):
        if ob.type != "MESH" or ob.name.startswith(skip_prefix) or ob.name.endswith("_body"):
            continue
        if len(ob.data.polygons) > 120 or any(t in ob.name for t in ("_face", "lamp_", "gear_display", "needle", "badge")):
            continue
        bv = ob.modifiers.new("soft", "BEVEL")
        bv.width, bv.segments, bv.limit_method = 0.005, 2, "ANGLE"
        bv.angle_limit = math.radians(35)


def build(k, cfg):
    """One car's cockpit. Returns the Layout (eye, wheel, dash positions)."""
    # The wheel half a metre below the eye (the approved DingDing's) and 44 cm across: at 47 cm / 40 cm
    # its upper opening was too small to read the dials through.
    cfg = dict(dict(wheel_drop=0.50, wheel_r=0.22), **cfg)
    cab = styles.find_cab(k)
    probe = (0.4 * cfg.get("side", -1), cab[1] if cab else 1.4, (cab[0] - 0.35) if cab else -0.3)
    m0 = k.measure(probe)
    ws = m0["ws"]
    eye_guess = (0.42 * cfg.get("side", -1), cfg.get("eye_y", min(ws["base_y"] + 0.27, m0["roof"] - 0.32)),
                 cfg.get("eye_z", max(ws["base_z"] - 0.85, m0["rear"] + 0.40)))
    m = k.measure(eye_guess)
    ws = m["ws"]
    ws.update(cfg.get("ws", {}))   # measured by hand where the rays get it wrong (wipers lying across the glass)
    # The measured top of the windscreen tends to come out low, which hangs a big header slab into the
    # view: keep the header at most 11 cm deep.
    ws["top_y"] = max(ws["top_y"], m["roof"] - 0.11)
    # Side windows at head height only (no tail lights, no wrapped windscreen corners); the belt line and
    # window tops from those. And ONE cabin half-width for all lining (the per-spot wall probes of the kit
    # catch roof rails and the like inside the body and then line the cabin far too narrow).
    ey_ = cfg.get("eye_y", min(ws["base_y"] + 0.27, m["roof"] - 0.32))
    ez_ = cfg.get("eye_z", max(ws["base_z"] - 0.85, m["rear"] + 0.40))
    wins = [w_ for w_ in m["windows"] if w_[0] < ws["top_z"] - 0.05 and w_[2] < ey_ - 0.05 < w_[3] and w_[3] - w_[2] > 0.2]
    if wins:
        m["windows"], m["belt"], m["win_top"] = wins, min(w_[2] for w_ in wins), max(w_[3] for w_ in wins)
    hits = []
    for s_ in (-1, 1):
        for i in range(5):
            for j in range(5):
                p_, _, _ = k.sampler.hit((0.0, m["belt"] - 0.25 + 0.05 * i, ez_ - 0.3 + 0.15 * j), (s_, 0, 0))
                if p_ is not None and abs(p_.x) > 0.45:
                    hits.append(abs(p_.x))
    hits.sort()
    half = cfg.get("cabin_half", hits[len(hits) // 2] if hits else 0.85)
    k.wall = lambda *a_, **kw_: half
    # The cross-section the side lining follows (kit.wall_x), measured along the front door.
    k.half = half
    door_win = max(m["windows"], key=lambda w_: w_[1]) if m["windows"] else (ez_ - 0.5, ez_ + 0.3)
    k.section_z = (door_win[0] + 0.05, min(door_win[1], ws["base_z"] - 0.05) - 0.05)
    print(f"v2 cabin: half width {half:.3f}, belt {m['belt']:.3f}, window top {m['win_top']:.3f}, windows {len(m['windows'])}")
    L = styles.Layout(k, m, cfg)
    b = B(k, L, cfg, m)
    # Flat game-style versions of the kit's shared materials.
    k.chrome, k.black, k.rubber = b.c["metal"], b.c["dark"], b.c["rubber"]
    P.empty("eye", L.eye)
    # Side walls only back from the front side window: traced along the slanted A pillar they come out
    # saw-toothed. A plain post fills the corner instead.
    doors_ = m["windows"]
    win_front = max((w_[1] for w_ in doors_), default=ws["base_z"] - 0.3)
    # Plain boxes (doors, pillars between the windows, roof edges, header, headliner, rear wall): the traced
    # surfaces of kit.auto_lining come out saw-toothed along slanted window edges, which reads badly.
    # (Between the A pillar beam and the door window the outside shows through: it reads as glass.)
    k.lining(dict(m, windows=doors_ or m["windows"]), b.c["liner"], front_z=win_front + 0.02)
    if "body_bits" in b.feat:
        k.body_bits(m)
    if "fj_bits" not in b.feat:   # (the FJs have hand-made closed wipers)
        k.wiper_copies(m)
    import signatures_v2
    sig = signatures_v2.SIGS.get(k.car)
    if sig:   # hand-composed dash, instruments and props for this car
        signatures_v2.structure(b)
        sig(b)
    else:
        dash(b)
        centre_stack(b)
        with cluster(b):
            instruments(b)
    wheel(b)
    pedals_levers(b)
    floor(b)
    seats(b)
    doors(b)
    visors_mirror(b)
    features(b)
    soften()
    return L
