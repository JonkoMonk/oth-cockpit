# v2 SIGNATURE cockpits: one hand-composed function per car, so no two cockpits share a dash shape,
# an instrument layout, a centre stack or their props. styles_v2.build calls SIGS[car](b) instead of the
# generic dash / centre stack / instruments; lining, floor, pedals, levers, wheel, seats and doors stay
# generic (tuned per car in cars_v2.py) and the props here sit on top of them.
#
# Every car still has all the parts the mod drives (tacho, speedo, fuel, temp needles, the four lamps,
# the gear display); they are only arranged differently. Props have no drives.
# Positions come from the measured Layout (L), never from fixed numbers, except where noted.
import math

import bpy

import parts as P
from parts import Rx, Ry, Rz
from styles_v2 import M, cluster, gauge, gear_display, hub_y, lamps, opening_y

# ---------------------------------------------------------------- context and shared bits


class C:
    """Short names for one car's layout."""

    def __init__(self, b):
        L = b.L
        self.b, self.k, self.L = b, b.k, L
        self.fz, self.ft, self.fb = L.face_z, L.face_top, L.face_bottom
        self.top, self.front = L.top_y, L.dash_front
        self.w = L.wall - 0.005
        self.dx = L.dx
        self.cy = (self.ft + self.fb) / 2
        self.side = L.side

    def p(self, d):
        """x at distance d from the centre line towards the passenger."""
        return self.L.m(d)

    def px(self, a, b):
        return tuple(sorted((self.p(a), self.p(b))))

    def thru_y(self, z, r):
        """Dial centre height read through the top opening of the wheel: the whole dial (ring included)
        hangs below the line over the rim, so the rim never crosses it."""
        return min(self.ft - r - 0.03, self.L.sight_y(z) - r - 0.03)

    def thru(self, z, *dials):
        """One centre height for dials [(x, r), ...] (r without the ring) so they all sit inside the wheel's
        upper opening, seen from the eye."""
        return min(opening_y(self.b, x, r + 0.012, z) for x, r in dials)

    def open_y(self, x, r, z):
        """Highest centre height inside the wheel opening for one instrument of outer radius r."""
        return opening_y(self.b, x, r, z)

    def hub(self, z):
        """Line over the wheel hub at depth z: instruments in the opening stay above it."""
        return hub_y(self.b, z)

    def over_y(self, z, r):
        """Dial centre height read over the wheel rim."""
        return min(self.top - r - 0.01, self.L.sight_y(z) + r + 0.015)

    def paint(self):
        return self.k.paint, self.b.dash_uv()


def structure(b):
    """Firewall, kick panels and the dark underside: every car needs these, they're never seen much."""
    c = C(b)
    k, L = c.k, c.L
    P.box("firewall", (-c.w, L.floor, c.front), (c.w, c.fb, c.front + 0.04), k.paint,
          uv=k.uv("firewall", (0, L.ws["base_y"] - 0.2, L.ws["base_z"] + 0.5), (0, 1, 0)))
    for s in (-1, 1):
        P.box(f"kick_{s}", (min(s * (c.w - 0.06), s * c.w), L.floor, c.fz + 0.05), (max(s * (c.w - 0.06), s * c.w), c.fb, c.front),
              k.paint, uv=k.uv("kick", (0, L.floor + 0.15, L.eye[2]), (s, 0, 0)))
    if c.front - 0.1 > c.fz + 0.06:
        P.box("dash_under", (-c.w, c.fb - 0.035, c.fz + 0.01), (c.w, c.fb - 0.02, c.front - 0.1), b.c["dark"])


def body(c, name, prof, mat, uv=None, x0=None, x1=None):
    """A dash piece across the car: profile (z, y) points extruded along x."""
    return P.prism(name, prof, "x", -c.w if x0 is None else x0, c.w if x1 is None else x1, mat, uv=uv)


def can(c, name, x, y, z, r, depth, mat, n=24):
    """Round housing standing out of a face towards the driver (z = the face it stands on)."""
    P.place(P.cylinder(name, r, depth, mat, n=n, z0=-depth), (x, y, z))
    return z - depth


def dial(c, kind, x, y, z, r, housing=None, depth=0.03, ring="metal"):
    """A dial, optionally in its own can (housing colour name)."""
    if housing:
        z = can(c, kind + "_can", x, y, z, r + 0.012, depth, c.b.c[housing]) - 0.001
    gauge(c.b, kind, x, y, r, z, ring=ring)
    return z


def plate(c, name, x0, x1, y0, y1, z, mat, depth=0.012):
    """A flat panel on a face (z = the face it sits on), towards the driver."""
    return P.box(name, (x0, y0, z - depth), (x1, y1, z + 0.002), mat)


def knob_row(c, name, xs, y, z, mat, r=0.012, length=0.02):
    for i, x in enumerate(xs):
        P.place(P.cylinder(f"{name}{i}", r, length, mat, n=10, z0=-length), (x, y, z))


def toggles(c, name, xs, y, z, plate_mat, bat_mat):
    for i, x in enumerate(xs):
        P.box(f"{name}_plate{i}", (x - 0.018, y - 0.02, z - 0.006), (x + 0.018, y + 0.02, z + 0.001), plate_mat)
        P.cbox(f"{name}_bat{i}", (0.01, 0.01, 0.035), bat_mat, centre=(x, y, z - 0.022))


def slots(c, name, x0, x1, y0, y1, z, n, mat, vertical=True):
    """Speaker grille / vent: n slots on a face."""
    for i in range(n):
        if vertical:
            xa = x0 + (x1 - x0) * (i + 0.2) / n
            P.box(f"{name}{i}", (xa, y0, z - 0.004), (xa + (x1 - x0) * 0.55 / n, y1, z + 0.001), mat)
        else:
            ya = y0 + (y1 - y0) * (i + 0.2) / n
            P.box(f"{name}{i}", (x0, ya, z - 0.004), (x1, ya + (y1 - y0) * 0.55 / n, z + 0.001), mat)


def lamp_row(c, x, y, z, step=0.032, r=0.012, order=("handbrake", "engine", "headlights", "lowrange")):
    lamps(c.b, {n: x + (i - 1.5) * step for i, n in enumerate(order)}, y, z, r=r)


def lamp_col(c, x, y, z, step=0.032, r=0.012, order=("handbrake", "engine", "headlights", "lowrange"), parent=None):
    lamps(c.b, {n: x for n in order}, 0, z, parent=parent, r=r)
    import bpy
    for i, n in enumerate(order):
        ob = bpy.data.objects["lamp_" + n]
        ob.location.z = y - i * step    # Blender z = game y


def seat_dims(c):
    L = c.L
    ey, ez = L.eye[1], L.eye[2]
    cushion = max(L.floor + 0.30, ey - c.b.cfg.get("seat_below_eye", 0.78))
    return cushion, ez - c.b.cfg.get("back_behind_eye", 0.36)


# ---------------------------------------------------------------- props (low-poly, flat colours)

def thermos(c, x, y, z):
    P.place(P.cylinder("thermos", 0.04, 0.26, M("thermos", (0.25, 0.48, 0.42)), n=10), (x, y, z), Rx(-90))
    P.place(P.cylinder("thermos_cap", 0.042, 0.06, M("thermos_cap", (0.80, 0.78, 0.72)), n=10), (x, y + 0.26, z), Rx(-90))


def mug(c, name, x, y, z, col=(0.86, 0.36, 0.22)):
    P.place(P.cylinder(name, 0.04, 0.09, M(name, col), n=10), (x, y, z), Rx(-90))
    P.place(P.torus(name + "_handle", 0.025, 0.007, M(name, col), n=10, m=5), (x + 0.045, y + 0.045, z), Ry(90))


def gloves(c, x, y, z, rot=20):
    g = M("gloves", (0.78, 0.62, 0.36))
    for i in range(2):
        P.place(P.cbox(f"glove{i}", (0.10, 0.025, 0.17), g), (x + i * 0.06, y + i * 0.025, z - i * 0.03), Ry(rot + i * 25))


def clipboard(c, x, y, z, rot=8):
    P.place(P.cbox("clipboard", (0.22, 0.012, 0.30), M("board", (0.66, 0.48, 0.30))), (x, y, z), Ry(rot))
    P.place(P.cbox("clip_paper", (0.19, 0.004, 0.24), M("paper", (0.95, 0.93, 0.88))), (x, y + 0.008, z - 0.01), Ry(rot))


def map_sheet(c, name, x, y, z, rot=15, w=0.30, d=0.22):
    P.place(P.cbox(name, (w, 0.006, d), M("map", (0.92, 0.86, 0.66))), (x, y, z), Ry(rot))
    P.place(P.cbox(name + "_trail", (w * 0.8, 0.002, 0.012), M("map_trail", (0.82, 0.30, 0.20))), (x, y + 0.004, z), Ry(rot + 25))


def toolbox(c, x, y, z):
    P.box("toolbox", (x - 0.20, y, z - 0.10), (x + 0.20, y + 0.16, z + 0.10), M("toolbox", (0.82, 0.22, 0.16)))
    P.cbox("toolbox_handle", (0.24, 0.03, 0.03), c.b.c["dark"], centre=(x, y + 0.19, z))


def jerrycan(c, x, y, z):
    P.box("jerrycan", (x - 0.08, y, z - 0.18), (x + 0.08, y + 0.44, z + 0.18), M("jerry", (0.30, 0.38, 0.22)))
    P.box("jerry_handle", (x - 0.03, y + 0.44, z + 0.04), (x + 0.03, y + 0.47, z + 0.16), c.b.c["dark"])


def picnic_basket(c, x, y, z):
    wick = M("wicker", (0.74, 0.54, 0.30))
    P.box("basket", (x - 0.18, y, z - 0.12), (x + 0.18, y + 0.16, z + 0.12), wick)
    P.box("basket_lid", (x - 0.185, y + 0.16, z - 0.125), (x + 0.185, y + 0.18, z + 0.125), M("wicker_dark", (0.60, 0.42, 0.22)))
    P.place(P.torus("basket_handle", 0.10, 0.01, wick, n=16, m=5), (x, y + 0.18, z), Rx(90) @ Rz(0))


def compass_ball(c, x, y, z):
    P.place(P.cylinder("compass_base", 0.035, 0.015, c.b.c["dark"], n=12), (x, y, z), Rx(-90))
    P.place(P.ball("compass", 0.035, M("compass_glass", (0.20, 0.22, 0.26)), rings=6, segs=10), (x, y + 0.05, z))
    P.place(P.cbox("compass_card", (0.05, 0.004, 0.004), c.b.c["accent"]), (x, y + 0.05, z - 0.03))


def sheepskin(c, x, cushion, back_z, w=0.23):
    wool = M("wool", (0.90, 0.84, 0.72))
    P.box(f"wool_seat{x:.2f}", (x - w, cushion + 0.015, back_z + 0.02), (x + w, cushion + 0.06, c.L.eye[2] + 0.05), wool)
    bk = P.empty(f"wool_backframe{x:.2f}", (x, cushion, back_z + 0.02), Rx(-7))
    P.box(f"wool_back{x:.2f}", (-w, 0.04, 0.0), (w, 0.62, 0.05), wool, parent=bk)


def beads(c, x, cushion, back_z):
    bead_a, bead_b = M("bead_a", (0.60, 0.44, 0.24)), M("bead_b", (0.40, 0.28, 0.16))
    bk = P.empty(f"beads_frame{x:.2f}", (x, cushion, back_z + 0.02), Rx(-7))
    for i in range(6):
        for j in range(8):
            P.place(P.ball(f"bead{x:.2f}_{i}_{j}", 0.018, bead_a if (i + j) % 2 else bead_b, parent=bk, rings=4, segs=6),
                    (-0.16 + i * 0.064, 0.10 + j * 0.065, 0.02))


def cassette_deck(c, name, x, y, z, w=0.18):
    P.box(name, (x - w / 2, y - 0.03, z - 0.02), (x + w / 2, y + 0.03, z + 0.002), c.b.c["dark"])
    P.box(name + "_slot", (x - w * 0.3, y + 0.0, z - 0.024), (x + w * 0.3, y + 0.018, z - 0.02), M("deck_slot", (0.05, 0.05, 0.06)))
    for i in range(5):
        P.box(f"{name}_btn{i}", (x - w * 0.4 + i * w * 0.18, y - 0.024, z - 0.03), (x - w * 0.4 + i * w * 0.18 + w * 0.12, y - 0.01, z - 0.02),
              c.b.c["metal"])
    P.box(name + "_display", (x + w * 0.32, y + 0.0, z - 0.022), (x + w * 0.46, y + 0.02, z - 0.02), c.b.c["accent"])


def clock(c, name, x, y, z, r=0.035):
    P.place(P.disc(name, r, M("clock_face", (0.94, 0.90, 0.80)), n=24), (x, y, z))
    P.place(P.torus(name + "_ring", r + 0.004, 0.005, c.b.c["metal"], n=24, m=5), (x, y, z))
    P.place(P.cbox(name + "_hour", (0.005, r * 0.55, 0.002), c.b.c["dark"]), (x, y + r * 0.2, z - 0.003), Rz(-60))
    P.place(P.cbox(name + "_min", (0.004, r * 0.8, 0.002), c.b.c["dark"]), (x, y + r * 0.3, z - 0.004), Rz(20))


def handset(c, x, y, z):
    P.cbox("handset", (0.05, 0.17, 0.05), c.b.c["dark"], centre=(x, y, z))
    P.cbox("handset_ear", (0.06, 0.04, 0.06), c.b.c["dark"], centre=(x, y + 0.09, z - 0.01))


# ---------------------------------------------------------------- one function per car


def burro(b):
    """FJ45 work pickup: painted steel like the Ding but bare and practical. One flat visor over a line of
    five dials, a blanking plate where a radio would be, clipboard and gloves in the dash tray, toolbox on
    the bench."""
    c = C(b)
    pm, uv = c.paint()
    body(c, "dash_body", [(c.fz + 0.02, c.fb - 0.02), (c.fz, c.fb), (c.fz, c.ft), (c.fz + 0.05, c.ft + 0.01), (c.front, c.top),
                          (c.front + 0.02, c.fb - 0.02)], pm, uv)
    z = c.fz - 0.002
    zz = z - 0.013
    # Big dials in the wheel's opening, the small ones lower out at the sides where the rim curves down,
    # lamps and the gear display in a row under the big dials (above the hub).
    # Big dials in the wheel's opening (the T wheel leaves no room under them), small dials outside the
    # rim at the ends of the strip with two lamps under each, the gear display at the far end.
    y = min(c.ft - 0.095, c.thru(zz, (c.dx - 0.08, 0.062), (c.dx + 0.08, 0.062)))
    with cluster(b):
        sx0, sx1 = sorted((c.dx - c.p(0.34), c.dx + c.p(0.40)))
        plate(c, "gauge_strip", sx0, sx1, y - 0.09, y + 0.085, z, b.c["panel"])
        P.box("gauge_visor", (sx0 - 0.02, y + 0.085, c.fz - 0.07), (sx1 + 0.02, y + 0.10, c.fz), pm, uv=uv)
        gauge(b, "speedo", c.dx - 0.08, y, 0.062, zz)
        gauge(b, "tacho", c.dx + 0.08, y, 0.062, zz)
        gauge(b, "fuel", c.dx - 0.29, y, 0.038, zz)
        gauge(b, "temp", c.dx + 0.29, y, 0.038, zz)
        lamps(b, {"handbrake": c.dx - 0.31, "engine": c.dx - 0.27, "headlights": c.dx + 0.27, "lowrange": c.dx + 0.31},
              y - 0.066, zz, r=0.01)
        gear_display(b, c.dx + c.p(0.365), y, zz, size=0.03)
    plate(c, "radio_blank", -0.10, 0.10, c.cy - 0.04, c.cy + 0.03, c.fz, pm, depth=0.004)
    knob_row(c, "blank_screw", (-0.085, 0.085), c.cy - 0.005, c.fz - 0.004, b.c["metal"], r=0.006, length=0.004)
    knob_row(c, "pull_knob", (-0.06, 0.0, 0.06), c.cy - 0.10, c.fz, b.c["knob"], r=0.013, length=0.03)
    tx0, tx1 = c.px(0.18, c.w - 0.06)
    P.box("tray_floor", (tx0, c.ft + 0.005, c.fz - 0.02), (tx1, c.ft + 0.012, c.fz + 0.14), b.c["rubber"])
    P.box("tray_lip", (tx0, c.ft + 0.012, c.fz - 0.03), (tx1, c.ft + 0.045, c.fz - 0.015), pm, uv=uv)
    clipboard(c, (tx0 + tx1) / 2 - 0.06 * c.side, c.ft + 0.02, c.fz + 0.05, rot=8)
    gloves(c, (tx0 + tx1) / 2 + 0.12 * -c.side, c.ft + 0.03, c.fz + 0.03)
    cushion, back_z = seat_dims(c)
    toolbox(c, c.p(0.45), cushion + 0.02, c.L.eye[2] - 0.15)


def protector(b):
    """Defender 90: black plastic, a deep parcel shelf right across under the dash top, the binnacle pod
    over the wheel, a tall centre console down to the floor with the heater sliders, and the lockable
    cubby box between the seats."""
    c = C(b)
    d = b.c["dash"]
    body(c, "dash_top", [(c.fz - 0.06, c.ft - 0.02), (c.fz - 0.06, c.ft + 0.02), (c.front, c.top), (c.front, c.ft - 0.02)], d)
    body(c, "shelf", [(c.fz - 0.16, c.fb + 0.04), (c.fz - 0.16, c.fb + 0.08), (c.fz - 0.14, c.fb + 0.08), (c.fz - 0.14, c.fb + 0.06),
                      (c.fz + 0.10, c.fb + 0.06), (c.fz + 0.10, c.fb + 0.04)], b.c["panel"])
    P.box("shelf_back", (-c.w, c.fb + 0.04, c.fz + 0.08), (c.w, c.ft - 0.02, c.fz + 0.12), d)
    # Binnacle on top, read over the wheel.
    z = c.fz - 0.07
    y = max(c.L.sight_y(z) + 0.075, c.ft + 0.02)
    pod = P.empty("binnacle", (c.dx, y, z), Rx(16))   # read over the wheel: already clear, not slid
    P.box("pod_housing", (-0.215, -0.085, 0.0), (0.215, 0.095, 0.12), d, parent=pod)
    P.box("pod_visor", (-0.225, 0.095, -0.06), (0.225, 0.115, 0.12), b.c["pad"], parent=pod)
    gauge(b, "speedo", -0.077, 0.01, 0.062, -0.002, pod)
    gauge(b, "tacho", 0.077, 0.01, 0.062, -0.002, pod)
    gauge(b, "fuel", -0.168, -0.058, 0.025, -0.002, pod)
    gauge(b, "temp", 0.168, -0.058, 0.025, -0.002, pod)
    lamps(b, {"handbrake": -0.20, "engine": -0.172, "headlights": 0.172, "lowrange": 0.20}, 0.08, -0.002, pod, r=0.01)
    gear_display(b, 0.0, -0.065, -0.002, pod, size=0.028)
    # Centre console from the dash down to the floor.
    L = c.L
    P.prism("console_stack", [(-0.12, L.floor + 0.2), (-0.12, c.ft - 0.04), (0.12, c.ft - 0.04), (0.12, L.floor + 0.2)], "z",
            c.fz - 0.14, c.fz + 0.06, d)
    for i in range(3):
        x = -0.06 + i * 0.06
        P.box(f"heater_slot{i}", (x - 0.008, c.cy - 0.06, c.fz - 0.145), (x + 0.008, c.cy + 0.06, c.fz - 0.14), b.c["dark"])
        P.box(f"heater_tab{i}", (x - 0.016, c.cy - 0.02 + i * 0.03, c.fz - 0.17), (x + 0.016, c.cy + i * 0.03, c.fz - 0.1415), b.c["knob3"] if i == 1 else b.c["metal"])
    cassette_deck(c, "radio", 0.0, c.fb - 0.03, c.fz - 0.14, w=0.17)
    P.box("cubby_box", (-0.16, L.floor + 0.25, L.eye[2] - 0.40), (0.16, L.floor + 0.48, L.eye[2] - 0.02), d)
    P.box("cubby_lid", (-0.165, L.floor + 0.48, L.eye[2] - 0.405), (0.165, L.floor + 0.50, L.eye[2] - 0.015), b.c["seat"])
    mug(c, "mug", c.p(0.40), c.fb + 0.065, c.fz - 0.05, col=(0.30, 0.42, 0.30))


def tinny(b):
    """Series IIA: a bare painted fascia with a long shelf; the instruments in an oval panel in the middle,
    starter button and choke pull beside them, a row of bolt heads, a tin mug on the shelf."""
    c = C(b)
    pm, uv = c.paint()
    P.box("fascia", (-c.w, c.fb + 0.05, c.fz), (c.w, c.ft - 0.04, c.fz + 0.025), pm, uv=uv)
    body(c, "shelf", [(c.fz - 0.20, c.fb + 0.05), (c.fz - 0.20, c.fb + 0.075), (c.fz + 0.02, c.fb + 0.075), (c.fz + 0.02, c.fb + 0.05)],
         pm, uv)
    P.box("shelf_lip", (-c.w + 0.02, c.fb + 0.075, c.fz - 0.205), (c.w - 0.02, c.fb + 0.10, c.fz - 0.19), pm, uv=uv)
    body(c, "top_rail", [(c.fz - 0.02, c.ft - 0.04), (c.fz - 0.02, c.ft), (c.front, c.top), (c.front, c.ft - 0.04)], pm, uv)
    cy = c.ft - 0.13
    with cluster(b, hi=c.ft - 0.045):
        oval = P.cylinder("oval_panel", 0.11, 0.015, b.c["panel"], n=28, z0=-0.015)
        P.place(oval, (0.0, cy, c.fz))
        oval.scale = (2.3, 1.0, 1.0)
        z = c.fz - 0.017
        gauge(b, "speedo", -0.10, cy, 0.072, z, ring="dark")
        gauge(b, "fuel", 0.03, cy + 0.044, 0.03, z, ring="dark")
        gauge(b, "temp", 0.03, cy - 0.044, 0.03, z, ring="dark")
        gauge(b, "tacho", 0.15, cy, 0.045, z, ring="dark")
        # Lamps and the gear display on the fascia under the oval.
        lamp_row(c, -0.10, cy - 0.128, c.fz - 0.002, step=0.028, r=0.01)
        gear_display(b, 0.03, cy - 0.128, c.fz - 0.002, size=0.03)
    knob_row(c, "starter", (-0.30,), cy - 0.02, c.fz, b.c["knob2"], r=0.016, length=0.025)
    knob_row(c, "choke", (0.30,), cy - 0.04, c.fz, b.c["knob"], r=0.012, length=0.05)
    knob_row(c, "bolt", [(-c.w + 0.08) + i * (2 * c.w - 0.16) / 9 for i in range(10)], c.ft - 0.055, c.fz, b.c["dark"],
             r=0.007, length=0.006)
    mug(c, "tin_mug", c.p(0.35), c.fb + 0.075, c.fz - 0.10, col=(0.82, 0.84, 0.80))


def trailrat(b):
    """Scout 800: flat painted dash with a raised rectangular gauge pod in front of the driver, a slim old
    AM radio with big push buttons, and a compass ball stuck on top of the dash."""
    c = C(b)
    pm, uv = c.paint()
    body(c, "dash_body", [(c.fz, c.fb - 0.02), (c.fz, c.ft), (c.fz + 0.02, c.ft + 0.02), (c.front, c.top), (c.front, c.fb - 0.02)], pm, uv)
    z = c.fz - 0.05
    zz = z - 0.005
    y = c.thru(zz, (c.dx, 0.064))
    with cluster(b):
        # Speedo in the middle, the small dials in a row either side, lamps under the speedo.
        P.box("gauge_pod", (c.dx - 0.30, y - 0.115, z), (c.dx + 0.30, y + 0.085, c.fz), pm, uv=uv)
        plate(c, "gauge_face", c.dx - 0.28, c.dx + 0.28, y - 0.105, y + 0.07, z, b.c["panel"], depth=0.004)
        gauge(b, "speedo", c.dx, y, 0.064, zz)
        gauge(b, "fuel", c.dx - 0.13, y, 0.034, zz)
        gauge(b, "temp", c.dx + 0.13, y, 0.034, zz)
        gauge(b, "tacho", c.dx - 0.225, y, 0.034, zz)
        lamp_row(c, c.dx, y - 0.093, zz, step=0.026, r=0.009)
        gear_display(b, c.dx + 0.225, y, zz, size=0.032)
    rx = c.p(0.0)
    P.box("am_radio", (rx - 0.13, c.cy - 0.03, c.fz - 0.02), (rx + 0.13, c.cy + 0.03, c.fz + 0.002), b.c["panel"])
    for i in range(5):
        P.box(f"am_btn{i}", (rx - 0.10 + i * 0.045, c.cy - 0.022, c.fz - 0.045), (rx - 0.07 + i * 0.045, c.cy + 0.006, c.fz - 0.02),
              M("am_btn", (0.92, 0.88, 0.78)))
    P.box("am_window", (rx - 0.10, c.cy + 0.01, c.fz - 0.022), (rx + 0.12, c.cy + 0.025, c.fz - 0.02), b.c["accent"])
    compass_ball(c, c.dx + c.p(0.32), c.ft + 0.025, c.fz + 0.06)
    knob_row(c, "pull", (c.p(0.32), c.p(0.40)), c.cy - 0.08, c.fz, b.c["knob"], r=0.012, length=0.03)


def bull(b):
    """Early Bronco: painted steel with a padded top, the wide horizontal oval dial band with a bright trim
    ring, a speaker grille in the middle instead of a radio, a passenger grab bar and a column shifter."""
    c = C(b)
    pm, uv = c.paint()
    body(c, "dash_body", [(c.fz + 0.02, c.fb - 0.02), (c.fz, c.fb), (c.fz, c.ft), (c.fz + 0.03, c.ft + 0.02), (c.front, c.top),
                          (c.front + 0.02, c.fb - 0.02)], pm, uv)
    body(c, "crash_pad", [(c.fz + 0.01, c.ft - 0.02), (c.fz - 0.03, c.ft), (c.fz - 0.02, c.ft + 0.03), (c.fz + 0.05, min(c.ft + 0.04, c.top)),
                          (c.front, c.top - 0.002), (c.front, c.ft - 0.02)], b.c["pad"])
    z = c.fz
    zz = z - 0.027
    y = c.thru(zz, (c.dx - 0.065, 0.06), (c.dx + 0.07, 0.05))
    with cluster(b, hi=c.ft - 0.03):   # stays under the crash pad's overhang
        band = P.cylinder("oval_band", 0.10, 0.025, b.c["panel"], n=28, z0=-0.025)
        P.place(band, (c.dx, y, z))
        band.scale = (3.0, 1.0, 1.0)
        trim = P.torus("oval_trim", 0.10, 0.007, b.c["metal"], n=36, m=6)
        P.place(trim, (c.dx, y, z - 0.025))
        trim.scale = (3.0, 1.0, 1.0)
        gauge(b, "speedo", c.dx - 0.065, y, 0.06, zz)
        gauge(b, "tacho", c.dx + 0.073, y, 0.05, zz)
        gauge(b, "fuel", c.dx - 0.20, y - 0.012, 0.032, zz)
        gauge(b, "temp", c.dx + 0.20, y - 0.012, 0.032, zz)
        # Lamps in pairs beside the ends of the band (outside the rim), the gear display under one end.
        lamps(b, {"handbrake": c.dx - 0.345, "headlights": c.dx + 0.345}, y + 0.017, c.fz - 0.001, r=0.01)
        lamps(b, {"engine": c.dx - 0.345, "lowrange": c.dx + 0.345}, y - 0.017, c.fz - 0.001, r=0.01)
        gear_display(b, c.dx - 0.345, y - 0.065, c.fz - 0.001, size=0.03)
    slots(c, "speaker", *c.px(0.05, 0.25), c.cy - 0.05, c.cy + 0.03, c.fz, 9, b.c["dark"])
    knob_row(c, "heater", (-0.07, 0.0, 0.07), c.cy - 0.10, c.fz, b.c["metal"], r=0.012, length=0.02)
    gx0, gx1 = c.px(0.24, min(c.w - 0.08, 0.62))
    c.k.beam("grab_bar", (gx0, c.ft - 0.025, c.fz - 0.07), (gx1, c.ft - 0.025, c.fz - 0.07), 0.026, 0.026, b.c["metal"])
    for i, gx in enumerate((gx0 + 0.015, gx1 - 0.015)):
        P.box(f"grab_post{i}", (gx - 0.014, c.ft - 0.04, c.fz - 0.07), (gx + 0.014, c.ft - 0.01, c.fz), b.c["metal"])


def trailburner(b):
    """Square-body K5 Blazer: a big moulded plastic dash, four square gauges in a long hooded cluster, a
    vertical heater slider panel, a wide padded horn bar on the wheel, the CB on a bracket under the dash
    and a paper pine tree on the mirror."""
    c = C(b)
    d = b.c["dash"]
    body(c, "dash_body", [(c.fz + 0.03, c.fb - 0.03), (c.fz, c.fb), (c.fz - 0.01, c.ft - 0.02), (c.fz + 0.02, c.ft + 0.02),
                          (c.front, c.top), (c.front + 0.02, c.fb - 0.03)], d)
    z = c.fz - 0.05
    top = min(c.ft + 0.02, c.top - 0.03)
    zz = z - 0.003
    y = min(top - 0.10, c.thru(zz, (c.dx - 0.085, 0.063), (c.dx + 0.085, 0.063)))
    with cluster(b, hi=top + 0.05):
        P.box("cluster_box", (c.dx - 0.36, min(top - 0.20, y - 0.135), z), (c.dx + 0.36, top, c.fz), d)
        P.prism("cluster_hood", [(z - 0.06, top + 0.02), (z - 0.05, top + 0.04), (c.fz + 0.03, top + 0.05), (c.fz + 0.03, top), (z, top)],
                "x", c.dx - 0.37, c.dx + 0.37, b.c["pad"])
        # The small outer gauges sit beside the opening: raised a little so the rim's sides don't cover them.
        for i, (kind, x, s, up) in enumerate((("fuel", -0.26, 0.10, 0.04), ("speedo", -0.085, 0.15, 0), ("tacho", 0.085, 0.15, 0),
                                              ("temp", 0.26, 0.10, 0.04))):
            plate(c, f"square_{kind}", c.dx + x - s / 2, c.dx + x + s / 2, y + up - s / 2, y + up + s / 2, z, b.c["panel"], depth=0.004)
            gauge(b, kind, c.dx + x, y + up, s * 0.42, zz - 0.002, ring="dark")
        lamps(b, {"handbrake": c.dx - 0.336, "headlights": c.dx + 0.336}, y + 0.02, zz, r=0.01)
        lamps(b, {"engine": c.dx - 0.336, "lowrange": c.dx + 0.336}, y - 0.015, zz, r=0.01)
        gear_display(b, c.dx + 0.336, y + 0.065, zz, size=0.03)
    plate(c, "hvac_panel", c.p(0.02), c.p(0.12), c.cy - 0.10, c.cy + 0.06, c.fz, b.c["panel"])
    for i in range(3):
        P.box(f"hvac_lever{i}", (c.p(0.04) - 0.012, c.cy + 0.03 - i * 0.05, c.fz - 0.04), (c.p(0.10) + 0.012, c.cy + 0.045 - i * 0.05,
              c.fz - 0.012), b.c["metal"])
    slots(c, "vent", c.p(0.40) - 0.08, c.p(0.40) + 0.08, c.cy + 0.02, c.cy + 0.10, c.fz, 5, b.c["dark"], vertical=False)
    cx = c.p(0.0)
    P.box("cb_bracket", (cx - 0.12, c.fb - 0.03, c.fz - 0.01), (cx + 0.12, c.fb - 0.0215, c.fz + 0.16), b.c["metal"])
    P.box("cb_radio", (cx - 0.11, c.fb - 0.09, c.fz - 0.02), (cx + 0.11, c.fb - 0.03, c.fz + 0.14), b.c["dark"])
    P.box("cb_dial", (cx - 0.07, c.fb - 0.075, c.fz - 0.024), (cx + 0.0, c.fb - 0.055, c.fz - 0.02), b.c["accent"])
    P.cbox("cb_mic", (0.05, 0.075, 0.03), b.c["dark"], centre=(cx + 0.15, c.fb - 0.02, c.fz - 0.03))


def cumbre(b):
    """80s pickup: a sloping 'waterfall' tan dash, two big rectangular dials with a strip of small ones
    under them, a cassette deck, a cup holder with a coffee thermos on the bench and the CB on the hump."""
    c = C(b)
    d = b.c["dash"]
    body(c, "dash_body", [(c.fz + 0.10, c.fb - 0.05), (c.fz - 0.03, c.fb + 0.05), (c.fz, c.ft - 0.03), (c.fz + 0.04, c.ft + 0.02),
                          (c.front, c.top), (c.front + 0.03, c.fb - 0.05)], d)
    z = c.fz - 0.04
    zz = z - 0.002
    y = c.thru(zz, (c.dx - 0.095, 0.055), (c.dx + 0.095, 0.055))
    with cluster(b):
        plate(c, "cluster_face", c.dx - 0.30, c.dx + 0.30, y - 0.14, y + 0.08, c.fz - 0.005, b.c["panel"], depth=0.035)
        P.prism("cluster_hood", [(z - 0.05, y + 0.08), (z - 0.04, y + 0.10), (c.fz + 0.03, y + 0.11), (c.fz + 0.03, y + 0.08)], "x",
                c.dx - 0.31, c.dx + 0.31, b.c["pad"])
        for kind, x in (("speedo", -0.095), ("tacho", 0.095)):
            plate(c, f"rect_{kind}", c.dx + x - 0.085, c.dx + x + 0.085, y - 0.06, y + 0.06, z, M("rect_bezel", (0.10, 0.10, 0.11)), depth=0.003)
            gauge(b, kind, c.dx + x, y, 0.055, zz - 0.002, ring="dark")
        # The strip of small ones under the big dials.
        gauge(b, "fuel", c.dx - 0.08, y - 0.105, 0.025, zz, ring="dark")
        gauge(b, "temp", c.dx + 0.08, y - 0.105, 0.025, zz, ring="dark")
        lamp_col(c, c.dx + 0.26, y + 0.045, zz, step=0.03, r=0.009)
        gear_display(b, c.dx - 0.20, y - 0.105, zz, size=0.028)
    cassette_deck(c, "deck", c.p(0.06), c.cy - 0.02, c.fz - 0.02, w=0.19)
    cushion, back_z = seat_dims(c)
    P.place(P.cylinder("cup_holder", 0.05, 0.03, b.c["dark"], n=12), (c.p(0.10), cushion + 0.02, c.L.eye[2] - 0.05), Rx(-90))
    thermos(c, c.p(0.10), cushion + 0.05, c.L.eye[2] - 0.05)
    cx = c.p(-0.02)
    P.box("cb_radio", (cx - 0.11, c.L.floor + 0.21, c.fz + 0.05), (cx + 0.11, c.L.floor + 0.28, c.fz + 0.22), b.c["dark"])
    P.box("cb_dial", (cx - 0.07, c.L.floor + 0.235, c.fz + 0.045), (cx + 0.0, c.L.floor + 0.255, c.fz + 0.05), b.c["accent"])


def woodman(b):
    """60s Wagoneer: a long horizontal painted dash with a woodgrain band, three separate round dial cans
    in a row on a bright strip, an 8-track player hung under the dash with a cartridge in it."""
    c = C(b)
    pm, uv = c.paint()
    body(c, "dash_body", [(c.fz, c.fb - 0.02), (c.fz, c.ft), (c.fz + 0.04, c.ft + 0.02), (c.front, c.top), (c.front, c.fb - 0.02)], pm, uv)
    body(c, "crash_pad", [(c.fz + 0.01, c.ft - 0.02), (c.fz - 0.025, c.ft), (c.fz - 0.015, c.ft + 0.03), (c.fz + 0.06, min(c.ft + 0.04, c.top)),
                          (c.front, c.top - 0.002), (c.front, c.ft - 0.02)], b.c["pad"])
    P.box("wood_band", (-c.w + 0.02, c.fb + 0.04, c.fz - 0.008), (c.w - 0.02, c.fb + 0.11, c.fz + 0.001), b.c["wood"])
    y = c.thru(c.fz - 0.04, (c.dx, 0.07))
    with cluster(b, hi=c.ft - 0.03):   # under the crash pad
        ys = min(y - 0.03, c.open_y(c.dx - 0.20, 0.059, c.fz - 0.035), c.open_y(c.dx + 0.20, 0.059, c.fz - 0.035))
        P.box("chrome_strip", (c.dx - 0.30, min(y - 0.145, ys - 0.07), c.fz - 0.004), (c.dx + 0.30, y + 0.085, c.fz + 0.001),
              b.c["metal"])
        dial(c, "fuel", c.dx - 0.20, ys, c.fz - 0.004, 0.045, housing="panel", depth=0.03)
        dial(c, "speedo", c.dx, y, c.fz - 0.004, 0.07, housing="panel", depth=0.035)
        dial(c, "temp", c.dx + 0.20, ys, c.fz - 0.004, 0.045, housing="panel", depth=0.03)
        lamp_row(c, c.dx, y - 0.125, c.fz - 0.006, step=0.03, r=0.01)
    # The tacho and gear display sit beside the wheel, towards the passenger.
    gauge(b, "tacho", c.dx + c.p(0.40), y + 0.01, 0.045, c.fz - 0.006)
    gear_display(b, c.dx + c.p(0.40), y - 0.075, c.fz - 0.002, size=0.03)
    tx = c.p(0.0)
    P.box("eight_track", (tx - 0.12, c.fb - 0.10, c.fz - 0.03), (tx + 0.12, c.fb - 0.03, c.fz + 0.16), b.c["wood"])
    P.box("eight_track_face", (tx - 0.11, c.fb - 0.095, c.fz - 0.034), (tx + 0.11, c.fb - 0.035, c.fz - 0.03), b.c["dark"])
    P.box("cartridge", (tx - 0.05, c.fb - 0.08, c.fz - 0.10), (tx + 0.05, c.fb - 0.05, c.fz - 0.03), M("cartridge", (0.90, 0.44, 0.20)))
    P.box("cartridge_label", (tx - 0.04, c.fb - 0.0495, c.fz - 0.09), (tx + 0.04, c.fb - 0.0490, c.fz - 0.05), M("label", (0.95, 0.88, 0.40)))


def grandwoodman(b):
    """Grand Wagoneer: the whole fascia in wood, two rectangular dial pods, an analog clock on the passenger
    side, plush pillow seats and an overhead console with a compass."""
    c = C(b)
    d, wood = b.c["dash"], b.c["wood"]
    body(c, "dash_body", [(c.fz, c.fb - 0.02), (c.fz, c.ft), (c.fz + 0.03, c.ft + 0.02), (c.front, c.top), (c.front, c.fb - 0.02)], d)
    body(c, "crash_pad", [(c.fz + 0.01, c.ft - 0.03), (c.fz - 0.03, c.ft - 0.01), (c.fz - 0.02, c.ft + 0.03), (c.fz + 0.06, min(c.ft + 0.04, c.top)),
                          (c.front, c.top - 0.002), (c.front, c.ft - 0.03)], b.c["pad"])
    P.box("wood_fascia", (-c.w + 0.02, c.fb + 0.02, c.fz - 0.010), (c.w - 0.02, c.ft - 0.035, c.fz + 0.001), wood)
    zf = c.fz - 0.010
    y = c.thru(zf - 0.031, (c.dx - 0.10, 0.06), (c.dx + 0.10, 0.06))
    with cluster(b, hi=c.ft - 0.04):   # on the wood, under the crash pad
        for kind, x in (("speedo", -0.10), ("tacho", 0.10)):
            P.box(f"pod_{kind}", (c.dx + x - 0.09, y - 0.08, zf - 0.03), (c.dx + x + 0.09, y + 0.08, zf), d)
            gauge(b, kind, c.dx + x, y, 0.06, zf - 0.031)
        zs = zf - 0.003   # just in front of the wood (flush would flicker)
        gauge(b, "fuel", c.dx - 0.25, y + 0.03, 0.03, zs)
        gauge(b, "temp", c.dx + 0.25, y + 0.03, 0.03, zs)
        lamp_row(c, c.dx, y - 0.112, zs, step=0.03, r=0.009)
        gear_display(b, c.dx + 0.25, y - 0.045, zs, size=0.028)
    clock(c, "clock", c.p(0.40), c.cy + 0.02, zf - 0.002, r=0.04)
    cassette_deck(c, "deck", c.p(0.05), c.cy - 0.05, zf, w=0.18)
    L, m = c.L, b.m
    ws = L.ws
    P.box("overhead", (-0.14, m["roof"] - 0.07, ws["top_z"] - 0.40), (0.14, m["roof"] - 0.01, ws["top_z"] - 0.12), d)
    P.box("overhead_window", (-0.05, m["roof"] - 0.075, ws["top_z"] - 0.30), (0.05, m["roof"] - 0.07, ws["top_z"] - 0.22), b.c["accent"])
    cushion, back_z = seat_dims(c)
    for sx in (L.dx, -L.dx):
        bk = P.empty(f"pillow_frame{sx:.2f}", (sx, cushion, back_z + 0.02), Rx(-7))
        for j in range(4):
            P.box(f"pillow{sx:.2f}_{j}", (-0.20, 0.08 + j * 0.13, 0.0), (0.20, 0.19 + j * 0.13, 0.05), b.c["seat2"], parent=bk)


def timberbox(b):
    """50s woodie: a painted steel dash with a bright horizontal strip, one huge speedo in a hooded can,
    a big speaker grille in the middle with the push-button radio under it, and a picnic basket."""
    c = C(b)
    pm, uv = c.paint()
    body(c, "dash_body", [(c.fz + 0.03, c.fb - 0.03), (c.fz, c.fb), (c.fz - 0.01, c.ft - 0.03), (c.fz + 0.03, c.ft + 0.02),
                          (c.front, c.top), (c.front + 0.02, c.fb - 0.03)], pm, uv)
    P.box("bright_strip", (-c.w + 0.02, c.fb + 0.035, c.fz - 0.006), (c.w - 0.02, c.fb + 0.05, c.fz + 0.001), b.c["metal"])
    # The huge speedo in its hooded can, read through the top of the banjo wheel (no room over the rim
    # under this windscreen). The dash face leans towards the driver near the top: the small dials stand
    # 1.2 cm proud so they aren't buried in it.
    zc = c.fz - 0.05
    y = min(c.ft - 0.14, c.thru(zc, (c.dx, 0.106)))
    zf = c.fz - 0.012
    with cluster(b, hi=c.ft - 0.02):
        zc = can(c, "speedo_can", c.dx, y, c.fz, 0.118, 0.05, b.c["panel"], n=32)
        P.box("speedo_hood", (c.dx - 0.12, y + 0.10, zc - 0.04), (c.dx + 0.12, y + 0.125, c.fz), pm, uv=uv)
        gauge(b, "speedo", c.dx, y, 0.10, zc - 0.001)
    ys = min(c.ft - 0.07, c.open_y(c.dx + c.p(0.20), 0.046, zf), c.open_y(c.dx - c.p(0.20), 0.054, zf))
    with cluster(b, hi=c.ft - 0.02):
        gauge(b, "fuel", c.dx + c.p(0.20), ys, 0.034, zf)
        gauge(b, "temp", c.dx + c.p(0.20), ys - 0.095, 0.034, zf)
        gauge(b, "tacho", c.dx - c.p(0.20), ys, 0.042, zf)
        gear_display(b, c.dx - c.p(0.20), ys - 0.09, zf, size=0.03)
    lamp_row(c, c.dx + c.p(0.36), c.ft - 0.06, zf, step=0.028, r=0.009)
    slots(c, "speaker", -0.11, 0.11, c.cy - 0.02, c.cy + 0.11, c.fz, 11, b.c["metal"])
    P.box("radio", (-0.11, c.cy - 0.09, c.fz - 0.02), (0.11, c.cy - 0.03, c.fz + 0.002), b.c["panel"])
    for i in range(5):
        P.box(f"radio_btn{i}", (-0.085 + i * 0.036, c.cy - 0.082, c.fz - 0.04), (-0.06 + i * 0.036, c.cy - 0.058, c.fz - 0.02),
              M("radio_btn", (0.94, 0.90, 0.80)))
    cushion, back_z = seat_dims(c)
    picnic_basket(c, c.p(0.42), cushion + 0.02, c.L.eye[2] - 0.12)


def blastwagon(b):
    """Power Wagon: a flat steel dash with a cluster of five small cream dials in front of the driver, a
    long throttle and choke pull, and the floor full of levers (gear, transfer, winch)."""
    c = C(b)
    pm, uv = c.paint()
    P.box("dash_face", (-c.w, c.fb, c.fz), (c.w, c.ft, c.fz + 0.03), pm, uv=uv)
    body(c, "dash_top", [(c.fz - 0.03, c.ft), (c.fz - 0.03, c.ft + 0.02), (c.front, c.top), (c.front, c.ft)], pm, uv)
    z = c.fz - 0.013
    y = c.thru(z, (c.dx, 0.065))
    yf = min(y + 0.045, c.open_y(c.dx - 0.16, 0.048, z), c.open_y(c.dx + 0.16, 0.048, z))
    with cluster(b, hi=c.ft - 0.01):   # under the dash-top lip
        plate(c, "cluster_plate", c.dx - 0.24, c.dx + 0.24, min(y - 0.11, yf - 0.16), max(y + 0.10, yf + 0.06), c.fz, b.c["panel"])
        gauge(b, "speedo", c.dx, y, 0.065, z)
        gauge(b, "fuel", c.dx - 0.16, yf, 0.036, z)
        gauge(b, "temp", c.dx + 0.16, yf, 0.036, z)
        gauge(b, "tacho", c.dx - 0.16, yf - 0.10, 0.036, z)
        gear_display(b, c.dx + 0.16, yf - 0.10, z, size=0.032)
        lamp_row(c, c.dx, y - 0.09, z, step=0.028, r=0.009)
    knob_row(c, "pull_throttle", (c.dx + c.p(0.30), c.dx + c.p(0.36)), c.fb + 0.05, c.fz, b.c["knob"], r=0.013, length=0.06)
    knob_row(c, "dash_bolt", [(-c.w + 0.06) + i * (2 * c.w - 0.12) / 11 for i in range(12)], c.ft - 0.02, c.fz, b.c["dark"],
             r=0.006, length=0.005)
    gloves(c, c.p(0.40), c.ft + 0.025, c.fz - 0.02)


def boar(b):
    """Volvo TP21 'Sugga' radio car: a 50s Volvo dash with one big dial and two small ones, and the army
    radio stack filling the passenger side, handset hanging off it, a map board clipped to the dash."""
    c = C(b)
    pm, uv = c.paint()
    body(c, "dash_body", [(c.fz + 0.03, c.fb - 0.03), (c.fz, c.fb), (c.fz - 0.01, c.ft - 0.02), (c.fz + 0.03, c.ft + 0.02),
                          (c.front, c.top), (c.front + 0.02, c.fb - 0.03)], pm, uv)
    # The dash face leans towards the driver near the top: everything on it stands 1.2 cm proud.
    zf = c.fz - 0.012
    y = min(c.ft - 0.13, c.thru(c.fz - 0.031, (c.dx, 0.093)))
    with cluster(b, hi=c.ft - 0.02):
        zc = can(c, "speedo_can", c.dx, y, c.fz, 0.105, 0.03, b.c["panel"], n=32)
        gauge(b, "speedo", c.dx, y, 0.09, zc - 0.001)
        gear_display(b, c.dx, y - 0.13, zf, size=0.03)
    ys = min(y, c.open_y(c.dx - 0.17, 0.047, zf), c.open_y(c.dx + 0.17, 0.047, zf))
    with cluster(b, hi=c.ft - 0.02):
        gauge(b, "fuel", c.dx - 0.17, ys, 0.035, zf)
        gauge(b, "temp", c.dx + 0.17, ys, 0.035, zf)
    # The tacho and the lamps beside the wheel, towards the passenger.
    gauge(b, "tacho", c.dx + c.p(0.32), y - 0.01, 0.04, zf)
    lamp_row(c, c.dx + c.p(0.32), y + 0.075, zf, step=0.028, r=0.009)
    olive, dark = M("olive", (0.36, 0.40, 0.26)), b.c["dark"]
    rx = c.p(0.42)
    L = c.L
    P.box("radio_rack", (rx - 0.20, L.floor + 0.02, c.fz - 0.30), (rx + 0.20, c.fb + 0.06, c.fz - 0.02), M("rack", (0.30, 0.32, 0.22)))
    for i, (y0, y1) in enumerate(((L.floor + 0.05, L.floor + 0.30), (L.floor + 0.32, c.fb + 0.04))):
        P.box(f"radio_unit{i}", (rx - 0.18, y0, c.fz - 0.31), (rx + 0.18, y1, c.fz - 0.29), olive)
        knob_row(c, f"radio_knob{i}_", (rx - 0.12, rx - 0.04, rx + 0.04, rx + 0.12), (y0 + y1) / 2, c.fz - 0.31, b.c["metal"], r=0.016)
        P.box(f"radio_dial{i}", (rx - 0.14, y1 - 0.06, c.fz - 0.313), (rx + 0.0, y1 - 0.03, c.fz - 0.31), b.c["accent"])
    handset(c, rx + 0.24 * -c.side, c.fb - 0.08, c.fz - 0.20)
    P.place(P.cylinder("antenna_base", 0.02, 0.10, dark, n=8), (rx, c.fb + 0.06, c.fz - 0.15), Rx(-90))
    bx = c.p(0.17)
    P.box("map_board", (bx - 0.10, c.ft - 0.27, c.fz - 0.012), (bx + 0.10, c.ft - 0.05, c.fz), M("board", (0.66, 0.48, 0.30)))
    P.box("map_board_paper", (bx - 0.085, c.ft - 0.25, c.fz - 0.016), (bx + 0.085, c.ft - 0.07, c.fz - 0.012), M("map", (0.92, 0.86, 0.66)))


def lynx(b):
    """VW Iltis: a bare black steel dash with a grab bar across it, the instrument box on top, a military
    switch panel with guarded toggles and a big rotary light switch, a map case for the passenger."""
    c = C(b)
    d = b.c["dash"]
    body(c, "dash_body", [(c.fz, c.fb), (c.fz, c.ft), (c.fz + 0.02, c.ft + 0.01), (c.front, c.top), (c.front, c.fb)], d)
    z = c.fz - 0.05
    y0 = max(c.L.sight_y(z) + 0.015, c.ft - 0.06)
    pod = P.empty("instrument_box", (c.dx, y0 + 0.07, z), Rx(12))
    P.box("box_housing", (-0.18, -0.095, 0.0), (0.18, 0.085, 0.09), b.c["panel"], parent=pod)
    P.box("box_visor", (-0.19, 0.085, -0.05), (0.19, 0.10, 0.09), d, parent=pod)
    gauge(b, "speedo", -0.075, 0.0, 0.056, -0.002, pod)
    gauge(b, "tacho", 0.065, 0.025, 0.04, -0.002, pod)
    gauge(b, "fuel", 0.03, -0.06, 0.018, -0.002, pod)
    gauge(b, "temp", 0.10, -0.06, 0.018, -0.002, pod)
    lamps(b, {"handbrake": -0.155, "headlights": 0.15}, 0.06, -0.002, pod, r=0.009)
    lamps(b, {"engine": -0.155, "lowrange": 0.15}, 0.03, -0.002, pod, r=0.009)
    gear_display(b, -0.155, -0.06, -0.002, pod, size=0.026)
    gx0, gx1 = -c.w + 0.12, c.w - 0.12
    c.k.beam("dash_grab_bar", (gx0, c.ft - 0.03, c.fz - 0.06), (gx1, c.ft - 0.03, c.fz - 0.06), 0.025, 0.025, b.c["metal"])
    sx = c.p(0.0)
    plate(c, "switch_panel", sx - 0.14, sx + 0.14, c.cy - 0.10, c.cy + 0.02, c.fz, M("olive_plate", (0.34, 0.37, 0.25)))
    for i, x in enumerate((sx - 0.09, sx - 0.03, sx + 0.03)):
        P.box(f"toggle_guard{i}", (x - 0.022, c.cy - 0.06, c.fz - 0.03), (x + 0.022, c.cy - 0.055, c.fz - 0.012), b.c["dark"])
        P.cbox(f"toggle{i}", (0.01, 0.01, 0.03), b.c["metal"], centre=(x, c.cy - 0.04, c.fz - 0.027))
    P.place(P.cylinder("light_switch", 0.03, 0.03, b.c["dark"], n=12, z0=-0.03), (sx + 0.09, c.cy - 0.04, c.fz - 0.012))
    P.place(P.cbox("light_switch_bar", (0.05, 0.012, 0.012), b.c["knob3"]), (sx + 0.09, c.cy - 0.04, c.fz - 0.046))
    mx0, mx1 = c.px(0.30, 0.62)
    P.box("map_case", (mx0, c.cy - 0.12, c.fz - 0.03), (mx1, c.cy + 0.06, c.fz + 0.002), M("map_case", (0.40, 0.42, 0.28)))
    P.box("map_window", (mx0 + 0.03, c.cy - 0.09, c.fz - 0.033), (mx1 - 0.03, c.cy + 0.03, c.fz - 0.03), M("map", (0.92, 0.86, 0.66)))


def wombat(b):
    """Early G-Class: a flat upright dash, three round dials in a row under a straight hood, the chunky
    passenger grab handle, the yellow diff-lock buttons and a first-aid kit by the passenger's knees."""
    c = C(b)
    d = b.c["dash"]
    body(c, "dash_body", [(c.fz, c.fb), (c.fz, c.ft), (c.fz + 0.01, c.ft + 0.02), (c.front, c.top), (c.front, c.fb)], d)
    z = c.fz - 0.04
    zz = z - 0.004
    # Speedo in the wheel's opening, the tacho and the fuel/temp pair a little lower where the rim curves
    # down; the gear display at the outer end, the lamps in a square at the passenger end.
    y = c.thru(zz, (c.dx, 0.064))
    yt = min(y, c.open_y(c.dx - 0.165, 0.067, zz))
    yf = min(y + 0.038, c.open_y(c.dx + 0.155, 0.036, zz))
    lo = min(y - 0.08, yt - 0.08, yf - 0.115)
    with cluster(b):
        P.box("hood_box", (c.dx - 0.30, lo, z), (c.dx + 0.30, y + 0.08, c.fz), d)
        P.box("hood_brow", (c.dx - 0.31, y + 0.08, z - 0.05), (c.dx + 0.31, y + 0.10, c.fz), b.c["pad"])
        plate(c, "dial_face", c.dx - 0.29, c.dx + 0.29, lo + 0.005, y + 0.075, z, b.c["panel"], depth=0.003)
        gauge(b, "tacho", c.dx - 0.165, yt, 0.055, zz)
        gauge(b, "speedo", c.dx, y, 0.064, zz)
        gauge(b, "fuel", c.dx + 0.155, yf, 0.024, zz)
        gauge(b, "temp", c.dx + 0.155, yf - 0.076, 0.024, zz)
        lamps(b, {"handbrake": c.dx + 0.245, "engine": c.dx + 0.275}, yf + 0.01, zz, r=0.009)
        lamps(b, {"headlights": c.dx + 0.245, "lowrange": c.dx + 0.275}, yf - 0.02, zz, r=0.009)
        gear_display(b, c.dx - 0.26, yt + 0.035, zz, size=0.024)
    gx0, gx1 = c.px(0.20, 0.55)
    c.k.beam("grab_handle", (gx0, c.cy + 0.05, c.fz - 0.09), (gx1, c.cy + 0.05, c.fz - 0.09), 0.04, 0.04, b.c["dark"])
    for i, gx in enumerate((gx0 + 0.02, gx1 - 0.02)):
        P.box(f"grab_post{i}", (gx - 0.02, c.cy + 0.035, c.fz - 0.09), (gx + 0.02, c.cy + 0.065, c.fz), b.c["dark"])
    for i in range(3):
        x = -0.05 + i * 0.05
        P.box(f"diff_btn{i}", (x - 0.018, c.fb + 0.03, c.fz - 0.03), (x + 0.018, c.fb + 0.066, c.fz), M("diffbtn", (0.95, 0.78, 0.25)))
    P.box("first_aid", (c.p(0.30) - 0.12, c.fb - 0.10, c.fz - 0.02), (c.p(0.30) + 0.12, c.fb - 0.0215, c.fz + 0.06), M("kit", (0.92, 0.92, 0.90)))
    P.box("first_aid_band", (c.p(0.30) - 0.12, c.fb - 0.07, c.fz - 0.022), (c.p(0.30) + 0.12, c.fb - 0.05, c.fz - 0.02), M("kit_band", (0.20, 0.55, 0.36)))


def brick(b):
    """80s Land Cruiser: chunky grey plastic with a carpet mat on the dash top, a rectangular cluster with
    square-shouldered dials, a Japanese cassette radio, heater sliders, sheepskin seat covers."""
    c = C(b)
    d = b.c["dash"]
    body(c, "dash_body", [(c.fz + 0.02, c.fb - 0.03), (c.fz, c.fb), (c.fz - 0.02, c.ft - 0.03), (c.fz + 0.02, c.ft + 0.02),
                          (c.front, c.top), (c.front + 0.02, c.fb - 0.03)], d)
    body(c, "dash_mat", [(c.fz + 0.03, c.ft + 0.022), (c.fz + 0.03, c.ft + 0.03), (c.front - 0.02, c.top + 0.006), (c.front - 0.02, c.top - 0.002)],
         M("dash_mat", (0.22, 0.20, 0.18)), x0=-c.w + 0.05, x1=c.w - 0.05)
    z = c.fz - 0.06
    top = min(c.ft + 0.01, c.top - 0.03)
    zz = z - 0.004
    y = min(top - 0.10, c.thru(zz, (c.dx - 0.085, 0.07), (c.dx + 0.085, 0.07)))
    with cluster(b, hi=top + 0.045):
        bot = min(top - 0.21, y - 0.135)
        P.box("cluster_box", (c.dx - 0.30, bot, z), (c.dx + 0.30, top, c.fz), d)
        P.prism("cluster_hood", [(z - 0.06, top + 0.01), (z - 0.05, top + 0.035), (c.fz + 0.03, top + 0.045), (c.fz + 0.03, top), (z, top)],
                "x", c.dx - 0.31, c.dx + 0.31, b.c["pad"])
        plate(c, "cluster_face", c.dx - 0.28, c.dx + 0.28, bot + 0.01, top - 0.01, z, b.c["panel"], depth=0.003)
        gauge(b, "speedo", c.dx - 0.085, y, 0.07, zz)
        gauge(b, "tacho", c.dx + 0.085, y, 0.07, zz)
        ys = min(y + 0.03, c.open_y(c.dx - 0.225, 0.042, zz), c.open_y(c.dx + 0.225, 0.042, zz))
        gauge(b, "fuel", c.dx - 0.225, ys, 0.03, zz)
        gauge(b, "temp", c.dx + 0.225, ys, 0.03, zz)
        # Lamps in pairs at the ends (outside the rim), the gear display in the notch over the big dials.
        lamps(b, {"handbrake": c.dx - 0.282, "headlights": c.dx + 0.282}, y + 0.045, zz, r=0.009)
        lamps(b, {"engine": c.dx - 0.282, "lowrange": c.dx + 0.282}, y + 0.015, zz, r=0.009)
        gear_display(b, c.dx, y + 0.075, zz, size=0.028)
    cassette_deck(c, "deck", c.p(0.05), c.cy, c.fz, w=0.18)
    for i in range(3):
        x = c.p(0.05) - 0.06 + i * 0.06
        P.box(f"slider{i}", (x - 0.012, c.cy - 0.10, c.fz - 0.03), (x + 0.012, c.cy - 0.075, c.fz - 0.005), b.c["metal"])
    cushion, back_z = seat_dims(c)
    for sx in (c.L.dx, -c.L.dx):
        sheepskin(c, sx, cushion, back_z)


def roamer(b):
    """90s 4Runner: a curved dark dash with a deep cowl over a tach-first cluster, the dash-top tilt and
    compass meter, a double-height cassette radio with a green clock, sunglasses on the dash."""
    c = C(b)
    d = b.c["dash"]
    body(c, "dash_body", [(c.fz + 0.05, c.fb - 0.04), (c.fz - 0.01, c.fb + 0.02), (c.fz - 0.02, c.ft - 0.04), (c.fz + 0.01, c.ft + 0.015),
                          (c.fz + 0.08, c.ft + 0.03), (c.front, c.top), (c.front + 0.03, c.fb - 0.04)], d)
    z = c.fz - 0.06
    top = min(c.ft + 0.015, c.top - 0.03)
    zz = z - 0.003
    y = min(top - 0.11, c.thru(zz, (c.dx - 0.06, 0.08), (c.dx + 0.12, 0.06)))
    with cluster(b, hi=top + 0.06):
        P.prism("cowl", [(z - 0.07, top + 0.005), (z - 0.06, top + 0.035), (z - 0.02, top + 0.055), (c.fz + 0.05, top + 0.06),
                         (c.fz + 0.05, top), (z, top)], "x", c.dx - 0.33, c.dx + 0.33, b.c["pad"])
        P.box("cluster_well", (c.dx - 0.32, min(top - 0.22, y - 0.14), z), (c.dx + 0.32, top, c.fz), b.c["panel"])
        gauge(b, "tacho", c.dx - 0.06, y, 0.08, zz)
        gauge(b, "speedo", c.dx + 0.12, y - 0.01, 0.06, zz)
        ys = min(y + 0.04, c.open_y(c.dx - 0.235, 0.042, zz))
        gauge(b, "fuel", c.dx - 0.235, ys, 0.03, zz)
        gauge(b, "temp", c.dx - 0.235, ys - 0.09, 0.03, zz)
        # The gear display and the lamps (in a square) at the outer end, clear of the rim.
        gear_display(b, c.dx + 0.29, y + 0.07, zz, size=0.03)
        lamps(b, {"handbrake": c.dx + 0.275, "engine": c.dx + 0.305}, y + 0.025, zz, r=0.009)
        lamps(b, {"headlights": c.dx + 0.275, "lowrange": c.dx + 0.305}, y - 0.005, zz, r=0.009)
    pod = P.empty("incl_pod", (0.0, c.ft + 0.075, c.fz + 0.06), Ry(12 * c.side) @ Rx(15))
    P.box("incl_housing", (-0.10, -0.045, 0.0), (0.10, 0.045, 0.07), d, parent=pod)
    P.box("incl_visor", (-0.105, 0.045, -0.035), (0.105, 0.058, 0.07), b.c["pad"], parent=pod)
    for i, x in enumerate((-0.048, 0.048)):
        P.place(P.disc(f"incl_face{i}", 0.036, P.material("glow:incl", image="v2_incl.png", rough=0.9), n=28, parent=pod), (x, 0.0, -0.002))
    cassette_deck(c, "deck", c.p(0.04), c.cy + 0.03, c.fz - 0.01, w=0.18)
    cassette_deck(c, "deck2", c.p(0.04), c.cy - 0.04, c.fz - 0.01, w=0.18)
    P.box("clock_display", (c.p(0.04) - 0.04, c.cy + 0.075, c.fz - 0.012), (c.p(0.04) + 0.04, c.cy + 0.095, c.fz - 0.01),
          M("green_lcd", (0.40, 0.85, 0.50)))
    sx = c.p(0.42)
    sg = M("shades", (0.10, 0.10, 0.12))
    for i in (-1, 1):
        P.place(P.cbox(f"shade_lens{i}", (0.05, 0.006, 0.035), sg), (sx + i * 0.03, c.ft + 0.04, c.fz + 0.06), Ry(20))


def polyana(b):
    """Lada Niva: a black dash whose cluster has three deep tubes, a tall centre stack to the floor with
    three small gauges, a Soviet radio and the choke knob, and two transfer levers (range, diff lock)."""
    c = C(b)
    d = b.c["dash"]
    body(c, "dash_body", [(c.fz, c.fb), (c.fz, c.ft), (c.fz + 0.03, c.ft + 0.02), (c.front, c.top), (c.front, c.fb)], d)
    z = c.fz - 0.04
    zt = z - 0.051
    y = c.thru(zt, (c.dx, 0.068))
    yt = min(y - 0.035, c.open_y(c.dx - 0.17, 0.072, zt), c.open_y(c.dx + 0.17, 0.062, zt))
    with cluster(b):
        P.box("cluster_box", (c.dx - 0.30, min(y, yt) - 0.10, z), (c.dx + 0.30, y + 0.10, c.fz), d)
        P.box("cluster_brow", (c.dx - 0.31, y + 0.10, z - 0.05), (c.dx + 0.31, y + 0.115, c.fz), b.c["pad"])
        for i, (kind, x, r) in enumerate((("tacho", -0.17, 0.06), ("speedo", 0.0, 0.068), ("fuel", 0.17, 0.05))):
            ty = y if kind == "speedo" else yt
            zc = can(c, f"{kind}_tube", c.dx + x, ty, z, r + 0.012, 0.05, M("tube", (0.08, 0.08, 0.09)), n=20)
            gauge(b, kind, c.dx + x, ty, r, zc - 0.001)
        # Lamps in pairs above the side tubes (the tubes stand 5 cm out and hide what's right under them).
        lamps(b, {"handbrake": c.dx - 0.215, "engine": c.dx - 0.18, "headlights": c.dx + 0.18, "lowrange": c.dx + 0.215},
              yt + 0.087, z - 0.002, r=0.009)
    L = c.L
    P.prism("centre_stack", [(-0.11, L.floor + 0.22), (-0.11, c.fb + 0.10), (0.11, c.fb + 0.10), (0.11, L.floor + 0.22)], "z",
            c.fz - 0.12, c.fz + 0.06, d)
    zs = c.fz - 0.122
    gauge(b, "temp", -0.06, c.fb + 0.04, 0.03, zs)
    clock(c, "clock", 0.0, c.fb + 0.04, zs, r=0.03)
    P.place(P.disc("volt_face", 0.03, M("volt", (0.18, 0.18, 0.20)), n=20), (0.06, c.fb + 0.04, zs))
    gear_display(b, 0.0, c.fb - 0.03, zs, size=0.03)
    P.box("soviet_radio", (-0.10, c.fb - 0.14, zs - 0.012), (0.10, c.fb - 0.07, zs + 0.002), M("radio_silver", (0.66, 0.66, 0.64)))
    knob_row(c, "radio_knob", (-0.075, 0.075), c.fb - 0.105, zs - 0.012, b.c["dark"], r=0.014)
    knob_row(c, "choke", (c.dx + c.p(0.32),), c.fb + 0.04, c.fz, b.c["knob"], r=0.012, length=0.05)


def grizzly(b):
    """Fiat Panda: no dash, a full-width fabric hammock shelf with life in it (map, sunglasses, a cassette),
    a tiny instrument box, one round vent in the middle."""
    c = C(b)
    d = b.c["dash"]
    body(c, "dash_top", [(c.fz + 0.06, c.ft - 0.02), (c.fz + 0.04, c.ft + 0.02), (c.front, c.top), (c.front, c.ft - 0.02)], d)
    body(c, "shelf_tray", [(c.fz - 0.10, c.fb + 0.02), (c.fz - 0.10, c.fb + 0.06), (c.fz - 0.08, c.fb + 0.06), (c.fz - 0.06, c.fb + 0.03),
                           (c.fz + 0.10, c.fb + 0.03), (c.fz + 0.10, c.fb + 0.02)], b.c["seat2"], x0=-c.w + 0.02, x1=c.w - 0.02)
    P.box("shelf_rail", (-c.w + 0.02, c.fb + 0.055, c.fz - 0.115), (c.w - 0.02, c.fb + 0.075, c.fz - 0.095), d)
    P.box("shelf_back", (-c.w, c.fb - 0.02, c.fz + 0.10), (c.w, c.ft - 0.02, c.fz + 0.13), d)
    z = c.fz + 0.0
    y0 = max(c.L.sight_y(z) + 0.015, c.ft - 0.05)
    pod = P.empty("instrument_box", (c.dx, y0 + 0.08, z), Rx(10))
    P.box("box_housing", (-0.15, -0.095, 0.0), (0.15, 0.07, 0.09), d, parent=pod)
    P.box("box_visor", (-0.16, 0.07, -0.04), (0.16, 0.085, 0.09), b.c["pad"], parent=pod)
    gauge(b, "speedo", -0.05, 0.0, 0.048, -0.002, pod)
    gauge(b, "tacho", 0.075, 0.02, 0.032, -0.002, pod)
    gauge(b, "fuel", 0.045, -0.055, 0.016, -0.002, pod)
    gauge(b, "temp", 0.11, -0.055, 0.016, -0.002, pod)
    lamp_col(c, -0.13, 0.045, -0.002, step=0.025, r=0.008, parent=pod)
    gear_display(b, -0.05, -0.078, -0.002, pod, size=0.02)
    P.place(P.cylinder("round_vent", 0.05, 0.02, b.c["dark"], n=16, z0=-0.02), (0.0, c.ft - 0.06, c.fz + 0.10))
    tray_y = c.fb + 0.035
    map_sheet(c, "shelf_map", c.p(0.40), tray_y, c.fz - 0.02, rot=10, w=0.26, d=0.12)
    sg = M("shades", (0.10, 0.10, 0.12))
    for i in (-1, 1):
        P.place(P.cbox(f"shade_lens{i}", (0.045, 0.006, 0.03), sg), (c.p(0.18) + i * 0.028, tray_y + 0.006, c.fz - 0.03), Ry(-15))
    P.place(P.cbox("cassette_case", (0.11, 0.015, 0.07), M("cassette", (0.30, 0.55, 0.80))), (c.p(-0.05), tray_y + 0.008, c.fz - 0.02), Ry(25))


def baguette(b):
    """Small French 4x4: a tan plastic dash with a rounded 'bubble' pod for the dials, a single-spoke
    wheel, orange corduroy seats, and a baguette on the passenger seat (of course)."""
    c = C(b)
    d = b.c["dash"]
    body(c, "dash_body", [(c.fz + 0.03, c.fb - 0.03), (c.fz, c.fb), (c.fz - 0.01, c.ft - 0.03), (c.fz + 0.03, c.ft + 0.02),
                          (c.front, c.top), (c.front + 0.02, c.fb - 0.03)], d)
    z = c.fz
    zz = z - 0.064
    y = c.thru(zz, (c.dx - 0.07, 0.058), (c.dx + 0.075, 0.048))
    with cluster(b):
        bubble = P.ball("bubble_pod", 0.10, b.c["pad"], rings=6, segs=14)
        P.place(bubble, (c.dx, y, z - 0.005))
        bubble.scale = (3.1, 0.55, 1.1)   # wide flat lozenge (Blender x across, y depth, z up)
        plate(c, "bubble_face", c.dx - 0.26, c.dx + 0.26, y - 0.08, y + 0.08, z - 0.058, b.c["panel"], depth=0.004)
        gauge(b, "speedo", c.dx - 0.07, y, 0.058, zz)
        gauge(b, "tacho", c.dx + 0.075, y, 0.048, zz)
        gauge(b, "fuel", c.dx - 0.222, y, 0.028, zz)
        gauge(b, "temp", c.dx + 0.222, y, 0.028, zz)
        # Two lamps over each small dial, the gear display low between the big ones.
        lamps(b, {"handbrake": c.dx - 0.24, "engine": c.dx - 0.205, "headlights": c.dx + 0.205, "lowrange": c.dx + 0.24},
              y + 0.058, zz, r=0.008)
        gear_display(b, c.dx + 0.005, y - 0.06, zz, size=0.024)
    slots(c, "vent", c.p(0.40) - 0.07, c.p(0.40) + 0.07, c.cy, c.cy + 0.06, c.fz, 6, b.c["dark"])
    cushion, back_z = seat_dims(c)
    _loaf(c, c.p(0.42), cushion + 0.03, c.L.eye[2] - 0.20, rot=35)




def mammoth(b):
    """Unimog 406: a tall flat steel dash with separate round dial cans on a bar in the middle, two air
    pressure gauges, grab handles, and a forest of colour-coded levers on the floor."""
    c = C(b)
    pm, uv = c.paint()
    P.box("dash_face", (-c.w, c.fb, c.fz), (c.w, c.ft, c.fz + 0.03), pm, uv=uv)
    body(c, "dash_top", [(c.fz - 0.06, c.ft), (c.fz - 0.06, c.ft + 0.025), (c.front, c.top), (c.front, c.ft)], b.c["pad"])
    y = c.ft - 0.12
    P.box("dial_bar", (-0.32, y - 0.105, c.fz - 0.01), (0.32, y + 0.09, c.fz + 0.001), b.c["panel"])
    for kind, x, yy, r in (("speedo", c.p(-0.10), y, 0.075), ("tacho", c.p(0.08), y, 0.075), ("fuel", c.p(0.25), y + 0.045, 0.032),
                           ("temp", c.p(0.25), y - 0.045, 0.032)):
        dial(c, kind, x, yy, c.fz - 0.01, r, housing="dark", depth=0.03)
    P.place(P.disc("air_gauge", 0.035, M("air_face", (0.92, 0.90, 0.82)), n=20), (c.dx, c.ft - 0.06, c.fz - 0.002))
    P.place(P.torus("air_gauge_ring", 0.039, 0.005, b.c["metal"], n=20, m=5), (c.dx, c.ft - 0.06, c.fz - 0.002))
    lamp_row(c, 0.0, y - 0.13, c.fz - 0.002, step=0.03, r=0.01)
    gear_display(b, c.p(-0.01), y - 0.08, c.fz - 0.012, size=0.032)   # low between the cans, on the bar
    toggles(c, "toggle", (-0.28, -0.22, 0.22, 0.28), y - 0.13, c.fz, b.c["dark"], b.c["metal"])
    L, m = c.L, b.m
    for s in (-1, 1):
        c.k.beam(f"pillar_grab{s}", (s * (L.ws["half_w"] + 0.02), L.ws["base_y"] + 0.05, L.ws["base_z"] - 0.10),
                 (s * (L.ws["half_w"] + 0.02), L.ws["base_y"] + 0.35, L.ws["base_z"] - 0.14), 0.03, 0.03, b.c["dark"])


def marshal(b):
    """Land Rover 101 Forward Control: a flat olive panel dash, dials in the middle under a little hood,
    the big engine box between the seats with a map tray and a radio set on top of it."""
    c = C(b)
    d = b.c["dash"]
    P.box("dash_face", (-c.w, c.fb, c.fz), (c.w, c.ft, c.fz + 0.03), d)
    body(c, "dash_top", [(c.fz - 0.03, c.ft), (c.fz - 0.03, c.ft + 0.02), (c.front, c.top), (c.front, c.ft)], d)
    y = c.ft - 0.11
    # In the middle of the dash, the small dials on the passenger side, away from the wheel rim.
    px0, px1 = c.px(-0.14, 0.275)
    P.box("dial_hood", (px0 - 0.01, y + 0.08, c.fz - 0.06), (px1 + 0.01, y + 0.095, c.fz), b.c["pad"])
    plate(c, "dial_panel", px0, px1, y - 0.13, y + 0.08, c.fz, b.c["panel"])
    z = c.fz - 0.013
    gauge(b, "speedo", c.p(0.085), y, 0.07, z)
    gauge(b, "tacho", c.p(-0.07), y, 0.055, z)
    gauge(b, "fuel", c.p(0.23), y + 0.03, 0.03, z)   # low enough that the hood doesn't cover it
    gauge(b, "temp", c.p(0.23), y - 0.056, 0.03, z)
    lamp_row(c, c.p(0.085), y - 0.11, z, step=0.03, r=0.009)
    gear_display(b, c.p(-0.07), y - 0.095, z, size=0.03)
    toggles(c, "toggle", (c.dx - 0.10, c.dx, c.dx + 0.10), c.fb + 0.06, c.fz, b.c["dark"], b.c["metal"])
    L = c.L
    top_y = L.floor + 0.41
    P.prism("engine_cover", [(-0.22, L.floor), (-0.20, top_y), (0.20, top_y), (0.22, L.floor)], "z", L.eye[2] - 0.25, c.fz + 0.05, d)
    P.box("map_tray", (-0.19, top_y, L.eye[2] - 0.15), (0.19, top_y + 0.03, L.eye[2] + 0.25), b.c["rubber"])
    map_sheet(c, "tray_map", 0.0, top_y + 0.035, L.eye[2] + 0.05, rot=8, w=0.28, d=0.22)
    P.box("radio_set", (-0.17, top_y, c.fz - 0.20), (0.17, top_y + 0.22, c.fz + 0.02), M("olive", (0.36, 0.40, 0.26)))
    P.box("radio_set_face", (-0.15, top_y + 0.03, c.fz - 0.205), (0.15, top_y + 0.19, c.fz - 0.20), b.c["dark"])
    knob_row(c, "set_knob", (-0.09, 0.0, 0.09), top_y + 0.10, c.fz - 0.205, b.c["metal"], r=0.016)


def rustox(b):
    """Mercedes T2 camper: a tall white van dash with the cluster in a big round-cornered hood, a parcel
    tray across the top with a mug and a map, the engine box, and a beaded seat cover for the driver."""
    c = C(b)
    d = b.c["dash"]
    body(c, "dash_body", [(c.fz, c.fb - 0.05), (c.fz, c.ft), (c.fz + 0.03, c.ft + 0.02), (c.front, c.top), (c.front, c.fb - 0.05)], d)
    z = c.fz - 0.05
    zz = z - 0.004
    y = c.thru(zz, (c.dx - 0.07, 0.07), (c.dx + 0.08, 0.05))
    with cluster(b):
        P.box("cluster_box", (c.dx - 0.26, y - 0.10, z), (c.dx + 0.26, y + 0.10, c.fz), b.c["pad"])
        plate(c, "cluster_face", c.dx - 0.24, c.dx + 0.24, y - 0.085, y + 0.085, z, b.c["panel"], depth=0.003)
        gauge(b, "speedo", c.dx - 0.07, y, 0.07, zz)
        gauge(b, "tacho", c.dx + 0.08, y + 0.01, 0.05, zz)
        gauge(b, "fuel", c.dx + 0.185, y + 0.04, 0.025, zz)
        gauge(b, "temp", c.dx + 0.185, y - 0.04, 0.025, zz)
        lamp_row(c, c.dx + 0.08, y - 0.065, zz, step=0.025, r=0.008)
        gear_display(b, c.dx - 0.20, y + 0.055, zz, size=0.026)
    body(c, "parcel_tray", [(c.fz - 0.02, c.ft + 0.02), (c.fz - 0.02, c.ft + 0.05), (c.fz + 0.02, c.ft + 0.05), (c.fz + 0.02, c.ft + 0.025),
                            (c.front - 0.05, c.ft + 0.025), (c.front - 0.05, c.ft + 0.02)], b.c["pad"], x0=c.px(0.10, 0.80)[0],
         x1=c.px(0.10, 0.80)[1])
    mug(c, "camp_mug", c.p(0.45), c.ft + 0.025, c.fz + 0.06, col=(0.92, 0.48, 0.20))
    map_sheet(c, "dash_map", c.p(0.25), c.ft + 0.03, c.fz + 0.08, rot=-10, w=0.24, d=0.16)
    cassette_deck(c, "radio", c.p(0.10), c.cy - 0.04, c.fz, w=0.18)
    cushion, back_z = seat_dims(c)
    beads(c, c.L.dx, cushion, back_z)


def _loaf(c, x, y, z, rot=30):
    bread = M("bread", (0.86, 0.62, 0.32))
    ob = P.ball("loaf", 0.05, bread, rings=5, segs=8)
    P.place(ob, (x, y + 0.04, z), Ry(rot))
    ob.scale = (7.0, 0.9, 1.0)
    for i in range(4):
        t = -0.18 + i * 0.12
        P.place(P.cbox(f"loaf_cut{i}", (0.02, 0.006, 0.05), M("bread_cut", (0.96, 0.84, 0.60))),
                (x + math.cos(math.radians(rot)) * t, y + 0.085, z - math.sin(math.radians(rot)) * t), Ry(rot + 35))



SIGS = {
    "Burro": burro, "Protector": protector, "Tinny": tinny, "TrailRat": trailrat, "BullV1": bull,
    "TrailBurner": trailburner, "Cumbre": cumbre, "Woodman": woodman, "GrandWoodman": grandwoodman,
    "Timberbox": timberbox, "BlastWagon": blastwagon, "Boar": boar, "Lynx": lynx, "Wombat": wombat,
    "Brick": brick, "Roamer": roamer, "Polyana": polyana, "Grizzly": grizzly, "Baguette": baguette,
    "Mammoth": mammoth, "Marshal": marshal, "RustOx": rustox,
}
