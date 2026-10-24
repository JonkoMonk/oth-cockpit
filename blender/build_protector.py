# Protector cockpit: a classic utility off-roader. Upright black plastic dash with an open tray on the
# passenger side, dials in a square binnacle pod on top of the dash (read over the steering wheel),
# a flat 4-spoke wheel, painted door tops and windscreen frame, cloth seats with headrests, a tall
# handbrake lever by the seat, the "alpine" skylights in the roof edge and inward-facing benches in the back.
# Run: blender -b --factory-startup -P build_protector.py -- <assets folder> <car folder>
#
# Protector cabin (game coordinates, metres; measure.py): floor 0.375, roof inside 1.96, walls lean in:
# x +-0.87 below 1.0, +-0.81 at 1.1, +-0.77 at 1.3-1.5, +-0.70 at 1.9. Windscreen glass x +-0.74 from
# y 1.32 z 0.66 to y 1.82 z 0.44; hood top 1.18. Door z -0.35..0.56, beltline 1.20, side window top 1.71,
# B pillar z -0.58..-0.34, rear side window to z -1.59, rear z -1.80. Wipers pivot at the screen base.
import math
import os
import sys

import bpy

sys.dont_write_bytecode = True   # no __pycache__ (it would hold full folder paths)
sys.path.insert(0, os.path.dirname(__file__))
import kit as K  # noqa: E402
import parts as P  # noqa: E402
from parts import Rx  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
P.ASSETS, CARS = args[0], args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)

k = K.Kit("Protector", CARS)
SIDE = 1                        # +1 right-hand drive (like the real thing), -1 left-hand drive
DX = 0.42 * SIDE                # driver's centre line


def M(x):
    """x of a part drawn for a left-hand drive car, moved to this car's driver side."""
    return -SIDE * x


def MX(a, b):
    return (min(M(a), M(b)), max(M(a), M(b)))


EYE = (DX, 1.64, -0.30)
P.empty("eye", EYE)

plastic = P.material("lit:plastic", (0.018, 0.018, 0.02), rough=0.7)
cloth = P.material("lit:cloth", (0.035, 0.036, 0.04), rough=0.95)
cloth_light = P.material("lit:cloth_panel", (0.07, 0.07, 0.075), rough=0.95)
liner = P.material("lit:headliner", (0.30, 0.30, 0.29), rough=0.95)
yellow = P.material("lit:knob_yellow", (0.75, 0.55, 0.02), rough=0.35)
red = P.material("lit:knob_red", (0.45, 0.03, 0.02), rough=0.3)
vent = P.material("lit:vent", (0.005, 0.005, 0.006), rough=0.8)

HOOD_UV = k.uv("bulkhead (hood)", (0, 1.0, 1.2), (0, 1, 0))
FLOOR_UV = k.uv("floor (lower door)", (-0.5, 0.6, 0.1), (-1, 0, 0))

# ---- Dashboard: black plastic block up to the windscreen, vents on top, open tray for the passenger ----
P.prism("dash", [(0.30, 0.95), (0.30, 1.22), (0.64, 1.30), (0.74, 1.30), (0.74, 0.95)], "x", -0.80, 0.80, plastic)
for i, x in enumerate((-0.60, -0.30, 0.0, 0.30, 0.60)):
    P.box(f"defrost_vent{i}", (x - 0.11, 1.298, 0.55), (x + 0.11, 1.302, 0.60), vent)
t0, t1 = MX(0.02, 0.78)           # the tray is on the passenger side
P.box("tray_floor", (t0, 1.02, 0.235), (t1, 1.04, 0.30), plastic)
P.box("tray_lip", (t0, 1.04, 0.225), (t1, 1.075, 0.24), plastic)
P.box("tray_back", (t0, 1.04, 0.296), (t1, 1.20, 0.30), vent)   # dark recess behind the lip
for i, x in enumerate((-0.30, -0.08)):   # driver side of the tray
    P.box(f"face_vent{i}", (M(x) - 0.06, 1.12, 0.296), (M(x) + 0.06, 1.18, 0.30), vent)
# Centre console under the dash: radio and heater sliders.
P.box("console", (-0.16, 0.38, 0.30), (0.16, 0.95, 0.56), plastic)
P.box("radio", (-0.11, 0.80, 0.293), (0.11, 0.90, 0.30), k.black)
P.box("radio_display", (-0.06, 0.86, 0.29), (0.06, 0.885, 0.293), P.material("lit:radio_glass", (0.25, 0.18, 0.05), rough=0.2))
for i, x in enumerate((-0.08, 0.0, 0.08)):
    P.box(f"heater_slot{i}", (x - 0.004, 0.66, 0.296), (x + 0.004, 0.76, 0.30), vent)
    P.box(f"heater_slider{i}", (x - 0.012, 0.70 + i * 0.02, 0.285), (x + 0.012, 0.715 + i * 0.02, 0.296), k.chrome)

# ---- Binnacle pod on the dash in front of the driver, tilted back towards the eyes ----
pod = k.panel("binnacle", (DX, 1.33, 0.24), Rx(18))
P.box("pod_housing", (-0.19, -0.09, 0.0), (0.19, 0.11, 0.10), plastic, parent=pod)
P.box("pod_visor", (-0.20, 0.11, -0.06), (0.20, 0.125, 0.10), plastic, parent=pod)
for s in (-1, 1):
    P.box(f"pod_side{'LR'[s > 0]}", (s * 0.19 - 0.006, -0.09, -0.04), (s * 0.19 + 0.006, 0.11, 0.0), plastic, parent=pod)
k.gauge("tacho", -0.072, 0.012, 0.062, "tacho.png", "rpm", 135, -135, 6000, parent=pod, bezel=k.black)
k.gauge("speedo", 0.072, 0.012, 0.062, "speedo.png", "speed", 135, -135, 140, parent=pod, bezel=k.black)
k.gauge("fuel", -0.158, -0.058, 0.027, "fuel.png", "fuel", 45, -45, 1.0, parent=pod, bezel=k.black)
k.gauge("temp", 0.158, -0.058, 0.027, "temp.png", "temp", 45, -45, 40, zero=-20, parent=pod, bezel=k.black)
k.lamps({"handbrake": -0.150, "engine": -0.118, "headlights": 0.118, "lowrange": 0.150}, 0.088, parent=pod, size=0.026)
k.gear_display(0.0, 0.088, parent=pod, size=0.03)

# ---- Steering wheel: flat, four black spokes, big centre pad; high, dials read over the rim ----
WC = (DX, 1.16, -0.02)
k.steering_wheel(WC, 40, radius=0.20, rim=0.016, spokes=(15, 165, 245, 295), spoke_mat=plastic, hub_r=0.065,
                 rim_mat=plastic, spoke_w=0.03, column=0.45, horn_mat=plastic)

# ---- Floor (painted, rubber mats in the footwells), tunnel, bulkhead, pedals ----
P.box("floor", (-0.86, 0.33, -1.80), (0.86, 0.375, 0.76), k.paint, uv=FLOOR_UV)
P.prism("tunnel", [(-0.18, 0.375), (-0.12, 0.62), (0.12, 0.62), (0.18, 0.375)], "z", -0.62, 0.70, k.paint, uv=FLOOR_UV)
P.prism("toe_board", [(0.60, 0.375), (0.74, 0.52), (0.74, 0.375)], "x", -0.86, 0.86, k.paint, uv=HOOD_UV)
P.box("bulkhead", (-0.86, 0.375, 0.74), (0.86, 0.95, 0.78), k.paint, uv=HOOD_UV)
for i, x in enumerate((DX, -DX)):
    P.box(f"floor_mat{i}", (x - 0.22, 0.375, -0.30), (x + 0.22, 0.383, 0.58), k.rubber)
for name, x, w in (("clutch", DX - 0.13, 0.065), ("brake", DX, 0.075), ("throttle", DX + 0.14, 0.045)):
    k.pedal(name, (x, 0.86, 0.60), name, w, arm=0.32)

# ---- Levers on the tunnel: gear stick, red transfer lever, yellow diff lock, handbrake by the seat ----
k.lever("gear_lever", (M(-0.02), 0.62, 0.30), 0.48, 18, 0.035, k.black, drive="gear")
k.lever("transfer_lever", (M(0.09), 0.62, 0.22), 0.38, 15, 0.026, red, drive="lowrange", a1=-22)
k.lever("difflock_lever", (M(0.14), 0.62, 0.17), 0.30, 12, 0.022, yellow, boot=0.035, shaft_r=0.008)
k.lever("handbrake_lever", (M(-0.15), 0.62, 0.02), 0.34, -8, 0.03, k.black, drive="handbrake", a1=-30, boot=0.04,
        shaft_r=0.014)

# ---- Seats: cloth with headrests in front, inward-facing benches on the rear wheel arches ----
for side, sx in (("driver", DX), ("passenger", -DX)):
    P.box(f"seat_{side}_frame", (sx - 0.20, 0.375, -0.62), (sx + 0.20, 0.70, -0.12), k.black)
    P.prism(f"seat_{side}_cushion", [(-0.64, 0.70), (-0.64, 0.83), (-0.12, 0.85), (-0.06, 0.81), (-0.08, 0.70)],
            "x", sx - 0.24, sx + 0.24, cloth)
    P.prism(f"seat_{side}_back", [(-0.70, 0.80), (-0.60, 0.83), (-0.65, 1.40), (-0.75, 1.40), (-0.79, 0.83)],
            "x", sx - 0.235, sx + 0.235, cloth)
    P.prism(f"seat_{side}_back_panel", [(-0.598, 0.90), (-0.592, 0.90), (-0.636, 1.30), (-0.642, 1.30)],
            "x", sx - 0.15, sx + 0.15, cloth_light)
    P.box(f"seat_{side}_headrest", (sx - 0.13, 1.44, -0.79), (sx + 0.13, 1.62, -0.67), cloth)
    for j, px in enumerate((-0.07, 0.07)):
        P.box(f"seat_{side}_post{j}", (sx + px - 0.008, 1.38, -0.74), (sx + px + 0.008, 1.44, -0.72), k.chrome)
for s in (-1, 1):
    side = "L" if s < 0 else "R"

    def X(a, b, s=s):
        return (min(s * a, s * b), max(s * a, s * b))

    a0, a1 = X(0.50, 0.86)
    P.box(f"wheel_arch_{side}", (a0, 0.375, -1.42), (a1, 0.70, -0.78), k.paint, uv=FLOOR_UV)
    b0, b1 = X(0.52, 0.76)
    P.box(f"bench_{side}", (b0, 0.70, -1.60), (b1, 0.78, -0.88), cloth)
    r0, r1 = X(0.74, 0.79)
    P.box(f"bench_back_{side}", (r0, 0.80, -1.58), (r1, 1.15, -0.90), cloth)

# ---- Body lining: door cards, painted door tops, pillars, roof edges with alpine skylights ----
for s in (-1, 1):
    side = "L" if s < 0 else "R"

    def X(a, b, s=s):
        return (min(s * a, s * b), max(s * a, s * b))

    d0, d1 = X(0.78, 0.86)
    P.box(f"door_{side}", (d0, 0.375, -0.35), (d1, 1.20, 0.56), k.paint,
          uv=k.uv(f"door {side}", (s * 0.5, 1.0, 0.1), (s, 0, 0)))
    c0, c1 = X(0.765, 0.78)
    P.box(f"door_card_{side}", (c0, 0.48, -0.30), (c1, 1.08, 0.50), plastic)
    h0, h1 = X(0.70, 0.765)
    P.box(f"door_pull_{side}", (h0, 0.98, -0.20), (h1, 1.01, 0.10), plastic)
    w0, w1 = X(0.75, 0.765)
    P.box(f"door_handle_{side}", (w0, 1.10, 0.25), (w1, 1.125, 0.36), k.chrome)
    crank = P.cylinder(f"window_crank_{side}", 0.012, 0.03, k.chrome, n=8)
    P.place(crank, (s * 0.765, 0.85, 0.05), P.Rz(90) @ P.Ry(90 * s))
    q0, q1 = X(0.78, 0.86)
    P.box(f"quarter_{side}", (q0, 0.375, -1.80), (q1, 1.20, -0.35), k.paint,
          uv=k.uv(f"quarter {side}", (s * 0.5, 1.1, -1.2), (s, 0, 0)))
    p0, p1 = X(0.74, 0.80)
    P.box(f"pillar_B_{side}", (p0, 1.20, -0.58), (p1, 1.80, -0.34), k.paint,
          uv=k.uv(f"B pillar {side}", (s * 0.5, 1.5, -0.46), (s, 0, 0)))
    P.box(f"pillar_D_{side}", (p0, 1.20, -1.80), (p1, 1.80, -1.59), k.paint,
          uv=k.uv(f"D pillar {side}", (s * 0.5, 1.5, -1.70), (s, 0, 0)))
    rail_uv = k.uv(f"roof edge {side}", (s * 0.5, 1.8, -0.2), (s, 0, 0))
    e0, e1 = X(0.68, 0.78)
    P.box(f"roof_edge_front_{side}", (e0, 1.71, -0.68), (e1, 1.96, 0.44), k.paint, uv=rail_uv)
    P.box(f"roof_edge_rear_{side}", (e0, 1.71, -1.80), (e1, 1.96, -1.52), k.paint, uv=rail_uv)
    P.box(f"roof_edge_low_{side}", (e0, 1.71, -1.52), (e1, 1.84, -0.68), k.paint, uv=rail_uv)   # alpine skylight above
    t0, t1 = X(0.68, 0.72)
    P.box(f"roof_edge_top_{side}", (t0, 1.93, -1.52), (t1, 1.96, -0.68), k.paint, uv=rail_uv)
    # A pillar along the windscreen edge.
    ap0, ap1 = X(0.745, 0.83)
    bottom, top = (1.30, 0.68), (1.84, 0.44)
    length = math.dist(bottom, top)
    ang = math.degrees(math.atan2(top[1] - bottom[1], top[0] - bottom[0]))
    pil = P.cbox(f"pillar_A_{side}", (ap1 - ap0, length, 0.08), k.paint,
                 uv=k.uv(f"A pillar {side}", (s * 0.6, 1.6, 0.4), (s, 0, 1)))
    P.place(pil, ((ap0 + ap1) / 2, (bottom[0] + top[0]) / 2, (bottom[1] + top[1]) / 2 - 0.02), Rx(ang))

P.box("header", (-0.80, 1.82, 0.30), (0.80, 1.96, 0.46), k.paint, uv=k.uv("header", (0, 1.80, 0.2), (0, 0.5, 1)))
P.box("headliner", (-0.68, 1.93, -1.78), (0.68, 1.955, 0.30), liner)
REAR_UV = k.uv("rear wall", (0, 1.0, -1.0), (0, 0, -1))
P.box("rear_wall_low", (-0.86, 0.375, -1.84), (0.86, 1.25, -1.80), k.paint, uv=REAR_UV)
P.box("rear_wall_top", (-0.86, 1.70, -1.84), (0.86, 1.96, -1.80), k.paint, uv=REAR_UV)
P.box("rear_wall_L", (-0.86, 1.25, -1.84), (-0.45, 1.70, -1.80), k.paint, uv=REAR_UV)
P.box("rear_wall_R", (0.45, 1.25, -1.84), (0.86, 1.70, -1.80), k.paint, uv=REAR_UV)

# Sun visors, mirror, wipers.
for i, x in enumerate((DX, -DX)):
    v = P.cbox(f"sun_visor{i}", (0.38, 0.014, 0.16), plastic)
    P.place(v, (x, 1.80, 0.36), Rx(-20))
P.cbox("mirror_stem", (0.02, 0.06, 0.02), k.black, centre=(0, 1.79, 0.40))
m = P.cbox("mirror", (0.22, 0.06, 0.025), k.black)
P.place(m, (0.0, 1.74, 0.39), P.Ry(-8 * SIDE))   # turned towards the driver
k.wipers(blades=[((-0.483, 1.363, 0.609), (-0.001, 1.41, 0.66)), ((0.118, 1.363, 0.609), (0.60, 1.41, 0.66))],
         arms=[((-0.60, 1.235, 0.70), (-0.30, 1.39, 0.625)), ((0.0, 1.235, 0.70), (0.293, 1.39, 0.625))])

k.export(EYE, P.ASSETS)
k.previews(EYE, P.ASSETS, K.standard_shots(EYE))
