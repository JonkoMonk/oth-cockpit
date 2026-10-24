# DingDing cockpit: an old-school off-roader interior (painted metal dash, big thin steering wheel,
# floor shifters), fitted to the body measured with measure.py. Exports Car_DingDing.glb and renders
# preview pictures with the real body around it (the body is NOT exported).
# Run: blender -b --factory-startup -P build_dingding.py -- <assets folder> <car folder>
#
# DingDing cabin (game coordinates, metres): floor 0.46, roof inside 2.06, walls x +-0.86,
# windscreen base y 1.40 z 0.43 to top y 2.0 z 0.31 (glass x +-0.73), hood top 1.34,
# door z -0.43..0.41, side windows y 1.38..1.86, B pillar z -0.53..-0.39, C pillar z -1.50..-1.35, rear z -1.78.
import math
import os
import sys

import bpy

sys.dont_write_bytecode = True   # no __pycache__ (it would hold full folder paths)
sys.path.insert(0, os.path.dirname(__file__))
import carref  # noqa: E402
import parts as P  # noqa: E402
from parts import Rx, Rz  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
P.ASSETS, CARS = args[0], args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

DX = -0.42                      # driver's centre line (left-hand drive)
EYE = (DX, 1.62, -0.44)

paint = P.material("paint:body", (0.65, 0.58, 0.40), rough=0.6)
vinyl = P.material("lit:vinyl", (0.025, 0.025, 0.027), rough=0.75)
seat_vinyl = P.material("lit:seat", (0.045, 0.04, 0.035), rough=0.8)
rubber = P.material("lit:rubber", (0.04, 0.04, 0.04), rough=0.95)
liner = P.material("lit:headliner", (0.42, 0.40, 0.35), rough=0.95)
black = P.material("lit:black", (0.010, 0.010, 0.011), rough=0.45)
chrome = P.material("lit:chrome", (0.55, 0.55, 0.56), rough=0.25, metal=1.0)
needle_m = P.material("lit:needle", (1.0, 0.28, 0.02), rough=0.5)
knob_m = P.material("lit:knob", (0.02, 0.02, 0.02), rough=0.3)

P.empty("eye", EYE)

# The real body, for paint colours (and the previews). Not exported.
body = carref.load_body("DingDing", CARS)
body.data.materials[0].use_backface_culling = True
_sampler = carref.PaintSampler(body, CARS, "DingDing")


def body_uv(label, origin, direction):
    """Paint spot of the outside panel a ray from inside hits: the lining takes that panel's colour."""
    return _sampler.at(label, origin, direction, P.PAINT_UV)


DASH_UV = body_uv("dash (hood)", (0, 1.0, 1.0), (0, 1, 0))

# ---- Dashboard: painted steel face, padded top rail, shelf up to the windscreen ----
P.box("dash_face", (-0.86, 0.96, 0.24), (0.86, 1.31, 0.30), paint, uv=DASH_UV)
P.prism("dash_shelf", [(0.24, 1.31), (0.24, 1.355), (0.44, 1.405), (0.44, 1.31)], "x", -0.86, 0.86, paint, uv=DASH_UV)
P.prism("dash_pad", [(0.20, 1.325), (0.215, 1.36), (0.30, 1.372), (0.30, 1.325)],
        "x", -0.85, 0.85, vinyl, smooth=False)
# Parts that touch never share a face (two surfaces in one place flicker in the game).
P.prism("dash_lower", [(0.245, 0.93), (0.245, 0.958), (0.598, 0.958), (0.598, 0.93)], "x", -0.80, 0.80, vinyl)
P.box("firewall", (-0.86, 0.46, 0.60), (0.86, 0.97, 0.64), paint, uv=DASH_UV)
# Glovebox (passenger side), centre console with radio and heater knobs.
P.box("glovebox", (0.22, 1.05, 0.232), (0.66, 1.24, 0.24), paint, uv=DASH_UV)
P.box("glovebox_handle", (0.40, 1.205, 0.222), (0.48, 1.215, 0.232), chrome)
P.box("grab_bar", (0.25, 1.265, 0.20), (0.63, 1.285, 0.22), chrome)
P.box("radio", (-0.11, 1.08, 0.225), (0.11, 1.22, 0.24), black)
P.box("radio_dial", (-0.06, 1.16, 0.222), (0.06, 1.195, 0.225), P.material("lit:radio_glass", (0.25, 0.18, 0.05), rough=0.2))
for i, x in enumerate((-0.085, 0.085)):
    k = P.cylinder(f"radio_knob{i}", 0.016, 0.02, chrome, n=12, z0=-0.02)
    P.place(k, (x, 1.12, 0.225))
for i, x in enumerate((-0.07, 0.0, 0.07)):
    k = P.cylinder(f"heater_knob{i}", 0.012, 0.015, black, n=10, z0=-0.015)
    P.place(k, (x, 1.047, 0.24))

# ---- Instrument cluster in front of the driver ----
CZ = 0.17                       # cluster face (towards the driver)
P.box("cluster", (DX - 0.33, 1.04, CZ), (DX + 0.33, 1.33, 0.245), black)
P.prism("cluster_hood", [(CZ - 0.035, 1.342), (CZ - 0.03, 1.355), (0.22, 1.365), (0.22, 1.33), (CZ, 1.33)],
        "x", DX - 0.335, DX + 0.335, vinyl)


def gauge(name, x, y, r, image, drive, a0, a1, full, zero=0.0, needle_len=0.9):
    """Dial face with bezel and a needle pivot (empty) that the mod turns."""
    bez = P.torus(name + "_bezel", r + 0.004, 0.006, chrome, n=32, m=6)
    shade = P.cylinder(name + "_well", r + 0.004, 0.012, black, n=32, z0=0.0)
    P.place(shade, (x, y, CZ - 0.001))
    P.place(bez, (x, y, CZ))
    face = P.disc(name + "_face", r, P.material("glow:" + name, image=image), n=40)
    P.place(face, (x, y, CZ - 0.002))
    face["backlight"] = 1
    piv = P.empty("needle_" + name, (x, y, CZ - 0.008), drive=drive, axis="z", a0=a0, a1=a1, zero=zero, full=full)
    P.cbox(name + "_needle", (0.004 if r > 0.05 else 0.003, r * needle_len, 0.002), needle_m,
           centre=(0, r * needle_len * 0.4, 0), parent=piv)
    cap = P.cylinder(name + "_cap", r * 0.1, 0.006, black, n=12, z0=-0.006, parent=piv)
    P.place(cap)
    return face


# Layout: the big dials are read THROUGH the upper half of the wheel (between hub and rim, seen from
# the eye), the top row (fuel, lamps, gear display, temperature) OVER the rim.
DIAL_Y, TOP_Y = 1.135, 1.275
gauge("tacho", DX - 0.085, DIAL_Y, 0.075, "tacho.png", "rpm", 135, -135, 6000)
gauge("speedo", DX + 0.085, DIAL_Y, 0.075, "speedo.png", "speed", 135, -135, 140)
gauge("fuel", DX - 0.24, TOP_Y, 0.036, "fuel.png", "fuel", 45, -45, 1.0)
gauge("temp", DX + 0.24, TOP_Y, 0.036, "temp.png", "temp", 45, -45, 40, zero=-20)

# Warning lamps (icons from lamps.png, 4 cells) and the gear display (gears.png, 8 cells).
LAMPS = [("handbrake", 0, (0.9, 0.06, 0.03)), ("engine", 3, (0.9, 0.06, 0.03)),
         ("headlights", 1, (0.10, 0.85, 0.20)), ("lowrange", 2, (1.0, 0.55, 0.0))]
for i, (name, cell, col) in enumerate(LAMPS):
    x = DX + (-0.15, -0.105, 0.105, 0.15)[i]
    q = P.quad("lamp_" + name, 0.034, 0.034, P.material("glow:lamp_" + name, col, image="lamps.png"),
               uv_rect=(cell / 4, 0, (cell + 1) / 4, 1))
    P.place(q, (x, TOP_Y, CZ - 0.002))
    q["lamp"] = name
P.box("gear_window", (DX - 0.035, TOP_Y - 0.03, CZ - 0.004), (DX + 0.035, TOP_Y + 0.03, CZ - 0.001), chrome)
g = P.quad("gear_display", 0.05, 0.05, P.material("glow:gear", (1.0, 0.55, 0.05), image="gears.png"),
           uv_rect=(0, 0, 1, 1))
P.place(g, (DX, TOP_Y, CZ - 0.005))
g["display"] = "gear"
g["cells"] = 8

# ---- Steering wheel: big thin rim, T spokes, on a column into the dash ----
WC = (DX, 1.12, -0.02)          # wheel centre: high, like an old off-roader
TILT = 25                       # degrees from vertical, top leaning forward
wheel = P.empty("steering_wheel", WC, Rx(TILT), drive="steer", axis="z", a0=270, a1=-270, zero=-1, full=1)
P.torus("wheel_rim", 0.215, 0.013, black, n=40, m=8, parent=wheel)
for i, a in enumerate((0, 180, 270)):
    sp = P.cbox(f"wheel_spoke{i}", (0.17, 0.022, 0.008), chrome, centre=(0.125, 0, 0.018), parent=wheel)   # from under the hub
    P.place(sp, rot=Rz(a))
hub = P.cylinder("wheel_hub", 0.05, 0.035, black, n=16, z0=0.0, parent=wheel)
P.place(hub)
horn = P.cylinder("wheel_horn", 0.035, 0.006, chrome, n=16, z0=-0.004, parent=wheel)
P.place(horn)
col = P.cylinder("column", 0.032, 0.42, black, n=12, z0=0.03, r1=0.04)
P.place(col, WC, Rx(TILT))
stalk = P.cbox("indicator_stalk", (0.15, 0.012, 0.012), black, centre=(-0.075, 0, 0))
P.place(stalk, (DX - 0.035, 1.065, 0.10), Rx(TILT) @ Rz(-10))

# ---- Floor (painted steel, rubber mats in the footwells), tunnel, pedals, levers ----
FLOOR_UV = body_uv("floor (lower door)", (-0.5, 0.75, 0.0), (-1, 0, 0))
P.box("floor", (-0.86, 0.455, -1.78), (0.86, 0.50, 0.60), paint, uv=FLOOR_UV)
P.prism("tunnel", [(-0.17, 0.50), (-0.11, 0.67), (0.11, 0.67), (0.17, 0.50)], "z", -0.45, 0.60, paint, uv=FLOOR_UV)
P.box("toe_board", (-0.86, 0.50, 0.50), (0.86, 0.60, 0.598), paint, uv=FLOOR_UV)
for i, x in enumerate((DX, -DX)):
    P.box(f"floor_mat{i}", (x - 0.24, 0.50, -0.28), (x + 0.24, 0.508, 0.50), rubber)
    P.box(f"toe_mat{i}", (x - 0.24, 0.60, 0.50), (x + 0.24, 0.608, 0.56), rubber)


def pedal(name, x, drive, pad_w):
    piv = P.empty("pedal_" + name, (x, 0.93, 0.47), drive=drive, axis="x", a0=0, a1=-18, zero=0, full=1)
    arm = P.cbox(name + "_arm", (0.018, 0.30, 0.018), chrome, centre=(0, -0.15, -0.02), parent=piv)
    pad = P.cbox(name + "_pad", (pad_w, 0.075, 0.014), rubber, centre=(0, -0.30, -0.035), parent=piv)
    P.place(pad, rot=Rx(-25))


pedal("clutch", DX - 0.13, "clutch", 0.065)
pedal("brake", DX + 0.0, "brake", 0.075)
pedal("throttle", DX + 0.14, "throttle", 0.045)

gear = P.empty("gear_lever", (-0.02, 0.67, 0.05), drive="gear", axis="x", a0=0, a1=0, zero=0, full=1)
P.prism("gear_boot", [(-0.06, 0.0), (-0.025, 0.07), (0.025, 0.07), (0.06, 0.0)], "z", -0.06, 0.06, rubber, parent=gear)
shaft = P.cylinder("gear_shaft", 0.011, 0.42, chrome, n=8, z0=0.0, parent=gear)
P.place(shaft, rot=Rx(-105))          # z axis tipped up, leaning back 15 degrees
knob = P.ball("gear_knob", 0.035, knob_m, parent=gear)
P.place(knob, (0, 0.406, -0.109))

tc = P.empty("transfer_lever", (0.10, 0.67, 0.0), drive="lowrange", axis="x", a0=0, a1=-22, zero=0, full=1)
P.prism("transfer_boot", [(-0.04, 0.0), (-0.018, 0.05), (0.018, 0.05), (0.04, 0.0)], "z", -0.04, 0.04, rubber, parent=tc)
tshaft = P.cylinder("transfer_shaft", 0.009, 0.30, chrome, n=8, parent=tc)
P.place(tshaft, rot=Rx(-105))
tknob = P.ball("transfer_knob", 0.026, P.material("lit:knob_red", (0.45, 0.03, 0.02), rough=0.3), parent=tc)
P.place(tknob, (0, 0.29, -0.078))

# Handbrake: T-handle under the dash that pulls out towards the driver (slides, doesn't turn).
HB = (-0.03, 1.0, 0.236)
hb = P.empty("handbrake_handle", HB, drive="handbrake", move="slide", axis="z", a0=0, a1=-0.11, zero=0, full=1)
P.cbox("handbrake_shaft", (0.012, 0.012, 0.16), chrome, centre=(0, 0, 0.065), parent=hb)
P.cbox("handbrake_grip", (0.11, 0.026, 0.03), chrome, centre=(0, 0, -0.02), parent=hb)
P.cbox("handbrake_grip_rubber", (0.06, 0.03, 0.034), black, centre=(0, 0, -0.02), parent=hb)
P.box("handbrake_bezel", (HB[0] - 0.02, HB[1] - 0.015, 0.236), (HB[0] + 0.02, HB[1] + 0.015, 0.24), chrome)

# ---- Seats (simple vinyl buckets) ----
for side, sx in (("driver", DX), ("passenger", -DX)):
    P.box(f"seat_{side}_frame", (sx - 0.22, 0.50, -0.85), (sx + 0.22, 0.80, -0.30), black)
    P.prism(f"seat_{side}_cushion", [(-0.86, 0.80), (-0.86, 0.93), (-0.30, 0.95), (-0.22, 0.91), (-0.24, 0.80)],
            "x", sx - 0.25, sx + 0.25, seat_vinyl)
    P.prism(f"seat_{side}_back", [(-0.86, 0.90), (-0.76, 0.92), (-0.84, 1.62), (-0.93, 1.62), (-0.95, 0.92)],
            "x", sx - 0.245, sx + 0.245, seat_vinyl)   # a hair narrower than the cushion: no shared sides

# ---- Body lining: door cards, quarter panels, pillars, header, headliner, rear wall ----
for s in (-1, 1):
    side = "L" if s < 0 else "R"

    def X(a, b):
        """x range from the wall inwards: a, b = distances from the centre line."""
        return (min(s * a, s * b), max(s * a, s * b))

    x0, x1 = X(0.80, 0.86)
    door_uv = body_uv(f"door {side}", (s * 0.5, 1.2, 0.0), (s, 0, 0))
    P.box(f"door_{side}", (x0, 0.50, -0.43), (x1, 1.37, 0.41), paint, uv=door_uv)
    # Kick panel: side wall between door and firewall, beside the footwell (else you see out there).
    k0, k1 = X(0.80, 0.855)
    P.box(f"kick_panel_{side}", (k0, 0.501, 0.411), (k1, 1.31, 0.599), paint, uv=door_uv)
    c0, c1 = X(0.775, 0.80)
    P.box(f"door_card_{side}", (c0, 0.60, -0.38), (c1, 1.18, 0.34), vinyl)
    a0_, a1_ = X(0.72, 0.775)
    P.box(f"armrest_{side}", (a0_, 1.02, -0.30), (a1_, 1.07, 0.05), vinyl)
    h0, h1 = X(0.755, 0.775)
    P.box(f"door_handle_{side}", (h0, 1.12, 0.10), (h1, 1.14, 0.22), chrome)
    crank = P.cylinder(f"window_crank_{side}", 0.012, 0.03, chrome, n=8)
    P.place(crank, (s * 0.775, 0.90, 0.0), Rz(90) @ P.Ry(90 * s))
    q0, q1 = X(0.80, 0.86)
    P.box(f"quarter_{side}", (q0, 0.50, -1.78), (q1, 1.37, -0.43), paint,
          uv=body_uv(f"quarter {side}", (s * 0.5, 1.1, -1.1), (s, 0, 0)))
    P.box(f"pillar_B_{side}", (q0, 1.37, -0.53), (q1, 1.87, -0.39), paint,
          uv=body_uv(f"B pillar {side}", (s * 0.5, 1.6, -0.46), (s, 0, 0)))
    P.box(f"pillar_C_{side}", (q0, 1.37, -1.50), (q1, 1.87, -1.35), paint,
          uv=body_uv(f"C pillar {side}", (s * 0.5, 1.6, -1.42), (s, 0, 0)))
    P.box(f"roof_rail_{side}", (q0, 1.87, -1.78), (q1, 2.06, 0.32), paint,
          uv=body_uv(f"roof rail {side}", (s * 0.5, 1.96, -0.6), (s, 0, 0)))
    # A pillar: slanted bar along the windscreen edge.
    ap0, ap1 = X(0.73, 0.86)
    bottom, top = (1.40, 0.425), (2.02, 0.30)
    length = math.dist(bottom, top)
    ang = math.degrees(math.atan2(top[1] - bottom[1], top[0] - bottom[0]))   # lean back
    pil = P.cbox(f"pillar_A_{side}", (ap1 - ap0, length, 0.08), paint,
                 uv=body_uv(f"A pillar {side}", (s * 0.6, 1.7, 0.2), (s, 0, 1)))
    P.place(pil, ((ap0 + ap1) / 2, (bottom[0] + top[0]) / 2, (bottom[1] + top[1]) / 2 - 0.02), Rx(ang))

P.box("header", (-0.86, 1.97, 0.22), (0.86, 2.06, 0.34), paint, uv=body_uv("header", (0, 1.9, 0.0), (0, 0.4, 1)))
P.box("headliner", (-0.80, 2.01, -1.76), (0.80, 2.055, 0.22), liner)
# Rear wall with a window opening.
REAR_UV = body_uv("rear wall", (0, 1.1, -1.0), (0, 0, -1))
P.box("rear_wall_low", (-0.86, 0.50, -1.80), (0.86, 1.42, -1.76), paint, uv=REAR_UV)
P.box("rear_wall_top", (-0.86, 1.86, -1.80), (0.86, 2.06, -1.76), paint, uv=REAR_UV)
P.box("rear_wall_L", (-0.86, 1.42, -1.80), (-0.55, 1.86, -1.76), paint, uv=REAR_UV)
P.box("rear_wall_R", (0.55, 1.42, -1.80), (0.86, 1.86, -1.76), paint, uv=REAR_UV)

# Sun visors and rear-view mirror.
for i, x in enumerate((DX, -DX)):
    v = P.cbox(f"sun_visor{i}", (0.40, 0.014, 0.17), vinyl)
    P.place(v, (x, 1.955, 0.17), Rx(-12))
P.cbox("mirror_stem", (0.02, 0.07, 0.02), black, centre=(0, 1.93, 0.27))
m = P.cbox("mirror", (0.24, 0.065, 0.025), black)
P.place(m, (0.0, 1.88, 0.26), P.Ry(8))

# The body has a box on the hood in front of the driver; it is only drawn from outside, so from the
# seat just one floating edge shows. A closed copy at the same place makes it a solid object.
P.prism("hood_box", [(0.416, 1.356), (0.416, 1.462), (0.43, 1.477), (0.485, 1.477), (0.498, 1.462), (0.498, 1.356)],
        "x", -0.617, -0.316, P.material("lit:hood_box", (0.035, 0.035, 0.04), rough=0.6))

# Wipers: the body's own wipers sit outside the glass and are only drawn from the outside, so from
# the seat you'd see just their edges. These closed copies (same place, from measure of the body)
# are visible from inside too.
wiper_m = P.material("lit:wiper", (0.035, 0.035, 0.035), rough=0.6)
for i, (x0, x1) in enumerate(((-0.584, -0.150), (-0.044, 0.391))):
    P.box(f"wiper_blade{i}", (x0, 1.536, 0.392), (x1, 1.568, 0.418), wiper_m)
for i, (x0, x1) in enumerate(((-0.043, -0.307), (0.498, 0.234))):
    a, b = (x0, 1.39), (x1, 1.555)
    arm = P.cbox(f"wiper_arm{i}", (math.dist(a, b), 0.014, 0.012), wiper_m)
    P.place(arm, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.418),
            Rz(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))))

P.check_flicker(exclude=[body], eye=EYE)
P.export(os.path.join(P.ASSETS, "Car_DingDing.glb"), exclude=[body])

# ---- Preview pictures with the real body (single-sided, like in the game) ----
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.5
sun.rotation_euler = (math.radians(35), math.radians(15), math.radians(-30))
scene.collection.objects.link(sun)
world = bpy.data.worlds.new("w")
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.65, 0.8, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
scene.world = world
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
scene.camera = cam
LOOK_FWD = P.Matrix(((-1, 0, 0), (0, 0, -1), (0, -1, 0)))


def shot(name, pos, rot, fov):
    cam.data.lens_unit = "FOV"
    cam.data.sensor_fit = "VERTICAL"     # like the game's field of view setting
    cam.data.angle = math.radians(fov)
    cam.data.clip_start = 0.02
    P.place(cam, pos, rot @ LOOK_FWD)
    scene.render.filepath = os.path.join(P.ASSETS, f"Car_DingDing_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("wrote", scene.render.filepath)


shot("eye", EYE, Rx(10), 70)
shot("user", EYE, Rx(6), 85)
shot("eye_right", EYE, P.Ry(45) @ Rx(15), 70)
shot("eye_down", EYE, Rx(30), 70)
shot("handbrake", EYE, P.Ry(28) @ Rx(38), 40)
shot("floor_right", EYE, P.Ry(50) @ Rx(45), 85)
shot("floor_right_low", (0.30, 1.30, -0.30), P.Ry(35) @ Rx(40), 90)
shot("floor_left_low", (-0.30, 1.30, -0.30), P.Ry(-35) @ Rx(40), 90)
shot("back_seat", (0.3, 1.75, -1.4), P.Ry(-10) @ Rx(15), 70)
