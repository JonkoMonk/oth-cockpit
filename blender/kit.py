# Shared cockpit parts for the car scripts (build_<car>.py): dials, warning lamps, gear display,
# steering wheels, pedals, levers, wiper copies, body paint sampling and preview renders.
# Everything is in GAME coordinates (see parts.py). Parts that sit on an angled panel (an instrument
# pod) take a parent: an empty placed and rotated like the panel, the part in the panel's own space
# (x right, y up, -z = towards the driver).
import math
import os

import bpy
from mathutils import Matrix, Vector

import carref
import parts as P
from parts import Rx, Rz

def _components(cells):
    """Connected groups (4-neighbours) of grid cells."""
    cells = set(cells)
    out = []
    while cells:
        stack = [cells.pop()]
        comp = []
        while stack:
            c = stack.pop()
            comp.append(c)
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + d[0], c[1] + d[1])
                if n in cells:
                    cells.remove(n)
                    stack.append(n)
        out.append(comp)
    return out


LAMP_COLOURS = {"handbrake": (0.9, 0.06, 0.03), "engine": (0.9, 0.06, 0.03),
                "headlights": (0.10, 0.85, 0.20), "lowrange": (1.0, 0.55, 0.0)}
LAMP_CELLS = {"handbrake": 0, "headlights": 1, "lowrange": 2, "engine": 3}   # lamps.png


class Kit:
    """Materials and the real body for one car. Most methods take a parent (panel) or None (car space)."""

    def __init__(self, car, cars_folder):
        self.car = car
        self.body = carref.load_body(car, cars_folder)
        self.body.data.materials[0].use_backface_culling = True   # like in the game: from inside it's see-through
        self.sampler = carref.PaintSampler(self.body, cars_folder, car)
        self.paint = P.material("paint:body", (0.65, 0.58, 0.40), rough=0.6)
        self.black = P.material("lit:black", (0.010, 0.010, 0.011), rough=0.45)
        self.chrome = P.material("lit:chrome", (0.55, 0.55, 0.56), rough=0.25, metal=1.0)
        self.rubber = P.material("lit:rubber", (0.04, 0.04, 0.04), rough=0.95)
        self.needle = P.material("lit:needle", (1.0, 0.28, 0.02), rough=0.5)
        self.wiper = P.material("lit:wiper", (0.035, 0.035, 0.035), rough=0.6)

    # ---- paint ----
    def uv(self, label, origin, direction):
        """Paint spot of the outside panel a ray from inside hits: the part takes that panel's colour."""
        return self.sampler.at(label, origin, direction, getattr(self, "fallback_uv", P.PAINT_UV))

    # ---- instruments ----
    def panel(self, name, pos, rot=None):
        """An empty to put instruments on: its -z faces the driver."""
        return P.empty(name, pos, rot)

    def gauge(self, name, x, y, r, image, drive, a0, a1, full, zero=0.0, parent=None, z=0.0, bezel=None):
        """Dial face with chrome bezel and a needle pivot (empty) that the mod turns. Face plane at z."""
        bez = P.torus(name + "_bezel", r + 0.004, 0.006, bezel or self.chrome, n=32, m=6, parent=parent)
        P.place(bez, (x, y, z))
        face = P.disc(name + "_face", r, P.material("glow:" + name, image=image), n=40, parent=parent)
        P.place(face, (x, y, z - 0.002))
        face["backlight"] = 1
        piv = P.empty("needle_" + name, (x, y, z - 0.008), parent=parent,
                      drive=drive, axis="z", a0=a0, a1=a1, zero=zero, full=full)
        P.cbox(name + "_needle", (0.004 if r > 0.05 else 0.003, r * 0.9, 0.002), self.needle,
               centre=(0, r * 0.36, 0), parent=piv)
        cap = P.cylinder(name + "_cap", r * 0.1, 0.006, self.black, n=12, z0=-0.006, parent=piv)
        P.place(cap)
        return face

    def standard_gauges(self, cx, dial_y, top_y, parent=None, z=0.0, r=0.075, small=0.036, spread=0.085, outer=0.24):
        """Rev counter + speedometer side by side, fuel + temperature further out on the top row."""
        self.gauge("tacho", cx - spread, dial_y, r, "tacho.png", "rpm", 135, -135, 6000, parent=parent, z=z)
        self.gauge("speedo", cx + spread, dial_y, r, "speedo.png", "speed", 135, -135, 140, parent=parent, z=z)
        self.gauge("fuel", cx - outer, top_y, small, "fuel.png", "fuel", 45, -45, 1.0, parent=parent, z=z)
        self.gauge("temp", cx + outer, top_y, small, "temp.png", "temp", 45, -45, 40, zero=-20, parent=parent, z=z)

    def lamps(self, positions, y, parent=None, z=0.0, size=0.034):
        """positions: {lamp name: x}. Icons from lamps.png; the mod switches their glow."""
        for name, x in positions.items():
            cell = LAMP_CELLS[name]
            q = P.quad("lamp_" + name, size, size, P.material("glow:lamp_" + name, LAMP_COLOURS[name], image="lamps.png"),
                       uv_rect=(cell / 4, 0, (cell + 1) / 4, 1), parent=parent)
            P.place(q, (x, y, z - 0.002))
            q["lamp"] = name

    def gear_display(self, x, y, parent=None, z=0.0, size=0.05):
        P.box("gear_window", (x - size * 0.7, y - size * 0.6, z - 0.004), (x + size * 0.7, y + size * 0.6, z - 0.001),
              self.chrome, parent=parent)
        g = P.quad("gear_display", size, size, P.material("glow:gear", (1.0, 0.55, 0.05), image="gears.png"), parent=parent)
        P.place(g, (x, y, z - 0.005))
        g["display"] = "gear"
        g["cells"] = 8

    # ---- controls ----
    def steering_wheel(self, centre, tilt, radius=0.21, rim=0.013, spokes=(0, 180, 270), spoke_mat=None,
                       hub_r=0.05, column=0.42, rim_mat=None, spoke_w=0.022, horn_mat=None):
        """Wheel turning about its column; tilt = degrees from vertical (top leaning forward).
        spokes: angles in the wheel plane (0 = right, 90 = up)."""
        wheel = P.empty("steering_wheel", centre, Rx(tilt), drive="steer", axis="z", a0=270, a1=-270, zero=-1, full=1)
        P.torus("wheel_rim", radius, rim, rim_mat or self.black, n=56, m=10, parent=wheel)
        length = radius - hub_r * 0.6
        for i, a in enumerate(spokes):
            # Each spoke a hair deeper than the last, so where they meet under the hub they don't flicker.
            sp = P.cbox(f"wheel_spoke{i}", (length, spoke_w, 0.008), spoke_mat or self.chrome,
                        centre=(hub_r * 0.6 + length / 2, 0, 0.018 + 0.0015 * i), parent=wheel)
            P.place(sp, rot=Rz(a))
        hub = P.cylinder("wheel_hub", hub_r, 0.035, self.black, n=16, z0=0.0, parent=wheel)
        P.place(hub)
        horn = P.cylinder("wheel_horn", hub_r * 0.7, 0.006, horn_mat or self.chrome, n=16, z0=-0.004, parent=wheel)
        P.place(horn)
        col = P.cylinder("column", 0.032, column, self.black, n=12, z0=0.03, r1=0.04)
        P.place(col, centre, Rx(tilt))
        return wheel

    def pedal(self, name, pivot, drive, pad_w, arm=0.30):
        piv = P.empty("pedal_" + name, pivot, drive=drive, axis="x", a0=0, a1=-18, zero=0, full=1)
        P.cbox(name + "_arm", (0.018, arm, 0.018), self.chrome, centre=(0, -arm / 2, -0.02), parent=piv)
        # Tilted about its own centre (tilting about the pivot swung it ~16 cm forward, into the firewall).
        # A metal plate with the rubber on its face: all-black pads vanished against black floor mats.
        pad = P.cbox(name + "_pad", (pad_w, 0.075, 0.014), self.chrome, parent=piv)
        P.place(pad, (0, -arm, -0.035), Rx(-25))
        top = P.cbox(name + "_pad_rubber", (pad_w - 0.012, 0.063, 0.004), self.rubber, centre=(0, 0, -0.009), parent=pad)
        P.place(top)

    def lever(self, name, pivot, length, lean, knob_r, knob_mat, drive=None, a1=-22.0, boot=0.05, shaft_r=0.011,
              base_rot=None):
        """Floor lever: shaft from the pivot, leaning back by `lean` degrees, ball knob on top.
        drive: lowrange / handbrake / gear (gear: the mod moves it in an H pattern)."""
        extras = dict(drive=drive, axis="x", a0=0, a1=a1, zero=0, full=1) if drive else {}
        piv = P.empty(name, pivot, base_rot, **extras)
        P.prism(name + "_boot", [(-boot, 0.0), (-boot * 0.45, boot * 1.3), (boot * 0.45, boot * 1.3), (boot, 0.0)],
                "z", -boot, boot, self.rubber, parent=piv)
        shaft = P.cylinder(name + "_shaft", shaft_r, length, self.chrome, n=8, parent=piv)
        P.place(shaft, rot=Rx(-90 - lean))
        tip = (0, math.cos(math.radians(lean)) * length, -math.sin(math.radians(lean)) * length)
        knob = P.ball(name + "_knob", knob_r, knob_mat, parent=piv)
        P.place(knob, tip)
        return piv

    # ---- small parts the body only draws from outside ----
    def beam(self, name, a, b, w, h, mat, uv=None):
        """Box from point a to point b (car space), w wide, h thick."""
        a, b = Vector(a), Vector(b)
        d = b - a
        x = d.normalized()
        up = Vector((0, 0, 1)) if abs(x.z) < 0.9 else Vector((0, 1, 0))
        y = up.cross(x).normalized()
        z = x.cross(y)
        rot = Matrix((x, y, z)).transposed()
        ob = P.cbox(name, (d.length, w, h), mat, uv=uv)
        P.place(ob, tuple((a + b) / 2), rot)
        return ob

    # ---- automatic cabin: measure the real body, line it ----
    def measure(self, eye, side_x=None):
        """Measures the cabin around the eye with rays; the paint mask tells glass, paint and lights apart.
        Returns a dict (all game coordinates): floor, roof, rear, ws (windscreen: base_y, base_z, top_y,
        top_z, half_w), windows (side windows on the left: [(z0, z1, y0, y1)]), belt (lowest side glass),
        win_top, rear_glass ((x0, x1, y0, y1) or None), hood (top of the hood just ahead of the screen)."""
        S = self.sampler
        ex, ey, ez = eye
        m = {}
        p, _, _ = S.hit((0, ey - 0.3, ez), (0, -1, 0))
        m["floor"] = p.y if p else ey - 1.2
        p, _, _ = S.hit((0, ey, ez), (0, 1, 0))
        m["roof"] = p.y if p else ey + 0.4
        mid = (m["floor"] + m["roof"]) / 2
        p, _, _ = S.hit((0, mid, ez), (0, 0, -1))
        m["rear"] = p.z if p else ez - 1.5

        # Windscreen: forward rays up several lines across it; on each the longest run of glass. A box on
        # the hood or the bar of a split screen can interrupt one line, so combine them: lowest base, highest top.
        found = []
        for lx in (ex, ex * 0.5, 0.15, -ex * 0.5, -ex):
            runs, cur = [], []
            y = m["floor"] + 0.2
            while y < m["roof"]:
                p, _, kind = S.hit((lx, y, ez), (0, 0, 1))
                if kind == "glass" and p.z - ez < 1.5:   # far ahead is headlight glass, not the windscreen
                    cur.append((y, p.z))
                elif cur:
                    runs.append(cur)
                    cur = []
                y += 0.01
            if cur:
                runs.append(cur)
            # Wiper blades lie partly in front of the glass and cut a run in two: join runs with small gaps.
            joined = []
            for r in runs:
                if joined and r[0][0] - joined[-1][-1][0] < 0.09:
                    joined[-1] = joined[-1] + r
                else:
                    joined.append(r)
            if joined:
                found.append(max(joined, key=len))
        if found:
            # The longest run is the windscreen for sure; other lines count if they're at the same depth.
            anchor = max(found, key=len)
            az = sum(z for _, z in anchor) / len(anchor)
            same = [r for r in found if abs(sum(z for _, z in r) / len(r) - az) < 0.25]
            base = min((r[0] for r in same), key=lambda t: t[0])
            top = max((r[-1] for r in same), key=lambda t: t[0])
            ws = [base, top]
        else:
            ws = [(ey - 0.2, ez + 0.8), (ey + 0.2, ez + 0.7)]
        ymid = (ws[0][0] + ws[-1][0]) / 2
        # Outwards from the driver's line until the glass ends (split screens have a bar in the middle).
        half = 0.0
        x = abs(ex)
        while x < 1.3:
            _, _, kind = S.hit((-x, ymid, ez), (0, 0, 1))
            if kind != "glass":
                break
            half = x
            x += 0.01
        m["ws"] = dict(base_y=ws[0][0], base_z=ws[0][1], top_y=ws[-1][0], top_z=ws[-1][1], half_w=half)
        p, _, _ = S.hit((0, m["roof"] - 0.05, ws[0][1] + 0.15), (0, -1, 0))
        m["hood"] = p.y if p else ws[0][0] - 0.05

        # Side windows (left side; the bodies are symmetric): connected areas of glass on a z/y grid.
        # Small areas (side lights, glass-coloured details) don't count.
        step = 0.02
        zs = [m["rear"] + 0.02 + i * step for i in range(int((m["ws"]["base_z"] - 0.04 - m["rear"]) / step))]
        ys_ = [m["floor"] + 0.05 + i * step for i in range(int((m["roof"] - 0.06 - m["floor"]) / step))]
        cells = set()
        for i, z in enumerate(zs):
            for j, y in enumerate(ys_):
                _, _, kind = S.hit((-(side_x or 0.2), y, z), (-1, 0, 0))
                if kind == "glass":
                    cells.add((i, j))
        windows = []
        for comp in _components(cells):
            if len(comp) < 30:
                continue
            ii = [c[0] for c in comp]
            jj = [c[1] for c in comp]
            windows.append((zs[min(ii)], zs[max(ii)], ys_[min(jj)], ys_[max(jj)]))
        m["windows"] = sorted(windows)
        m["belt"] = min((w[2] for w in windows), default=ey - 0.35)
        m["win_top"] = max((w[3] for w in windows), default=ey + 0.2)

        # Rear window: the biggest area of glass right at the rear wall.
        wall_x = self.wall(mid - 0.2, mid + 0.2, m["rear"] + 0.1, m["rear"] + 0.4)
        xs_ = [-wall_x + 0.08 + i * 0.03 for i in range(int((2 * wall_x - 0.16) / 0.03) + 1)]
        ys2 = [m["floor"] + 0.1 + i * 0.03 for i in range(int((m["roof"] - m["floor"] - 0.1) / 0.03))]
        cells = set()
        for i, x in enumerate(xs_):
            for j, y in enumerate(ys2):
                p, _, kind = S.hit((x, y, m["rear"] + 0.3), (0, 0, -1), 1.0)
                if kind == "glass" and abs(p.z - m["rear"]) < 0.15:
                    cells.add((i, j))
        comps = [c for c in _components(cells) if len(c) >= 12]
        if comps:
            comp = max(comps, key=len)
            m["rear_glass"] = (xs_[min(c[0] for c in comp)], xs_[max(c[0] for c in comp)],
                               ys2[min(c[1] for c in comp)], ys2[max(c[1] for c in comp)])
        else:
            m["rear_glass"] = None
        # This car's own plain paint spot (lower front door), for parts whose own ray finds no paint.
        p, uv, kind = S.hit((-0.2, (m["floor"] + m["belt"]) / 2 + 0.1, ez), (-1, 0, 0))
        if kind == "paint":
            self.fallback_uv = uv
        print("measured:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items() if k != "ws"},
              {k: round(v, 3) for k, v in m["ws"].items()})
        return m

    def surface(self, name, us, vs, origin, direction, mat=None, inset=0.015, solid_kinds=("paint", "trim")):
        """A lining surface that follows the body: rays from origin(u, v) along direction on the grid us x vs.
        Every spot that isn't glass (or a light) gets covered, the window edges traced by bisection so they
        aren't stair-stepped. With mat=None the paint material is used and every corner takes the UV of
        its own outside spot, so the livery (stripes too) shows inside; faces across a seam of the paint
        layout take one UV. The faces look back towards the ray origins."""
        S = self.sampler
        d = Vector(direction).normalized()
        hits = {}
        for i, u in enumerate(us):
            for j, v in enumerate(vs):
                p, uv, kind = S.hit(origin(u, v), direction)
                hits[(i, j)] = (p, uv) if p is not None and kind in solid_kinds else None

        def edge_point(a, b):
            """Solid grid point a next to non-solid b: walk to the boundary between them."""
            (ia, ja), (ib, jb) = a, b
            ua, va, ub, vb = us[ia], vs[ja], us[ib], vs[jb]
            best = hits[a]
            lo, hi = 0.0, 1.0
            for _ in range(5):
                t = (lo + hi) / 2
                p, uv, kind = S.hit(origin(ua + (ub - ua) * t, va + (vb - va) * t), direction)
                if p is not None and kind in solid_kinds:
                    best, lo = (p, uv), t
                else:
                    hi = t
            return best

        verts, faces, uvs = [], [], []
        for i in range(len(us) - 1):
            for j in range(len(vs) - 1):
                corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                solid = [hits[c] is not None for c in corners]
                if sum(solid) < 2 or solid in ([True, False, True, False], [False, True, False, True]):
                    continue   # (two opposite corners only: glass runs between them)
                pts = []
                for k, c in enumerate(corners):
                    if solid[k]:
                        pts.append(hits[c])
                    else:
                        # Replace a missing corner by the boundary points towards its solid neighbours.
                        for nb in (corners[k - 1], corners[(k + 1) % 4]):
                            if hits[nb] is not None:
                                pts.append(edge_point(nb, c))
                if len(pts) < 3:
                    continue
                # Clean ring: drop repeats, keep order.
                ring = []
                for p in pts:
                    if not ring or (ring[-1][0] - p[0]).length > 1e-4:
                        ring.append(p)
                if len(ring) > 1 and (ring[0][0] - ring[-1][0]).length < 1e-4:
                    ring.pop()
                if len(ring) < 3:
                    continue
                spread = max((Vector(a[1]) - Vector(b[1])).length for a in ring for b in ring)
                if mat is None and spread > 0.04:
                    cu, cv = sum(us[c[0]] for c in corners) / 4, sum(vs[c[1]] for c in corners) / 4
                    _, cuv, _ = S.hit(origin(cu, cv), direction)
                    face_uvs = [cuv or ring[0][1]] * len(ring)
                else:
                    face_uvs = [r[1] for r in ring]
                base = len(verts)
                for (p, _), fuv in zip(ring, face_uvs):
                    verts.append(tuple(p - d * inset))
                    uvs.append(fuv)
                faces.append(tuple(range(base, base + len(ring))))
        if not faces:
            return None
        return P.mesh_object(name, verts, faces, mat or self.paint, uvs=uvs, closed=False, facing=tuple(-d))

    def auto_lining(self, m, liner, eye, front_z=None, side_from=0.25, step=0.04):
        """Lines the whole cabin from the measurements: both side walls (paint, livery-exact), the roof
        (headliner), the rear wall and the frame around the windscreen (A pillars, header)."""
        ws = m["ws"]
        front = front_z if front_z is not None else ws["base_z"] + 0.05
        floor, roof, rear = m["floor"] + 0.02, m["roof"], m["rear"]

        def rng(a, b, st):
            n = max(2, int(round((b - a) / st)) + 1)
            return [a + (b - a) * i / (n - 1) for i in range(n)]

        zs, ys = rng(rear + 0.01, front, step), rng(floor, roof - 0.01, step)
        for s in (-1, 1):
            self.surface(f"lining_side_{'L' if s < 0 else 'R'}", zs, ys,
                         lambda z, y, s=s: (s * side_from, y, z), (s, 0, 0))
        wall = self.wall(roof - 0.15, roof - 0.05, rear, front)
        # The headliner: everything above counts (a sunroof would be covered), and it stays a little
        # inside the walls so rays near them don't run into the tops of the side windows.
        xs = rng(-wall + 0.03, wall - 0.03, step)
        self.surface("lining_roof", xs, rng(rear + 0.01, ws["top_z"] + 0.05, step),
                     lambda x, z: (x, roof - 0.25, z), (0, 1, 0), mat=liner, inset=0.02,
                     solid_kinds=("paint", "trim", "light", "glass"))
        self.surface("lining_rear", rng(-wall - 0.05, wall + 0.05, step), [y for y in ys if y < roof - 0.12],
                     lambda x, y: (x, y, rear + 0.4), (0, 0, -1))
        # The windscreen frame: A pillars along the glass edges and a header bar above it. (A traced
        # surface along these narrow slanted strips comes out ragged; plain beams look clean.)
        for s in (-1, 1):
            side = "L" if s < 0 else "R"
            x = s * (ws["half_w"] + 0.05)
            self.beam(f"pillar_A_{side}", (x, ws["base_y"] - 0.02, ws["base_z"] - 0.03), (x, roof - 0.01, ws["top_z"] - 0.03),
                      0.10, 0.08, self.paint,
                      uv=self.uv(f"A pillar {side}", (x, (ws["base_y"] + ws["top_y"]) / 2, eye[2]), (0, 0, 1)))
        hw = self.wall(roof - 0.08, roof - 0.02, rear, front) - 0.01
        P.box("header", (-hw, ws["top_y"] - 0.01, ws["top_z"] - 0.10), (hw, roof - 0.004, ws["top_z"] + 0.02), self.paint,
              uv=self.uv("header", (0, ws["top_y"] - 0.05, eye[2]), (0, 0.6, 1)))

    def wall(self, y0, y1, z0, z1, s=-1):
        """Innermost |x| of the body's side wall over a region (s = -1 left, +1 right)."""
        best = 2.0
        for i in range(4):
            for j in range(4):
                y = y0 + (y1 - y0) * (i + 0.5) / 4
                z = z0 + (z1 - z0) * (j + 0.5) / 4
                p, _, _ = self.sampler.hit((0.0, y, z), (s, 0, 0))
                if p is not None:
                    best = min(best, abs(p.x))
        return best if best < 2.0 else 0.85

    # The cabin's cross-section: how far out the body's side is at each height, so the lining leans in
    # with the body (a straight wall at one width stuck out through bodies that lean in towards the roof,
    # and things mounted on the outside, like side jerrycans, showed inside). Measured once per side
    # along the front door (section_z) and used for every side panel, so they all line up.
    section_z = None
    half = 0.85

    def wall_x(self, y, s=-1):
        """Inner |x| of the body's side at height y (None where it's glass all along the door)."""
        key = (round(y, 3), s)
        cache = self.__dict__.setdefault("_wall_cache", {})
        if key in cache:
            return cache[key]
        z0, z1 = self.section_z
        xs = []
        for j in range(7):
            p, _, kind = self.sampler.hit((0.0, y, z0 + (z1 - z0) * (j + 0.5) / 7), (s, 0, 0))
            if p is not None and kind in ("paint", "trim") and abs(p.x) > 0.3:
                xs.append(abs(p.x))
        # The inner quarter: stays inside the skin, but one odd part inside the body doesn't decide it.
        x = sorted(xs)[len(xs) // 4] if len(xs) >= 2 else None
        if x is not None:
            x = min(max(x, self.half - 0.25), self.half + 0.10)
        cache[key] = x
        return x

    def wall_profile(self, y0, y1, s, step=0.05):
        """[(y, inner |x|)] from y0 to y1; heights with only glass are filled in along the line between the
        nearest measured ones (a pillar between windows leans like the door below and the roof above)."""
        n = max(2, int(math.ceil((y1 - y0) / step)) + 1)
        ys = [y0 + (y1 - y0) * i / (n - 1) for i in range(n)]
        # Look a little beyond the ends too, so a panel that is all window height still finds its lean.
        probe = [y0 - 0.25 + i * step for i in range(int((y1 - y0 + 0.5) / step) + 1)]
        known = [(y, self.wall_x(y, s)) for y in probe]
        known = [(y, x) for y, x in known if x is not None]
        if not known:
            return [(y, self.half) for y in ys]
        out = []
        for y in ys:
            below = [(yy, x) for yy, x in known if yy <= y]
            above = [(yy, x) for yy, x in known if yy >= y]
            if below and above:
                (ya, xa), (yb, xb) = below[-1], above[0]
                x = xa if yb == ya else xa + (xb - xa) * (y - ya) / (yb - ya)
            else:
                x = (below or above)[-1 if below else 0][1]
            out.append((y, x))
        return out

    @staticmethod
    def prof_x(prof, y):
        """Inner |x| of a wall profile at height y."""
        if y <= prof[0][0]:
            return prof[0][1]
        for (ya, xa), (yb, xb) in zip(prof, prof[1:]):
            if ya <= y <= yb:
                return xa + (xb - xa) * (y - ya) / max(yb - ya, 1e-9)
        return prof[-1][1]

    def side_panel(self, name, y0, y1, z0, z1, s, mat=None, thick=0.05):
        """Panel lining the side wall between y0..y1 and z0..z1, coloured like the outside there. With a
        measured cross-section (section_z) it leans with the body, 1.2 cm inside its skin."""
        uv = self.uv(name, (0, (y0 + y1) / 2, (z0 + z1) / 2), (s, 0, 0)) if mat is None else None
        if self.section_z is None:
            w = self.wall(y0, y1, z0, z1, s) - 0.012
            x0, x1 = sorted((s * w, s * (w + thick)))
            return P.box(name, (x0, y0, z0), (x1, y1, z1), mat or self.paint, uv=uv)
        prof = self.clear_glass(self.wall_profile(y0, y1, s), y0, y1, z0, z1, s)
        outline = [(s * (x - 0.012), y) for y, x in prof] + [(s * (x - 0.012 + thick), y) for y, x in reversed(prof)]
        return P.prism(name, outline, "z", z0, z1, mat or self.paint, uv=uv)

    def glass_x(self, y, z0, z1, s, face):
        """Most inboard |x| of the body's side glass at height y between z0 and z1 that lies within 3 cm in
        front of a panel face at |x| = face (glass further in is something else, like a windscreen corner).
        None: no such glass there."""
        xs = []
        for j in range(7):
            p, _, kind = self.sampler.hit((0.0, y, z0 + (z1 - z0) * (j + 0.5) / 7), (s, 0, 0))
            if p is not None and kind == "glass" and face - 0.03 < abs(p.x):
                xs.append(abs(p.x))
        return min(xs) if xs else None

    def clear_glass(self, prof, y0, y1, z0, z1, s):
        """The side windows reach a centimetre or two into the door (below the sill) and the roof edge, and
        the game draws the glass from inside too: where it stood in front of a panel it showed as a dark line
        along the door top. Within 4 cm of the panel's top and bottom edges, the face steps in to 6 mm inboard
        of any glass there (in 5 mm steps, so the step is a short chamfer), hiding the glass edge inside."""
        ys = sorted({round(y, 4) for y, _ in prof} |
                    {round(y, 4) for i in range(9) for y in (y1 - 0.005 * i, y0 + 0.005 * i) if y0 <= y <= y1})
        out, moved = [], 0
        for y in ys:
            x = self.prof_x(prof, y)
            if y > y1 - 0.045 or y < y0 + 0.045:
                g = self.glass_x(y, z0, z1, s, x - 0.012)
                if g is not None and x - 0.012 > g - 0.006:
                    x, moved = g + 0.006, moved + 1
            out.append((y, x))
        if moved:
            print(f"glass cleared: {moved} heights of a side panel step in past the window glass")
        return out

    def lining(self, m, liner, front_z=None, skip=()):
        """Doors and quarters below the windows, pillars between them, roof edges, header, A pillars,
        headliner and the rear wall with its window, from the measurements. front_z: where the side
        lining starts at the front (default: just behind the windscreen base)."""
        ws, wins = m["ws"], m["windows"]
        front = front_z if front_z is not None else ws["base_z"] - 0.02
        rear = m["rear"]
        floor, roof, belt, top = m["floor"], m["roof"], m["belt"], m["win_top"]
        for s in (-1, 1):
            side = "L" if s < 0 else "R"
            # Below the windows: front door and the rest.
            door = max(wins, key=lambda w: w[1]) if wins else (rear, front, belt, top)
            if "doors" not in skip:
                self.side_panel(f"door_{side}", floor, belt, door[0] - 0.04, front, s)
                if door[0] - 0.04 > rear + 0.02:
                    self.side_panel(f"quarter_{side}", floor, belt, rear, door[0] - 0.04, s)
            # Between the windows: pillars; behind the last one: the rear corner.
            edges = sorted(wins)
            gaps = [(edges[i][1], edges[i + 1][0]) for i in range(len(edges) - 1)]
            if edges:
                gaps.append((rear, edges[0][0]))
            for i, (z0, z1) in enumerate(gaps):
                if z1 - z0 > 0.02:
                    self.side_panel(f"pillar{i}_{side}", belt, top, z0, z1, s)
            # Above the windows up to the roof.
            if roof - top > 0.03:
                self.side_panel(f"roof_edge_{side}", top, roof, rear, front, s)
            # A pillar along the windscreen edge.
            if "a_pillars" not in skip:
                x = s * (ws["half_w"] + 0.045)
                self.beam(f"pillar_A_{side}", (x, ws["base_y"], ws["base_z"] - 0.04), (x, ws["top_y"], ws["top_z"] - 0.04),
                          0.09, 0.07, self.paint, uv=self.uv(f"A pillar {side}", (s * ws["half_w"] * 0.8, (ws["base_y"] + ws["top_y"]) / 2,
                                                                                    ws["base_z"] - 0.3), (s, 0, 1)))
        hw = self.wall(roof - 0.08, roof - 0.02, rear, front) - 0.02
        if self.section_z is not None:   # as wide as the body is up at the roof (it may lean in), its edges
            # tucked into the roof-edge panels (which start 1.2 cm inside the skin)
            hw = min(self.prof_x(self.wall_profile(roof - 0.08, roof - 0.02, s_), roof - 0.03) for s_ in (-1, 1)) + 0.005
        if "header" not in skip and roof - ws["top_y"] > 0.02:
            P.box("header", (-hw, ws["top_y"] - 0.01, ws["top_z"] - 0.12), (hw, roof, ws["top_z"] + 0.02), self.paint,
                  uv=self.uv("header", (0, ws["top_y"] - 0.05, ws["top_z"] - 0.3), (0, 0.6, 1)))
        if "headliner" not in skip:
            P.box("headliner", (-hw + 0.01, roof - 0.03, rear + 0.01), (hw - 0.01, roof - 0.005, ws["top_z"] - 0.13), liner)
        if "rear_wall" not in skip:
            rw = self.wall(floor + 0.1, roof - 0.1, rear + 0.05, rear + 0.2)
            uv = self.uv("rear wall", (0, (floor + roof) / 2, rear + 0.5), (0, 0, -1))
            z0, z1 = rear - 0.04, rear - 0.005
            g = m["rear_glass"]
            if g:
                gx0, gx1, gy0, gy1 = g[0] - 0.02, g[1] + 0.02, g[2] - 0.02, g[3] + 0.02
                P.box("rear_wall_low", (-rw, floor, z0), (rw, gy0, z1), self.paint, uv=uv)
                P.box("rear_wall_top", (-rw, gy1, z0), (rw, roof, z1), self.paint, uv=uv)
                P.box("rear_wall_L", (-rw, gy0, z0), (gx0, gy1, z1), self.paint, uv=uv)
                P.box("rear_wall_R", (gx1, gy0, z0), (rw, gy1, z1), self.paint, uv=uv)
            else:
                P.box("rear_wall", (-rw, floor, z0), (rw, roof, z1), self.paint, uv=uv)

    def body_bits(self, m):
        """Small body parts just outside the windscreen (wipers at the bottom or hanging from the top,
        boxes on the hood) are drawn by the game from outside only, so from the seat just their edges show.
        This copies their faces turned inwards, with the car's own paint layout: from inside they then look
        like the outside parts."""
        import bmesh
        ws = m["ws"]
        bm = bmesh.new()
        bm.from_mesh(self.body.data)
        uv_layer = bm.loops.layers.uv.active
        B2U = carref.U2B3.inverted()
        bm.verts.ensure_lookup_table()
        seen, islands = set(), []
        for v in bm.verts:
            if v.index in seen:
                continue
            stack, isl = [v], []
            seen.add(v.index)
            while stack:
                a = stack.pop()
                isl.append(a)
                for e in a.link_edges:
                    b = e.other_vert(a)
                    if b.index not in seen:
                        seen.add(b.index)
                        stack.append(b)
            islands.append(isl)

        def screen_z(y):
            t = (y - ws["base_y"]) / max(ws["top_y"] - ws["base_y"], 0.01)
            return ws["base_z"] + t * (ws["top_z"] - ws["base_z"])

        verts, faces, uvs = [], [], []
        parts = 0
        for isl in islands:
            if len(isl) > 60:
                continue
            pts = [B2U @ v.co for v in isl]
            c = sum(pts, Vector()) / len(pts)
            size = max((p - q).length for p in pts for q in pts)
            if size > 0.9 or not (ws["base_y"] - 0.15 < c.y < ws["top_y"] + 0.05 and abs(c.x) < ws["half_w"] + 0.05):
                continue
            if min(p.z - screen_z(p.y) for p in pts) < -0.02:   # all of it in front of the glass
                continue
            vset = set(v.index for v in isl)
            fs = {f for v in isl for f in v.link_faces if all(w.index in vset for w in f.verts)}
            for f in fs:
                base = len(verts)
                loops = list(f.loops)[::-1]   # reversed: facing inwards
                for lp in loops:
                    verts.append(tuple(B2U @ lp.vert.co))
                    uvs.append(tuple(lp[uv_layer].uv) if uv_layer else P.PAINT_UV)
                faces.append(tuple(range(base, base + len(loops))))
            parts += 1
        bm.free()
        if faces:
            # (Body -> game -> Blender coordinates is a round trip, so the reversed winding stays.)
            P.mesh_object("body_bits", verts, faces, self.paint, uvs=uvs, closed=False)
        print(f"body bits: {parts} small parts outside the windscreen copied facing inwards")

    def wiper_copies(self, m):
        """The game draws the wipers as single flat panels on the outside of the windscreen, seen from the
        front only: from the seat you look through them. This copies exactly those panels turned inwards,
        with the car's own paint layout, so from inside they look like the wipers outside. A wiper blade or
        arm is three long strips (12-75 cm, running across the screen, on the glass within a few cm either
        side of the measured screen line) plus small end caps and a pivot touching them; all of those are
        copied. Nothing else is (the old body_bits caught other small parts too and left floating shards)."""
        import bmesh
        ws = m["ws"]
        bm = bmesh.new()
        bm.from_mesh(self.body.data)
        uv_layer = bm.loops.layers.uv.active
        B2U = carref.U2B3.inverted()

        def screen_z(y):
            t = (y - ws["base_y"]) / max(ws["top_y"] - ws["base_y"], 0.01)
            return ws["base_z"] + t * (ws["top_z"] - ws["base_z"])

        # Separate pieces of the body (connected vertices); a wiper part is one flat panel: 3-8 corners.
        bm.verts.ensure_lookup_table()
        seen, pieces = set(), []
        for v in bm.verts:
            if v.index in seen:
                continue
            stack, isl = [v], []
            seen.add(v.index)
            while stack:
                a = stack.pop()
                isl.append(a)
                for e in a.link_edges:
                    o = e.other_vert(a)
                    if o.index not in seen:
                        seen.add(o.index)
                        stack.append(o)
            if 3 <= len(isl) <= 8:
                pieces.append(isl)
        boxes = []
        for isl in pieces:
            pts = [B2U @ v.co for v in isl]
            lo = Vector([min(p[i] for p in pts) for i in range(3)])
            hi = Vector([max(p[i] for p in pts) for i in range(3)])
            c = (lo + hi) / 2
            if not (ws["base_y"] - 0.10 < c.y < ws["top_y"] + 0.05 and abs(c.x) < ws["half_w"] + 0.08):
                continue
            # On the glass: the measured screen line is a few cm off here and there, so either side of it.
            if not (min(p.z - screen_z(p.y) for p in pts) > -0.06 and max(p.z - screen_z(p.y) for p in pts) < 0.10):
                continue
            boxes.append((isl, lo, hi))
        # The strips: long, and mostly across the screen (a window-frame edge or a split screen's bar stands
        # upright instead).
        size = lambda lo, hi: max(hi - lo)
        taken = [b for b in boxes if 0.12 < size(b[1], b[2]) < 0.75 and (b[2].x - b[1].x) >= 0.6 * size(b[1], b[2])]
        # Then the small pieces (end caps, pivots) touching a strip.
        near = lambda a, b: all(a[1][i] - 0.015 <= b[2][i] and b[1][i] - 0.015 <= a[2][i] for i in range(3))
        grew = True
        while grew:
            grew = False
            for b in boxes:
                if size(b[1], b[2]) <= 0.08 and not any(b is t for t in taken) and any(near(b, t) for t in taken):
                    taken.append(b)
                    grew = True
        verts, faces, uvs = [], [], []
        npieces = 0
        for isl, _, _ in taken:
            vset = {v.index for v in isl}
            for f in {f for v in isl for f in v.link_faces if all(w.index in vset for w in f.verts)}:
                base = len(verts)
                loops = list(f.loops)[::-1]   # reversed: facing inwards
                for lp in loops:
                    verts.append(tuple(B2U @ lp.vert.co))
                    uvs.append(tuple(lp[uv_layer].uv) if uv_layer else P.PAINT_UV)
                faces.append(tuple(range(base, base + len(loops))))
            npieces += 1
        bm.free()
        if faces:
            P.mesh_object("wiper_copies", verts, faces, self.paint, uvs=uvs, closed=False)
        print(f"wiper copies: {npieces} panels")
        return npieces

    def frame_covers(self, eye, min_x=0.5):
        """The body's dark window-frame edges (the rubber along the bottom and top of the side windows)
        face into the cabin; where they stick out past our lining they show as black strips along the door
        tops (and the painted door tops as stripes of another livery colour). Rays from the eye (and 2 cm
        above it) find every thin (< 6 cm) trim or paint strip of the body the game draws within 1.3 m at the
        sides (|x| > min_x) that isn't seen through glass; each gets a cover just in front of it, in the colour
        of the door beside it. Run after everything else is built (our parts hide the rest)."""
        from mathutils.bvhtree import BVHTree
        from mathutils.interpolate import poly_3d_calc
        dg = bpy.context.evaluated_depsgraph_get()
        verts, polys = [], []
        for ob in bpy.data.objects:
            if ob.type != "MESH" or ob == self.body:
                continue
            ev = ob.evaluated_get(dg)
            me = ev.to_mesh()
            base = len(verts)
            verts.extend(ob.matrix_world @ v.co for v in me.vertices)
            polys.extend([base + i for i in p.vertices] for p in me.polygons)
            ev.to_mesh_clear()
        ours = BVHTree.FromPolygons(verts, polys)
        S = self.sampler
        U2B3 = carref.U2B3

        def kind(index, loc):
            poly = S.me.polygons[index]
            w = poly_3d_calc([S.me.vertices[v].co for v in poly.vertices], loc)
            uv = (sum(a * S.uv[li].uv[0] for a, li in zip(w, poly.loop_indices)),
                  sum(a * S.uv[li].uv[1] for a, li in zip(w, poly.loop_indices)))
            r, g, b = S._px(S.mask, S.mask_px, uv)
            return "glass" if g > 0.5 else "light" if r > 0.5 else "paint" if b > 0.5 else "trim"

        found = set()
        for e in (Vector(eye), Vector(eye) + Vector((0, 0.02, 0))):
            o0 = U2B3 @ e
            for yaw in [a * 0.5 for a in range(-230, 231) if abs(a) >= 30]:
                for pitch in [a * 0.5 for a in range(-120, 81)]:
                    cp = math.cos(math.radians(pitch))
                    d = (U2B3 @ Vector((math.sin(math.radians(yaw)) * cp, math.sin(math.radians(pitch)),
                                        math.cos(math.radians(yaw)) * cp))).normalized()
                    o, glass = o0, False
                    for _ in range(20):
                        hb, ho = S.bvh.ray_cast(o, d, 10.0), ours.ray_cast(o, d, 10.0)
                        db = hb[3] if hb[0] is not None else 1e9
                        do = ho[3] if ho[0] is not None else 1e9
                        if db == 1e9 and do == 1e9:
                            break
                        if do <= db:
                            if ho[1].dot(d) < 0:
                                break       # one of our parts in front
                            o = ho[0] + d * 1e-4
                            continue
                        k_ = kind(hb[2], hb[0])
                        if hb[1].dot(d) < 0:   # a body face the game draws
                            if not glass and k_ in ("trim", "paint") and (hb[0] - o0).length < 1.3:
                                found.add(hb[2])
                            break
                        glass = glass or k_ == "glass"
                        o = hb[0] + d * 1e-4
        B2U = U2B3.inverted()
        verts, faces, uvs, side_uv = [], [], [], {}
        for pi in sorted(found):
            poly = S.me.polygons[pi]
            pts = [B2U @ S.me.vertices[v].co for v in poly.vertices]
            c = sum(pts, Vector()) / len(pts)
            longest = max((p - q).length for p in pts for q in pts)
            if abs(c.x) < min_x or 2 * poly.area / max(longest, 1e-6) > 0.06:   # only thin strips
                continue
            n = (B2U @ poly.normal).normalized()
            s = 1 if c.x > 0 else -1
            # One colour per side (covers overlap a little; two colours would flicker): the door skin
            # below the first one, else the car's fallback door colour.
            if s not in side_uv:
                side_uv[s] = self.uv(f"frame covers {'R' if s > 0 else 'L'}", (c.x - s * 0.15, c.y - 0.15, c.z), (s, 0, 0))
            uv = side_uv[s]
            base = len(verts)
            # 1.5 mm towards the eye (so from the seat it lines up with the face exactly) and every edge 4 mm
            # further out, so no sliver of the face peeks out past it from a moved head.
            e_ = Vector(eye)
            for i, p in enumerate(pts):
                a, b = pts[i - 1], pts[(i + 1) % len(pts)]
                outs = []
                for q0, q1 in ((a, p), (p, b)):
                    o = (q1 - q0).cross(n)
                    if o.length < 1e-9:
                        continue
                    o.normalize()
                    if o.dot((q0 + q1) / 2 - c) < 0:
                        o = -o
                    outs.append(o)
                shift = Vector()
                if outs:
                    mid = sum(outs, Vector())
                    if mid.length > 1e-6:
                        mid.normalize()
                        shift = mid * 0.004 / max(mid.dot(outs[0]), 0.3)   # mitred corner, capped at 1.3 cm
                verts.append(tuple(p + shift + (e_ - p).normalized() * 0.0015))
            uvs.extend([uv] * len(pts))
            faces.append(tuple(range(base, base + len(pts))))
        if faces:
            P.mesh_object("frame_covers", verts, faces, self.paint, uvs=uvs, closed=False)
        print(f"frame covers: {len(faces)} body trim faces covered")
        return len(faces)

    def wipers(self, blades, arms):
        """Closed copies of the body's wipers (which are single-sided and outside the glass).
        blades: [(lo, hi)] boxes; arms: [(pivot, tip)]."""
        for i, (lo, hi) in enumerate(blades):
            P.box(f"wiper_blade{i}", lo, hi, self.wiper)
        for i, (a, b) in enumerate(arms):
            self.beam(f"wiper_arm{i}", a, b, 0.014, 0.012, self.wiper)

    # ---- output ----
    def export(self, eye, assets, game_name=None):
        P.check_flicker(exclude=[self.body], eye=eye)
        P.export(os.path.join(assets, f"Car_{game_name or self.car}.glb"), exclude=[self.body])

    def previews(self, eye, assets, shots):
        """Renders from the driver's eye with the real body around it. shots: {name: (pos, rot, fov)}."""
        scene = bpy.context.scene
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 3.5
        sun.rotation_euler = (math.radians(35), math.radians(15), math.radians(-30))
        scene.collection.objects.link(sun)
        world = bpy.data.worlds.new("w")
        world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.65, 0.8, 1)
        scene.world = world
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x, scene.render.resolution_y = 1600, 900
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
        scene.collection.objects.link(cam)
        scene.camera = cam
        look_fwd = Matrix(((-1, 0, 0), (0, 0, -1), (0, -1, 0)))
        for name, (pos, rot, fov) in shots.items():
            cam.data.lens_unit = "FOV"
            cam.data.sensor_fit = "VERTICAL"     # like the game's field of view setting
            cam.data.angle = math.radians(fov)
            cam.data.clip_start = 0.02
            P.place(cam, pos or eye, rot @ look_fwd)
            folder = os.path.join(assets, "previews")
            os.makedirs(folder, exist_ok=True)
            bpy.ops.render.render()
            img = bpy.data.images["Render Result"]
            # A preview open in an image viewer can't be overwritten: then save next to it.
            for path in (os.path.join(folder, f"{self.car}_{name}.png"), os.path.join(folder, f"{self.car}_{name}_new.png")):
                try:
                    img.save_render(path)
                    print("wrote", path)
                    break
                except RuntimeError:
                    continue


def standard_shots(eye):
    return {
        "user": (eye, Rx(6), 85),
        "eye_down": (eye, Rx(30), 70),
        "eye_right": (eye, P.Ry(45) @ Rx(15), 70),
        "eye_left": (eye, P.Ry(-60) @ Rx(10), 70),
        "back": (eye, P.Ry(160) @ Rx(10), 70),
    }
