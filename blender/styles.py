# Cockpit styles for the generic car builder (build_car.py). A car's entry in cars_config.py picks a style
# for each part (dash, instruments, steering wheel, seats, levers) and tunes it; positions come from the
# automatic measurements of the real body (kit.measure), so every cockpit fits its car.
# All coordinates are GAME coordinates (x right, y up, z forward; see parts.py).
import math

import parts as P
from parts import Rx, Rz

MATS = {}


def mat(name, color, rough=0.7, metal=0.0):
    key = f"lit:{name}"
    if key not in MATS:
        MATS[key] = P.material(key, color, rough=rough, metal=metal)
    return MATS[key]


# Shared material palette (linear colours).
def palette(cfg):
    c = cfg.get("colors", {})
    return {
        "plastic": mat("plastic", c.get("plastic", (0.018, 0.018, 0.02)), 0.7),
        "plastic2": mat("plastic_grey", c.get("plastic2", (0.06, 0.06, 0.062)), 0.75),
        "vinyl": mat("vinyl", c.get("vinyl", (0.025, 0.025, 0.027)), 0.75),
        "seat": mat("seat", c.get("seat", (0.04, 0.04, 0.045)), 0.9),
        "seat2": mat("seat_panel", c.get("seat2", (0.08, 0.075, 0.07)), 0.9),
        "liner": mat("headliner", c.get("liner", (0.30, 0.30, 0.29)), 0.95),
        "wood": mat("wood", (0.20, 0.08, 0.025), 0.45),
        "carpet": mat("carpet", c.get("carpet", (0.03, 0.03, 0.032)), 1.0),
        "vent": mat("vent", (0.005, 0.005, 0.006), 0.8),
        "red": mat("knob_red", (0.45, 0.03, 0.02), 0.3),
        "yellow": mat("knob_yellow", (0.75, 0.55, 0.02), 0.35),
        "ivory": mat("ivory", (0.55, 0.50, 0.40), 0.35),
        "glass": mat("radio_glass", (0.25, 0.18, 0.05), 0.2),
    }


class Layout:
    """Where things go in this car, from the measurements and the config."""

    def __init__(self, k, m, cfg):
        ws = m["ws"]
        self.side = cfg.get("side", -1)                  # -1 left-hand drive, +1 right-hand drive
        self.wall = k.wall(ws["base_y"] - 0.3, ws["base_y"] - 0.05, ws["base_z"] - 0.6, ws["base_z"] - 0.2)
        self.dx = self.side * cfg.get("driver_x", min(0.42, self.wall * 0.52))
        eye_y = cfg.get("eye_y", min(ws["base_y"] + 0.27, m["roof"] - 0.32))
        eye_z = cfg.get("eye_z", max(ws["base_z"] - 0.85, m["rear"] + 0.40))
        self.eye = (self.dx, eye_y, eye_z)
        self.floor, self.roof = m["floor"], m["roof"]
        self.ws = ws
        # Dash: its face towards the driver, its top meeting the windscreen.
        self.face_z = cfg.get("dash_z", eye_z + 0.60)
        self.top_y = ws["base_y"] - 0.015
        self.face_top = min(self.top_y - 0.04, eye_y - cfg.get("dash_below_eye", 0.28))
        self.face_bottom = self.face_top - cfg.get("dash_height", 0.36)
        self.dash_front = ws["base_z"] + 0.02
        # Steering wheel.
        self.wheel_r = cfg.get("wheel_r", 0.20)
        self.tilt = cfg.get("wheel_tilt", 30)
        self.wc = (self.dx, eye_y - cfg.get("wheel_drop", 0.47), eye_z + cfg.get("wheel_dist", 0.40))

    def m(self, x):
        """x of a part drawn for a left-hand drive car, on this car's driver side."""
        return -self.side * x

    def mx(self, a, b):
        return (min(self.m(a), self.m(b)), max(self.m(a), self.m(b)))

    def rim_top(self):
        t = math.radians(self.tilt)
        return self.wc[1] + self.wheel_r * math.cos(t), self.wc[2] + self.wheel_r * math.sin(t)

    def sight_y(self, z):
        """Height at depth z of the line from the eye over the top of the steering wheel rim."""
        ry, rz = self.rim_top()
        ey, ez = self.eye[1], self.eye[2]
        return ey + (ry + 0.012 - ey) * (z - ez) / (rz - ez)


# ---------------------------------------------------------------- dash ----

def dash(k, L, cfg, pal):
    style = cfg.get("dash", "plastic")
    w = L.wall - 0.005
    ft, fb, fz, top, front = L.face_top, L.face_bottom, L.face_z, L.top_y, L.dash_front
    body = pal["plastic"]
    if style in ("painted", "painted_pad"):
        body_uv = k.uv("dash (hood)", (0, L.ws["base_y"] - 0.2, L.ws["base_z"] + 0.5), (0, 1, 0))
        P.box("dash_face", (-w, fb, fz), (w, ft, fz + 0.06), k.paint, uv=body_uv)
        P.prism("dash_top", [(fz, ft), (fz, ft + 0.03), (front, top), (front, ft)], "x", -w, w, k.paint, uv=body_uv)
        if style == "painted_pad":
            P.prism("dash_pad", [(fz - 0.07, ft - 0.025), (fz - 0.055, ft + 0.02), (fz + 0.06, ft + 0.035), (fz + 0.06, ft - 0.025)],
                    "x", -w + 0.01, w - 0.01, pal["vinyl"])
        if front - 0.1 > fz + 0.06:
            P.prism("dash_under", [(fz + 0.005, fb - 0.03), (fz + 0.005, fb), (front - 0.1, fb), (front - 0.1, fb - 0.03)],
                    "x", -w, w, pal["vinyl"])
    else:
        mat_ = {"plastic": pal["plastic"], "grey": pal["plastic2"], "wood": pal["plastic"], "shelf": pal["plastic"]}.get(style, body)
        P.prism("dash", [(fz, fb), (fz, ft), (fz + 0.06, ft + 0.03), (front, top), (front + 0.05, top - 0.02), (front + 0.05, fb)],
                "x", -w, w, mat_)
        if style == "wood":
            P.box("dash_wood", (-w + 0.02, ft - 0.11, fz - 0.006), (w - 0.02, ft - 0.05, fz), pal["wood"])
        if style == "shelf":
            # An open fabric shelf across the dash, the instruments in a small box in front of the driver.
            P.box("shelf_floor", (-w + 0.02, fb + 0.02, fz - 0.16), (w - 0.02, fb + 0.04, fz), pal["seat"])
            P.box("shelf_lip", (-w + 0.02, fb + 0.04, fz - 0.17), (w - 0.02, fb + 0.07, fz - 0.15), pal["plastic2"])
    # Defrost vents along the top.
    vw = min(0.09, w * 0.15)   # narrow cabs get narrower vents
    for i in range(5):
        x = -w * 0.8 + i * w * 0.4
        P.box(f"defrost_vent{i}", (x - vw, top - 0.001, front - 0.12), (x + vw, top + 0.003, front - 0.07), pal["vent"])
    # Centre: radio and heater controls (not where the instruments sit in the middle).
    cy = (ft + fb) / 2
    if cfg.get("cluster") != "center":
        P.box("radio", (-0.11, cy - 0.06, fz - 0.012), (0.11, cy + 0.04, fz), pal["plastic"])
        P.box("radio_display", (-0.06, cy, fz - 0.016), (0.06, cy + 0.025, fz - 0.012), pal["glass"])
    for i, x in enumerate((-0.08, 0.0, 0.08)):
        knob = P.cylinder(f"heater_knob{i}", 0.013, 0.016, k.chrome if style.startswith("painted") else pal["plastic2"], n=10, z0=-0.016)
        P.place(knob, (x, cy - 0.10, fz))
    # Glovebox or tray on the passenger side.
    gx0, gx1 = L.mx(0.20, w - 0.08)
    if cfg.get("glovebox", True):
        mat_g = k.paint if style.startswith("painted") else pal["plastic"]
        uv = k.uv("glovebox", (0, L.ws["base_y"] - 0.2, L.ws["base_z"] + 0.5), (0, 1, 0)) if mat_g is k.paint else None
        P.box("glovebox", (gx0, cy - 0.08, fz - 0.008), (gx1, cy + 0.06, fz), mat_g, uv=uv)
        hx = (gx0 + gx1) / 2
        P.box("glovebox_handle", (hx - 0.04, cy + 0.035, fz - 0.016), (hx + 0.04, cy + 0.048, fz - 0.008), k.chrome)
    if cfg.get("grab_bar"):
        bx0, bx1 = L.mx(0.18, w - 0.06)
        P.box("grab_bar", (bx0, ft - 0.03, fz - 0.06), (bx1, ft - 0.012, fz - 0.042), k.chrome)
        for i, bx in enumerate((bx0 + 0.01, bx1 - 0.03)):
            P.box(f"grab_bar_post{i}", (bx, ft - 0.028, fz - 0.058), (bx + 0.02, ft - 0.014, fz), k.chrome)
    # Firewall and the floor.
    fw_uv = k.uv("firewall (hood)", (0, L.ws["base_y"] - 0.2, L.ws["base_z"] + 0.5), (0, 1, 0))
    P.box("firewall", (-w, L.floor, front), (w, fb, front + 0.04), k.paint, uv=fw_uv)


def floor(k, L, cfg, pal, m):
    w = L.wall + 0.02
    uv = k.uv("floor (lower side)", (0, L.floor + 0.15, L.eye[2]), (-1, 0, 0))
    P.box("floor", (-w, L.floor - 0.04, m["rear"]), (w, L.floor + 0.005, L.dash_front), k.paint, uv=uv)
    mat_ = pal["carpet"] if cfg.get("carpet") else k.rubber
    mw = min(0.22, abs(L.dx) - 0.03)
    for i, x in enumerate((L.dx, -L.dx)):
        P.box(f"floor_mat{i}", (x - mw, L.floor + 0.005, L.eye[2] + 0.05), (x + mw, L.floor + 0.013, L.dash_front - 0.08), mat_)
    if cfg.get("tunnel", True):
        th = cfg.get("tunnel_h", 0.20)
        P.prism("tunnel", [(-0.17, L.floor + 0.005), (-0.11, L.floor + th), (0.11, L.floor + th), (0.17, L.floor + 0.005)],
                "z", L.eye[2] - 0.45, L.dash_front - 0.02, k.paint, uv=uv)


# ----------------------------------------------------------- instruments ----

def instruments(k, L, cfg, pal):
    style = cfg.get("cluster", "hood")
    bezel = k.black if cfg.get("bezel", "chrome") == "black" else k.chrome
    dx = L.dx
    if style == "pod":
        # A square pod on top of the dash, read over the steering wheel.
        z = L.face_z - 0.04
        y0 = max(L.sight_y(z) + 0.02, L.face_top - 0.10)
        pod = k.panel("binnacle", (dx, y0 + 0.09, z), Rx(18))
        painted = cfg.get("pod_mat") == "paint"
        pmat = k.paint if painted else pal["plastic"]
        puv = k.uv("pod (hood)", (0, L.ws["base_y"] - 0.2, L.ws["base_z"] + 0.5), (0, 1, 0)) if painted else None
        P.box("pod_housing", (-0.19, -0.09, 0.0), (0.19, 0.11, 0.10), pmat, parent=pod, uv=puv)
        P.box("pod_visor", (-0.20, 0.11, -0.06), (0.20, 0.125, 0.10), pmat, parent=pod, uv=puv)
        if cfg.get("pod_trim") == "chrome":
            P.box("pod_trim_top", (-0.195, 0.105, -0.065), (0.195, 0.112, -0.055), k.chrome, parent=pod)
            P.box("pod_trim_bottom", (-0.19, -0.095, -0.012), (0.19, -0.088, -0.004), k.chrome, parent=pod)
        k.gauge("tacho", -0.072, 0.012, 0.062, "tacho.png", "rpm", 135, -135, 6000, parent=pod, bezel=bezel)
        k.gauge("speedo", 0.072, 0.012, 0.062, "speedo.png", "speed", 135, -135, 140, parent=pod, bezel=bezel)
        k.gauge("fuel", -0.158, -0.058, 0.027, "fuel.png", "fuel", 45, -45, 1.0, parent=pod, bezel=bezel)
        k.gauge("temp", 0.158, -0.058, 0.027, "temp.png", "temp", 45, -45, 40, zero=-20, parent=pod, bezel=bezel)
        k.lamps({"handbrake": -0.150, "engine": -0.118, "headlights": 0.118, "lowrange": 0.150}, 0.088, parent=pod, size=0.026)
        k.gear_display(0.0, 0.088, parent=pod, size=0.03)
        return
    if style in ("hood", "wide"):
        # Recessed cluster under a hood: big dials read through the top of the wheel or over it.
        cz = L.face_z - 0.05
        width = 0.33 if style == "hood" else 0.40
        top = min(L.face_top + 0.015, L.top_y - 0.03)
        bottom = top - 0.26
        P.box("cluster", (dx - width, bottom, cz), (dx + width, top, L.face_z + 0.01), pal["plastic"])
        P.prism("cluster_hood", [(cz - 0.045, top + 0.012), (cz - 0.04, top + 0.03), (L.face_z + 0.02, top + 0.04),
                                 (L.face_z + 0.02, top), (cz, top)], "x", dx - width - 0.01, dx + width + 0.01,
                pal["vinyl"] if cfg.get("dash", "plastic").startswith("painted") else pal["plastic"])
        r = cfg.get("dial_r", 0.075)
        dial_y = max((top + bottom) / 2 - 0.02, L.sight_y(cz) - 0.05)
        dial_y = min(dial_y, top - 0.07 - r)   # below the row of lamps and small gauges
        k.standard_gauges(dx, dial_y, top - 0.035, z=cz, r=r, small=0.032, spread=r + 0.012, outer=width - 0.07)
        lamps_y = top - 0.035
        k.lamps({"handbrake": dx - 0.16, "engine": dx - 0.115, "headlights": dx + 0.115, "lowrange": dx + 0.16}, lamps_y, z=cz, size=0.03)
        k.gear_display(dx, lamps_y, z=cz, size=0.04)
        if style == "wide":
            P.box("cluster_trim", (dx - width, bottom - 0.012, cz - 0.004), (dx + width, bottom, cz), k.chrome)
        return
    if style == "center":
        # Instruments in the middle of the dash (old utility vehicles).
        cz = L.face_z - 0.004
        cy = (L.face_top + L.face_bottom) / 2 + 0.06
        P.box("center_panel", (-0.25, cy - 0.12, cz), (0.25, cy + 0.10, L.face_z + 0.01), pal["plastic"])
        k.gauge("speedo", -0.10, cy, 0.075, "speedo.png", "speed", 135, -135, 140, z=cz, bezel=bezel)
        k.gauge("tacho", 0.07, cy + 0.02, 0.05, "tacho.png", "rpm", 135, -135, 6000, z=cz, bezel=bezel)
        k.gauge("fuel", 0.17, cy + 0.035, 0.03, "fuel.png", "fuel", 45, -45, 1.0, z=cz, bezel=bezel)
        k.gauge("temp", 0.17, cy - 0.045, 0.03, "temp.png", "temp", 45, -45, 40, zero=-20, z=cz, bezel=bezel)
        k.lamps({"handbrake": -0.20, "engine": -0.16, "headlights": 0.0, "lowrange": 0.05}, cy - 0.095, z=cz, size=0.028)
        k.gear_display(0.12, cy - 0.095, z=cz, size=0.034)
        return
    if style == "single":
        # One big round speedometer in front of the driver with the small gauges around it (40s-60s).
        cz = L.face_z - 0.004
        cy = min(L.face_top - 0.11, max(L.sight_y(cz) + 0.02, (L.face_top + L.face_bottom) / 2))
        k.gauge("speedo", dx, cy, 0.095, "speedo.png", "speed", 135, -135, 140, z=cz, bezel=bezel)
        k.gauge("tacho", dx + L.m(-0.17), cy + 0.03, 0.045, "tacho.png", "rpm", 135, -135, 6000, z=cz, bezel=bezel)
        k.gauge("fuel", dx + L.m(0.16), cy + 0.04, 0.032, "fuel.png", "fuel", 45, -45, 1.0, z=cz, bezel=bezel)
        k.gauge("temp", dx + L.m(0.16), cy - 0.04, 0.032, "temp.png", "temp", 45, -45, 40, zero=-20, z=cz, bezel=bezel)
        k.lamps({"handbrake": dx - 0.05, "engine": dx - 0.015, "headlights": dx + 0.02, "lowrange": dx + 0.055},
                cy + 0.118, z=cz, size=0.026)   # above the speedo: below it they hide behind the wheel
        k.gear_display(dx + L.m(-0.17), cy - 0.06, z=cz, size=0.032)
        return
    if style == "row":
        # A row of small gauges on a flat steel panel (military / truck).
        cz = L.face_z - 0.004
        cy = min(L.face_top - 0.08, max(L.sight_y(cz) + 0.04, (L.face_top + L.face_bottom) / 2 + 0.05))
        P.box("gauge_panel", (dx - 0.30, cy - 0.10, cz), (dx + 0.30, cy + 0.07, L.face_z + 0.01), pal["plastic2"])
        k.gauge("speedo", dx - 0.07, cy, 0.06, "speedo.png", "speed", 135, -135, 140, z=cz, bezel=bezel)
        k.gauge("tacho", dx + 0.07, cy, 0.06, "tacho.png", "rpm", 135, -135, 6000, z=cz, bezel=bezel)
        k.gauge("fuel", dx - 0.20, cy, 0.04, "fuel.png", "fuel", 45, -45, 1.0, z=cz, bezel=bezel)
        k.gauge("temp", dx + 0.20, cy, 0.04, "temp.png", "temp", 45, -45, 40, zero=-20, z=cz, bezel=bezel)
        k.lamps({"handbrake": dx - 0.24, "engine": dx - 0.20, "headlights": dx + 0.20, "lowrange": dx + 0.24}, cy - 0.075,
                z=cz, size=0.026)
        k.gear_display(dx, cy - 0.075, z=cz, size=0.032)
        for i, x in enumerate((-0.12, -0.08, 0.08, 0.12)):   # toggle switches
            P.cbox(f"toggle{i}", (0.008, 0.008, 0.03), k.chrome, centre=(dx + x, cy - 0.075, cz - 0.015))
        return
    raise ValueError(f"cluster style {style}")


# -------------------------------------------------------------- controls ----

WHEELS = {
    "t": dict(spokes=(0, 180, 270), spoke_w=0.022),
    "three": dict(spokes=(30, 150, 270), spoke_w=0.026),
    "two": dict(spokes=(0, 180), spoke_w=0.03),
    "four": dict(spokes=(15, 165, 245, 295), spoke_w=0.03),
    "banjo": dict(spokes=(20, 60, 120, 160, 250, 290), spoke_w=0.008),
}


def controls(k, L, cfg, pal):
    wcfg = WHEELS[cfg.get("wheel", "t")]
    rim = {"black": k.black, "ivory": pal["ivory"], "wood": pal["wood"], "plastic": pal["plastic"]}[cfg.get("rim", "black")]
    spoke = {"chrome": k.chrome, "black": pal["plastic"], "ivory": pal["ivory"]}[cfg.get("spoke_mat", "chrome")]
    k.steering_wheel(L.wc, L.tilt, radius=L.wheel_r, rim=cfg.get("rim_thick", 0.014), spokes=wcfg["spokes"], spoke_mat=spoke,
                     hub_r=cfg.get("hub_r", 0.05), rim_mat=rim, spoke_w=wcfg["spoke_w"],
                     column=max(0.08, (L.face_z - L.wc[2]) / math.cos(math.radians(L.tilt)) - 0.03),   # ends at the dash
                     horn_mat=k.chrome if cfg.get("horn", "chrome") == "chrome" else pal["plastic"])
    # Pedals hang from under the dash.
    py = L.face_bottom - 0.03
    pz = L.face_z + 0.22
    arm = max(0.18, py - L.floor - 0.10)
    pedals = (("clutch", -0.13, 0.065), ("brake", 0.0, 0.075), ("throttle", 0.14, 0.045))
    if cfg.get("automatic"):
        pedals = (("brake", -0.04, 0.10), ("throttle", 0.13, 0.05))
    for name, off, w in pedals:
        k.pedal(name, (L.dx + off, py, pz), name, w, arm=arm)
    # Levers.
    tunnel_top = L.floor + cfg.get("tunnel_h", 0.20)
    lz = L.eye[2] + 0.30
    if cfg.get("shifter", "floor") == "floor":
        k.lever("gear_lever", (L.m(-0.02), tunnel_top, lz), cfg.get("gear_len", 0.42), 15, 0.034,
                pal["plastic"] if cfg.get("knob", "black") == "black" else pal["ivory"], drive="gear")
    elif cfg["shifter"] == "dash":
        # Push-pull gear lever coming out of the dash (small French cars).
        piv = P.empty("gear_lever", (L.m(-0.12), L.face_bottom + 0.06, L.face_z - 0.01), drive="gear", axis="x", a0=0, a1=0, zero=0, full=1)
        rod = P.cylinder("gear_rod", 0.009, 0.20, k.chrome, n=8, parent=piv)
        P.place(rod, rot=Rx(180))
        knob = P.ball("gear_knob", 0.03, pal["plastic"], parent=piv)
        P.place(knob, (0, 0, -0.20))
    elif cfg["shifter"] == "column":
        piv = P.empty("gear_lever", (L.dx + L.m(0.06), L.wc[1] - 0.06, L.wc[2] + 0.12), drive="gear", axis="x", a0=0, a1=0, zero=0, full=1)
        k.beam("column_shift_arm", (L.dx + L.m(0.06), L.wc[1] - 0.06, L.wc[2] + 0.12),
               (L.dx + L.m(0.28), L.wc[1] - 0.02, L.wc[2] + 0.02), 0.012, 0.012, k.chrome)
    if cfg.get("transfer", True):
        k.lever("transfer_lever", (L.m(0.09), tunnel_top, lz - 0.08), 0.32, 15, 0.026, pal["red"], drive="lowrange")
    if cfg.get("difflock"):
        k.lever("difflock_lever", (L.m(0.14), tunnel_top, lz - 0.12), 0.26, 12, 0.022, pal["yellow"], boot=0.035, shaft_r=0.008)
    hb = cfg.get("handbrake", "lever")
    if hb == "lever":
        k.lever("handbrake_lever", (L.m(-0.15), tunnel_top, L.eye[2] + 0.05), 0.32, -8, 0.03, pal["plastic"], drive="handbrake",
                a1=-30, boot=0.04, shaft_r=0.014)
    elif hb == "pull":
        hx = L.dx + L.m(0.30)
        y = L.face_bottom + 0.04
        h = P.empty("handbrake_handle", (hx, y, L.face_z - 0.004), drive="handbrake", move="slide", axis="z", a0=0, a1=-0.11, zero=0, full=1)
        P.cbox("handbrake_shaft", (0.012, 0.012, 0.16), k.chrome, centre=(0, 0, 0.065), parent=h)
        P.cbox("handbrake_grip", (0.11, 0.026, 0.03), k.chrome, centre=(0, 0, -0.02), parent=h)
        P.cbox("handbrake_grip_rubber", (0.06, 0.03, 0.034), k.black, centre=(0, 0, -0.02), parent=h)


# ----------------------------------------------------------------- seats ----

def seats(k, L, cfg, pal, m):
    style = cfg.get("seats", "bucket")
    ey, ez = L.eye[1], L.eye[2]
    cushion = max(L.floor + 0.30, ey - cfg.get("seat_below_eye", 0.78))
    back_z = ez - cfg.get("back_behind_eye", 0.36)
    xs = (L.dx, -L.dx)
    if style == "bench":
        w = L.wall - 0.05
        P.box("bench_frame", (-w, L.floor, back_z), (w, cushion - 0.12, ez - 0.05), k.black)
        P.prism("bench_cushion", [(back_z - 0.02, cushion - 0.12), (back_z - 0.02, cushion), (ez + 0.02, cushion + 0.02),
                                  (ez + 0.07, cushion - 0.03), (ez + 0.05, cushion - 0.12)], "x", -w, w, pal["seat"])
        P.prism("bench_back", [(back_z - 0.10, cushion - 0.02), (back_z, cushion), (back_z - 0.06, cushion + 0.58),
                               (back_z - 0.16, cushion + 0.58), (back_z - 0.20, cushion)], "x", -w + 0.005, w - 0.005, pal["seat"])
        for i, x in enumerate((-w * 0.5, w * 0.5)):
            P.prism(f"bench_panel{i}", [(back_z + 0.002, cushion + 0.08), (back_z + 0.008, cushion + 0.08),
                                        (back_z - 0.04, cushion + 0.50), (back_z - 0.046, cushion + 0.50)],
                    "x", x - w * 0.35, x + w * 0.35, pal["seat2"])
        return
    for side, sx in zip(("driver", "passenger"), xs):
        P.box(f"seat_{side}_frame", (sx - 0.20, L.floor, back_z + 0.05), (sx + 0.20, cushion - 0.12, ez - 0.02), k.black)
        P.prism(f"seat_{side}_cushion", [(back_z + 0.02, cushion - 0.12), (back_z + 0.02, cushion), (ez + 0.02, cushion + 0.02),
                                         (ez + 0.08, cushion - 0.02), (ez + 0.06, cushion - 0.12)], "x", sx - 0.24, sx + 0.24, pal["seat"])
        P.prism(f"seat_{side}_back", [(back_z - 0.08, cushion - 0.02), (back_z + 0.02, cushion), (back_z - 0.04, cushion + 0.60),
                                      (back_z - 0.14, cushion + 0.60), (back_z - 0.18, cushion)], "x", sx - 0.235, sx + 0.235, pal["seat"])
        P.prism(f"seat_{side}_panel", [(back_z + 0.022, cushion + 0.10), (back_z + 0.028, cushion + 0.10),
                                       (back_z - 0.026, cushion + 0.52), (back_z - 0.032, cushion + 0.52)],
                "x", sx - 0.15, sx + 0.15, pal["seat2"])
        if style == "headrest":
            P.box(f"seat_{side}_headrest", (sx - 0.13, cushion + 0.64, back_z - 0.18), (sx + 0.13, cushion + 0.82, back_z - 0.06), pal["seat"])
            for j, px in enumerate((-0.07, 0.07)):
                P.box(f"seat_{side}_post{j}", (sx + px - 0.008, cushion + 0.58, back_z - 0.13), (sx + px + 0.008, cushion + 0.64, back_z - 0.11), k.chrome)
    if cfg.get("rear_bench", True) and L.eye[2] - m["rear"] > 1.3:
        w = L.wall - 0.06
        rz = back_z - 0.55
        P.prism("rear_bench_cushion", [(rz - 0.45, cushion - 0.14), (rz - 0.45, cushion - 0.04), (rz + 0.05, cushion - 0.02),
                                       (rz + 0.08, cushion - 0.14)], "x", -w, w, pal["seat"])
        P.prism("rear_bench_back", [(rz - 0.50, cushion - 0.06), (rz - 0.42, cushion - 0.04), (rz - 0.47, cushion + 0.48),
                                    (rz - 0.56, cushion + 0.48)], "x", -w, w, pal["seat"])
        P.box("rear_bench_frame", (-w, L.floor, rz - 0.42), (w, cushion - 0.14, rz + 0.04), k.black)


def doors(k, L, cfg, pal, m):
    """Door cards with handle, armrest and window winder on the front doors."""
    wins = m["windows"]
    door = max(wins, key=lambda w: w[1]) if wins else (L.eye[2] - 0.6, L.eye[2] + 0.5, m["belt"], m["win_top"])
    z0, z1 = door[0] + 0.05, min(door[1], L.face_z) - 0.02
    belt = m["belt"]
    for s in (-1, 1):
        side = "L" if s < 0 else "R"
        wall = k.wall(L.floor + 0.25, belt - 0.05, z0, z1, s) - 0.015
        c0, c1 = sorted((s * (wall - 0.02), s * wall))
        P.box(f"door_card_{side}", (c0, L.floor + 0.15, z0), (c1, belt - 0.12, z1), pal["plastic"] if cfg.get("door", "plastic") == "plastic" else pal["vinyl"])
        a0, a1 = sorted((s * (wall - 0.075), s * (wall - 0.02)))
        P.box(f"armrest_{side}", (a0, belt - 0.32, z0 + 0.10), (a1, belt - 0.28, (z0 + z1) / 2 + 0.05), pal["vinyl"])
        h0, h1 = sorted((s * (wall - 0.035), s * (wall - 0.02)))
        P.box(f"door_handle_{side}", (h0, belt - 0.22, z1 - 0.16), (h1, belt - 0.205, z1 - 0.06), k.chrome)
        crank = P.cylinder(f"window_crank_{side}", 0.012, 0.03, k.chrome, n=8)
        P.place(crank, (s * (wall - 0.02), belt - 0.40, (z0 + z1) / 2), Rz(90) @ P.Ry(90 * s))


def extras(k, L, cfg, pal, m):
    """Sun visors and the rear-view mirror at the top of the windscreen."""
    ws = L.ws
    for i, x in enumerate((L.dx, -L.dx)):
        v = P.cbox(f"sun_visor{i}", (0.38, 0.014, 0.16), pal["vinyl"])
        P.place(v, (x, ws["top_y"] - 0.03, ws["top_z"] - 0.12), Rx(-15))
    P.cbox("mirror_stem", (0.02, 0.06, 0.02), k.black, centre=(0, ws["top_y"] - 0.03, ws["top_z"] - 0.06))
    mirror = P.cbox("mirror", (0.22, 0.06, 0.025), k.black)
    P.place(mirror, (0.0, ws["top_y"] - 0.08, ws["top_z"] - 0.07), P.Ry(8 * L.side * -1))


def find_cab(k):
    """Middle of the front-most side window (the driver's door), seen from the car's centre line.
    Trucks and pickups have their cab far forward; a probe in the load bed would mistake the cab's
    rear window for the windscreen."""
    best = None
    z = 3.0
    while z > -3.0:
        for y in (1.3, 1.45, 1.6, 1.75, 1.9, 2.05):
            p, _, kind = k.sampler.hit((0.0, y, z), (-1, 0, 0))
            if kind == "glass" and p.x < -0.4:
                best = (z, y)
                break
        if best:
            break
        z -= 0.05
    return best


def build(k, cfg, assets):
    """The whole cockpit of one car."""
    pal = palette(cfg)
    cab = find_cab(k)
    probe = (0.4 * cfg.get("side", -1), cab[1] if cab else 1.4, (cab[0] - 0.35) if cab else -0.3)
    print("cab probe:", probe)
    m0 = k.measure(probe)
    ws = m0["ws"]
    eye_guess = (0.42 * cfg.get("side", -1), cfg.get("eye_y", min(ws["base_y"] + 0.27, m0["roof"] - 0.32)),
                 cfg.get("eye_z", max(ws["base_z"] - 0.85, m0["rear"] + 0.40)))
    m = k.measure(eye_guess)
    L = Layout(k, m, cfg)
    P.empty("eye", L.eye)
    k.auto_lining(m, pal["liner"], L.eye)
    k.body_bits(m)
    dash(k, L, cfg, pal)
    floor(k, L, cfg, pal, m)
    instruments(k, L, cfg, pal)
    controls(k, L, cfg, pal)
    seats(k, L, cfg, pal, m)
    if cfg.get("door_cards", True):
        doors(k, L, cfg, pal, m)
    extras(k, L, cfg, pal, m)
    return L
