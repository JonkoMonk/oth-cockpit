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


def _hull2d(points):
    """Convex hull of 2D points, counter-clockwise, without (nearly) straight corners."""
    pts = sorted(set((round(x, 4), round(y, 4)) for x, y in points))
    if len(pts) < 3:
        return pts
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 1e-7:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 1e-7:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


LAMP_COLOURS = {"handbrake": (0.9, 0.06, 0.03), "engine": (0.9, 0.06, 0.03),
                "headlights": (0.10, 0.85, 0.20), "lowrange": (1.0, 0.55, 0.0)}
LAMP_CELLS = {"handbrake": 0, "headlights": 1, "lowrange": 2, "engine": 3}   # lamps.png


class Kit:
    """Materials and the real body for one car. Most methods take a parent (panel) or None (car space)."""

    def __init__(self, car, cars_folder):
        self.car = car
        self.folder = cars_folder
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
        if kind == "paint" and S.shade(uv) >= S.AO_MIN:
            self.fallback_uv = uv
        print("measured:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items() if k != "ws"},
              {k: round(v, 3) for k, v in m["ws"].items()})
        return m

    def surface(self, name, us, vs, origin, direction, mat=None, inset=0.015, solid_kinds=("paint", "trim"), one_uv=None,
                tags=None):
        """A lining surface that follows the body: rays from origin(u, v) along direction on the grid us x vs.
        Every spot that isn't glass (or a light) gets covered, the window edges traced by bisection so they
        aren't stair-stepped. With mat=None the paint material is used and every corner takes the UV of
        its own outside spot, so the livery (stripes too) shows inside; faces across a seam of the paint
        layout take one UV. The faces look back towards the ray origins. tags (a list): filled with one word per
        vertex, "glass" for a point on a window's edge, else "free" (tuck_rear_wall may move those)."""
        S = self.sampler
        d = Vector(direction).normalized()
        hits, kinds = {}, {}
        for i, u in enumerate(us):
            for j, v in enumerate(vs):
                p, uv, kind = S.hit(origin(u, v), direction)
                hits[(i, j)] = (p, uv) if p is not None and kind in solid_kinds else None
                kinds[(i, j)] = kind

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
        shaded = 0
        for i in range(len(us) - 1):
            for j in range(len(vs) - 1):
                corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                solid = [hits[c] is not None for c in corners]
                if sum(solid) < 2 or solid in ([True, False, True, False], [False, True, False, True]):
                    continue   # (two opposite corners only: glass runs between them)
                pts = []
                for k, c in enumerate(corners):
                    if solid[k]:
                        pts.append(hits[c] + ("free",))
                    else:
                        # Replace a missing corner by the boundary points towards its solid neighbours.
                        for nb in (corners[k - 1], corners[(k + 1) % 4]):
                            if hits[nb] is not None:
                                pts.append(edge_point(nb, c) + ("glass" if kinds[c] == "glass" else "free",))
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
                if mat is None and any(S.shade(r[1]) < S.AO_MIN for r in ring):
                    # a spot the car's baked shading makes dark (in game it would be nearly black): plain body colour
                    face_uvs = [getattr(self, "fallback_uv", P.PAINT_UV)] * len(ring)
                    shaded += 1
                elif mat is None and spread > 0.04:
                    cu, cv = sum(us[c[0]] for c in corners) / 4, sum(vs[c[1]] for c in corners) / 4
                    _, cuv, _ = S.hit(origin(cu, cv), direction)
                    face_uvs = [cuv or ring[0][1]] * len(ring)
                else:
                    face_uvs = [r[1] for r in ring]
                base = len(verts)
                for (p, _, tg), fuv in zip(ring, face_uvs):
                    verts.append(tuple(p - d * inset))
                    uvs.append(fuv)
                    if tags is not None:
                        tags.append(tg)
                faces.append(tuple(range(base, base + len(ring))))
        if not faces:
            return None
        if one_uv is not None:   # one colour all over (the rear wall: the side panels' colour)
            uvs = [one_uv] * len(uvs)
        elif shaded > 0.2 * len(faces):   # mostly shaded: all of it one colour (mixed, it read as a patchwork)
            uvs = [getattr(self, "fallback_uv", P.PAINT_UV)] * len(uvs)
            print(f"{name}: {shaded} of {len(faces)} faces over shaded body spots: all in the plain body colour")
        elif shaded:
            print(f"{name}: {shaded} of {len(faces)} faces over shaded body spots take the plain body colour")
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
    # Per car (cfg fit_sides): side panels bent to the body along their length + a headliner that follows the
    # roof (fitted_panel, headliner). v2 cars: on by default since 0.4.3 (styles_v2), off for the 5 cars where
    # the renders looked worse (cars_v2). The "new flicker" it seemed to cause was a false alarm of the check.
    fit_sides = False
    # The roof lining alone (headliner following the roof, roof edges 1.5 cm short of it); None = same as fit_sides.
    # Rust Ox 0.4.4: fitted roof but straight side panels (bent ones stepped through its cab's door cards).
    fit_roof = None
    # 0.4.5: rear wall traced along the body with every window open (False: the old flat board, one window).
    rear_traced = True
    roof_edge_short = True

    def roof_fitted(self):
        return self.fit_sides if self.fit_roof is None else self.fit_roof

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
        if self.fit_sides:
            return self.fitted_panel(name, prof, z0, z1, s, mat or self.paint, uv, thick)
        outline = [(s * (x - 0.012), y) for y, x in prof] + [(s * (x - 0.012 + thick), y) for y, x in reversed(prof)]
        return P.prism(name, outline, "z", z0, z1, mat or self.paint, uv=uv)

    def facing_hit(self, origin, direction, axis, max_dist=10.0, least=0.4):
        """(game point, kind) where a ray hits the body, only if the surface there faces along `axis` (0 = x for
        a side wall, 1 = y for the roof) by at least `least`; else (None, None). A ray along the side at a
        panel's end otherwise hit the back wall of a cab (Blast Wagon) and bent the panel away from the corner."""
        p, _, kind = self.sampler.hit(origin, direction, max_dist)
        if p is None:
            return None, None
        o, d = carref.U2B3 @ Vector(origin), (carref.U2B3 @ Vector(direction)).normalized()
        _, n, _, _ = self.sampler.bvh.ray_cast(o, d, max_dist)
        if n is None or abs((carref.U2B3.inverted() @ n).normalized()[axis]) < least:
            return None, None
        return p, kind

    def headliner(self, hw, roof, z0, z1, liner, nx=14, step=0.06):
        """The roof lining, following the roof down where it curves at the edges and the rear corners (a flat
        board 3 cm under the highest point poked through there, and the game's paint showed in the corners:
        Polyana review 2026-11-08). Face 1.2 cm under the roof, never more than 3 cm above the old board."""
        nz = max(2, int(math.ceil((z1 - z0) / step)) + 1)
        xs = [-hw + 0.01 + (2 * hw - 0.02) * i / (nx - 1) for i in range(nx)]
        zs = [z0 + (z1 - z0) * j / (nz - 1) for j in range(nz)]
        face = []
        for z in zs:
            row = []
            for x in xs:
                y = roof - 0.03
                p, kind = self.facing_hit((x, roof - 0.30, z), (0, 1, 0), 1, 0.40)
                if p is not None and kind != "light" and roof - 0.30 < p.y - 0.012 < y:
                    y = p.y - 0.012
                row.append(y)
            face.append(row)
        verts = [(x, face[j][i], z) for j, z in enumerate(zs) for i, x in enumerate(xs)]
        off = len(verts)
        verts += [(x, face[j][i] + 0.025, z) for j, z in enumerate(zs) for i, x in enumerate(xs)]

        def v(j, i, top=0):
            return top * off + j * nx + i
        faces = []
        for j in range(nz - 1):
            for i in range(nx - 1):
                faces.append((v(j, i), v(j + 1, i), v(j + 1, i + 1), v(j, i + 1)))
                faces.append((v(j, i, 1), v(j, i + 1, 1), v(j + 1, i + 1, 1), v(j + 1, i, 1)))
        for j in range(nz - 1):
            faces.append((v(j, 0), v(j, 0, 1), v(j + 1, 0, 1), v(j + 1, 0)))
            faces.append((v(j, nx - 1), v(j + 1, nx - 1), v(j + 1, nx - 1, 1), v(j, nx - 1, 1)))
        for i in range(nx - 1):
            faces.append((v(0, i), v(0, i + 1), v(0, i + 1, 1), v(0, i, 1)))
            faces.append((v(nz - 1, i), v(nz - 1, i, 1), v(nz - 1, i + 1, 1), v(nz - 1, i + 1)))
        dropped = max(roof - 0.03 - y for row in face for y in row)
        if dropped > 0.005:
            print(f"headliner: follows the roof down up to {dropped * 100:.1f} cm at its edges")
        return P.mesh_object("headliner", verts, faces, liner)

    def fitted_panel(self, name, prof, z0, z1, s, mat, uv, thick, step=0.03):
        """A side panel bent to the body along its length. The cross-section comes from the front door, but
        behind it the body can be narrower: the Polyana's rear side lining stood 3-8 cm out through the body at
        the sill, and at the rounded rear corner (C pillar, roof edge) up to 19 cm; from inside, the game's own
        paint showed through there (review 2026-11-08). At each station along z the face moves in to the body
        where it's closer than the door's cross-section (by up to 30 cm above the lowest 25 cm, 10 cm lower
        down: further in there is a wheel arch or a seat box, not the side)."""
        n = max(2, int(math.ceil((z1 - z0) / step)) + 1)
        zs = [z0 + (z1 - z0) * j / (n - 1) for j in range(n)]
        floor_y = prof[0][0]
        grid, moved = [], 0.0
        for z in zs:
            col = []
            for y, x in prof:
                reach = 0.10 if y < floor_y + 0.25 else 0.30
                best = x
                for dz in (-0.02, 0.0, 0.02):
                    zz = min(max(z + dz, z0 + 0.005), z1 - 0.005)
                    p, kind = self.facing_hit((0.0, y, zz), (s, 0, 0), 0)
                    if p is not None and kind != "light" and x - reach < abs(p.x) < best:
                        best = abs(p.x)
                moved = max(moved, x - best)
                col.append(best)
            grid.append(col)
        if moved > 0.005:
            print(f"side fit: {name} bent in up to {moved * 100:.1f} cm (body narrower there than at the door)")
        ny = len(prof)
        verts = []
        for j, z in enumerate(zs):
            for i, (y, _) in enumerate(prof):
                verts.append((s * (grid[j][i] - 0.012), y, z))
        off = len(verts)
        for j, z in enumerate(zs):
            for i, (y, _) in enumerate(prof):
                verts.append((s * (grid[j][i] - 0.012 + thick), y, z))

        def v(j, i, outer=0):
            return outer * off + j * ny + i
        faces = []
        for j in range(n - 1):
            for i in range(ny - 1):
                faces.append((v(j, i), v(j, i + 1), v(j + 1, i + 1), v(j + 1, i)))
                faces.append((v(j, i, 1), v(j + 1, i, 1), v(j + 1, i + 1, 1), v(j, i + 1, 1)))
        for j in range(n - 1):   # bottom and top edges
            faces.append((v(j, 0), v(j + 1, 0), v(j + 1, 0, 1), v(j, 0, 1)))
            faces.append((v(j, ny - 1), v(j, ny - 1, 1), v(j + 1, ny - 1, 1), v(j + 1, ny - 1)))
        for i in range(ny - 1):  # front and rear ends
            faces.append((v(0, i), v(0, i, 1), v(0, i + 1, 1), v(0, i + 1)))
            faces.append((v(n - 1, i), v(n - 1, i + 1), v(n - 1, i + 1, 1), v(n - 1, i, 1)))
        return P.mesh_object(name, verts, faces, mat, uv=uv)

    def pillar_panel(self, name, y0, y1, z0, z1, s, depth=0.025, thick=0.05):
        """Lining of a pillar between two side windows. A flat panel 1.2 cm inside the skin (side_panel) read as a
        plain slab standing in front of the window when the pillar is right beside the driver's head (review
        2026-11-07: DingDing, Trail Burner, Burro). Now a moulded trim: its face comes `depth` into the cabin,
        narrower than the pillar, with slanted sides back to the window edges, easing out to flat over the top and
        bottom 6 cm (where the roof edge and the door meet it). Wide panels (a rear corner) stay flat."""
        self.pillars = getattr(self, "pillars", [])
        z0, z1 = sorted((z0, z1))
        if self.section_z is None or z1 - z0 > 0.35:
            ob = self.side_panel(name, y0, y1, z0, z1, s, thick=thick)
            self.pillars.append(dict(name=name, s=s, y0=y0, y1=y1, z0=z0, z1=z1, prof=None, depth=0.0, chamfer=0.0))
            return ob
        uv = self.uv(name, (0, (y0 + y1) / 2, (z0 + z1) / 2), (s, 0, 0))
        prof = self.clear_glass(self.wall_profile(y0, y1, s), y0, y1, z0, z1, s)
        w = z1 - z0
        c = min(0.035, 0.28 * w)                 # how far the slanted sides reach in from each window edge
        d = min(depth, 0.22 * w)

        def ease(y):   # small at the ends (never 0: no zero-size faces), 1 from 6 cm in
            t = min(y - y0, y1 - y) / 0.06
            t = max(0.0, min(1.0, t))
            return max(0.12, t * t * (3 - 2 * t))

        verts, rows = [], []
        for y, x in prof:
            face = x - 0.012                      # |x| of the flat lining face
            dd = d * ease(y)
            cc = c * ease(y)
            row = [(s * face, y, z0), (s * (face - dd), y, z0 + cc), (s * (face - dd), y, z1 - cc), (s * face, y, z1),
                   (s * (face + thick), y, z1), (s * (face + thick), y, z0)]
            rows.append(len(verts))
            verts += row
        faces = []
        for a, b in zip(rows, rows[1:]):
            for k in range(6):
                faces.append((a + k, a + (k + 1) % 6, b + (k + 1) % 6, b + k))
        faces.append(tuple(rows[0] + k for k in range(6)))
        faces.append(tuple(rows[-1] + k for k in reversed(range(6))))
        ob = P.mesh_object(name, verts, faces, self.paint, uv=uv)
        self.pillars.append(dict(name=name, s=s, y0=y0, y1=y1, z0=z0, z1=z1, prof=prof, depth=d, chamfer=c))
        return ob

    def seat_belt(self, eye):
        """The driver's seat belt hanging down the pillar beside the head (the B pillar): a dark strap from a
        metal anchor at shoulder height down into the door, with the buckle tongue on it. It breaks up the big
        plain pillar face right next to the driver. Returns the pillar's name or None."""
        pillars = [p for p in getattr(self, "pillars", []) if p["prof"] is not None and p["s"] * eye[0] > 0]
        # The pillar level with or just behind the eye.
        near = [p for p in pillars if p["z0"] - 0.15 < eye[2] and (p["z0"] + p["z1"]) / 2 > eye[2] - 0.6]
        if not near:
            print("seat belt: no pillar beside the driver")
            return None
        p = min(near, key=lambda q: abs((q["z0"] + q["z1"]) / 2 - (eye[2] - 0.15)))
        s, z0, z1, d, c = p["s"], p["z0"], p["z1"], p["depth"], p["chamfer"]
        strap_w = 0.046
        if (z1 - z0) - 2 * c < strap_w + 0.01:
            print(f"seat belt: {p['name']} too narrow")
            return None
        zc = (z0 + z1) / 2
        top = min(p["y1"] - 0.08, eye[1] - 0.02)
        bottom = p["y0"] + 0.005
        if top - bottom < 0.15:
            print(f"seat belt: {p['name']} too short")
            return None

        def face_x(y):   # |x| of the pillar's cabin face at height y (with its moulding)
            t = max(0.0, min(1.0, min(y - p["y0"], p["y1"] - y) / 0.06))
            return self.prof_x(p["prof"], y) - 0.012 - d * max(0.12, t * t * (3 - 2 * t))

        belt = P.material("lit:seat_belt", (0.055, 0.055, 0.06), rough=0.95)
        metal = P.material("lit:belt_metal", (0.50, 0.50, 0.52), rough=0.35, metal=0.8)
        n = 8
        ys = [bottom + (top - bottom) * i / (n - 1) for i in range(n)]
        outline = [(s * (face_x(y) - 0.002), y) for y in ys] + [(s * (face_x(y) - 0.005), y) for y in reversed(ys)]
        P.prism("seat_belt", outline, "z", zc - strap_w / 2, zc + strap_w / 2, belt)
        # Anchor plate with its bolt at the top, buckle tongue a third of the way down.
        ya = top + 0.005
        xa = face_x(ya)
        P.prism("seat_belt_anchor", [(s * (xa - 0.002), ya - 0.03), (s * (xa - 0.002), ya + 0.025), (s * (xa - 0.009), ya + 0.025),
                                     (s * (xa - 0.009), ya - 0.03)], "z", zc - 0.031, zc + 0.031, metal)
        P.place(P.cylinder("seat_belt_bolt", 0.009, 0.006, self.black, n=10), (s * (xa - 0.012), ya + 0.004, zc),
                P.Ry(90 * s))
        yt = top - (top - bottom) * 0.38
        xt = face_x(yt)
        P.box("seat_belt_tongue", (min(s * (xt - 0.005), s * (xt - 0.012)), yt - 0.045, zc - 0.018),
              (max(s * (xt - 0.005), s * (xt - 0.012)), yt + 0.01, zc + 0.018), metal)
        print(f"seat belt: on {p['name']} ({(z1 - z0) * 100:.0f} cm wide, strap {top - bottom:.2f} m)")
        return p["name"]

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
                    self.pillar_panel(f"pillar{i}_{side}", belt, top, z0, z1, s)
            # Above the windows up to the roof.
            if roof - top > 0.03:
                # Bent to the body (fitted_panel), its top edge would lie on a curved roof's inside, on the
                # copy inner_skins puts there (flicker): stop 1.5 cm short, the headliner follows the roof down.
                # 0.4.5: its front ends at the windscreen's top edge. Up there the A pillar leans far back, and run
                # on to the door window's front the panel stuck out past the pillar into the windscreen's corner:
                # a slab across it (Roamer) or slivers beside the pillar trim (Woodman, Trail Burner, drive 22 Nov).
                re_front = min(front, ws["top_z"] - 0.03) if self.roof_edge_short else front
                # (where the windscreen wraps round, its corner up there is further back still: the glass there; the
                # panel's lower front corner sits out at the side wall, beside the pillar, so 6.5 cm behind the glass)
                # cfg roof_edge_short=False: as in 0.4.4 (on the Bull its pillar trim ends low and the panel covered
                # the rest of the pillar: "the right A pillar goes halfway", drive 25 Nov)
                for yy in ((top + 0.02, (top + roof) / 2) if self.roof_edge_short else ()):
                    p_, _, kind_ = self.sampler.hit((s * (ws["half_w"] - 0.03), yy, ws["top_z"] - 0.6), (0, 0, 1), 1.2)
                    if p_ is not None and kind_ == "glass":
                        re_front = min(re_front, p_.z - 0.065)
                self.side_panel(f"roof_edge_{side}", top, roof - (0.015 if self.roof_fitted() else 0.0),
                                rear, re_front, s)
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
            # Its front follows the windscreen glass (6 mm behind it): the glass runs on up past the measured
            # top, and the game draws it from inside too, so it showed in front of a plain box.
            y0, zb, zf = ws["top_y"] - 0.01, ws["top_z"] - 0.12, ws["top_z"] + 0.02
            n = max(2, int(round((roof - y0) / 0.01)) + 1)
            front = []
            for i in range(n):
                y = y0 + (roof - y0) * i / (n - 1)
                z = zf
                for x in (0.0, -0.3 * hw, 0.3 * hw, -0.6 * hw, 0.6 * hw, -0.85 * hw, 0.85 * hw, -0.97 * hw, 0.97 * hw):
                    p, _, kind = self.sampler.hit((x, y, ws["top_z"] - 0.25), (0, 0, 1), 0.45)
                    if p is not None and kind == "glass":
                        z = min(z, p.z - 0.006)
                front.append((max(z, zb + 0.02), y))
            moved = sum(1 for z, _ in front if z < zf)
            prof = [(zb, y0), (zb, roof)] + front[::-1]
            P.prism("header", prof, "x", -hw, hw, self.paint,
                    uv=self.uv("header", (0, ws["top_y"] - 0.05, ws["top_z"] - 0.3), (0, 0.6, 1)))
            if moved:
                print(f"header: front steps back behind the windscreen glass at {moved} of {n} heights")
        if "headliner" not in skip:
            if not self.roof_fitted():
                P.box("headliner", (-hw + 0.01, roof - 0.03, rear + 0.01), (hw - 0.01, roof - 0.005, ws["top_z"] - 0.13), liner)
            else:
                self.headliner(hw, roof, rear + 0.01, ws["top_z"] - 0.13, liner)
        if "rear_wall" not in skip and self.rear_traced:
            # 0.4.5: the rear wall follows the body (rays back from inside the cabin) and stays open wherever the
            # body is glass, so every rear and rear-door window stays a window. The flat board below had room for
            # one window only (the biggest), and a leaning tailgate's glass was missed: "can't see out the back"
            # on the Grand Woodman, Woodman, Boar, Marshal and Timberbox (all-cars drive 22 Nov).
            rw = self.wall(floor + 0.1, roof - 0.1, rear + 0.05, rear + 0.2)

            def rng(a, b, st):
                n = max(2, int(round((b - a) / st)) + 1)
                return [a + (b - a) * i / (n - 1) for i in range(n)]
            S = self.sampler

            # Rays start up to 90 cm in front of the back (0.45 left the corners under a sloping roof open: Boar), but
            # never ahead of the front door window's back edge (a short pickup cab: Cumbre).
            door_ = max(m["windows"], key=lambda w: w[1]) if m["windows"] else (rear + 0.5,)
            reach_ = min(0.90, max(0.45, door_[0] - rear - 0.05))

            def origin(x, y):
                return (x, y, rear + reach_)
            # Only the body's back counts (a ray that meets a side wall or the roof first is left open: the side
            # lining and headliner cover those).
            orig_hit = S.hit

            def back_hit(o, d, max_dist=10.0):
                p, uv, kind = orig_hit(o, d, max_dist)
                if p is not None:
                    _, n_, _, _ = S.bvh.ray_cast(carref.U2B3 @ Vector(o), (carref.U2B3 @ Vector(d)).normalized(), max_dist)
                    ng_ = (carref.U2B3.inverted() @ n_).normalized() if n_ is not None else None
                    if ng_ is not None and abs(ng_[2]) < 0.3:
                        return None, None, None   # a flat roof or floor (the headliner is there: it flickered, DingDing)
                if p is not None and p.z > rear + reach_ - 0.05:
                    return None, None, None
                return p, uv, kind
            # 0.4.5b2: one colour, the rear side panels' (the body's back is often another livery colour, or the
            # light unpainted part of the paint layout: a beige "trunk panel" in 8 cars, drive 25 Nov).
            wall_uv = self.rear_wall_uv(m)
            S.hit = back_hit
            try:
                # (tail lights count as wall: left open, you saw out through them, Timberbox "I can see out of the trunk")
                tags = []
                ob = self.surface("rear_wall", rng(-rw + 0.005, rw - 0.005, 0.03), rng(floor + 0.01, roof - 0.02, 0.03),
                                  origin, (0, 0, -1), mat=self.rear_wall_mat(), inset=0.018, one_uv=wall_uv,
                                  solid_kinds=("paint", "trim", "light"), tags=tags)   # (1.2 cm lay on the headliner under a sloping roof: Boar)
            finally:
                S.hit = orig_hit
            if ob is not None and self.rear_tuck:
                self.tuck_rear_wall(ob, tags, rear)
            print(f"rear wall: traced along the body's back ({len(ob.data.polygons) if ob else 0} faces), windows left open")
        elif "rear_wall" not in skip:
            rw = self.wall(floor + 0.1, roof - 0.1, rear + 0.05, rear + 0.2)
            uv = self.rear_wall_uv(m)   # 0.4.5b2: the side panels' colour (was the body's back: beige, Blast Wagon)
            wm = self.rear_wall_mat()
            z0, z1 = rear - 0.04, rear - 0.005
            g = m["rear_glass"]
            if g:
                gx0, gx1, gy0, gy1 = g[0] - 0.02, g[1] + 0.02, g[2] - 0.02, g[3] + 0.02
                P.box("rear_wall_low", (-rw, floor, z0), (rw, gy0, z1), wm, uv=uv)
                P.box("rear_wall_top", (-rw, gy1, z0), (rw, roof, z1), wm, uv=uv)
                P.box("rear_wall_L", (-rw, gy0, z0), (gx0, gy1, z1), wm, uv=uv)
                P.box("rear_wall_R", (gx1, gy0, z0), (rw, gy1, z1), wm, uv=uv)
            else:
                P.box("rear_wall", (-rw, floor, z0), (rw, roof, z1), wm, uv=uv)

    # 0.4.5b3: the traced rear wall's edges tucked in behind the side lining (tuck_rear_wall); cfg rear_tuck=False: off.
    rear_tuck = True

    def window_edge_strips(self, rear, reach=0.12, step=0.02):
        """0.4.5b3: the rear corner pillar's lining ends at the side window's measured box, but the glass starts a
        little further on (a rounded window corner most of all). That strip of window frame was only covered by the
        rear wall's edge sticking out into the cabin. Now a thin strip lies flat on the frame (6 mm off the body,
        under the pillar lining where they overlap) from under the pillar's end up to the glass, so the wall's edge
        can tuck in behind it (tuck_rear_wall) without opening the frame."""
        S = self.sampler
        made = 0
        for p in getattr(self, "pillars", []):
            if abs(p["z0"] - rear) > 0.02:
                continue   # only the rearmost pillar on each side (from the back to the first side window)
            src = bpy.data.objects.get(p["name"])
            if src is None:
                continue
            s, z1 = p["s"], p["z1"]
            n = max(2, int(math.ceil((p["y1"] - p["y0"]) / step)) + 1)
            rows = []
            for i in range(n):
                y = p["y0"] + (p["y1"] - p["y0"]) * i / (n - 1)
                hit_at = lambda z: S.hit((s * 0.25, y, z), (s, 0, 0))
                zg = None
                z = z1 - 0.01
                while z < z1 + reach:
                    pb, _, kd = hit_at(z)
                    if pb is not None and kd == "glass":
                        lo, hi = z - 0.005, z
                        for _ in range(5):
                            mid = (lo + hi) / 2
                            pm, _, km = hit_at(mid)
                            if pm is not None and km == "glass":
                                hi = mid
                            else:
                                lo = mid
                        zg = lo
                        break
                    z += 0.005
                if zg is None or zg <= z1:
                    rows.append(None)
                    continue
                pts = []
                for z in (z1 - 0.02, (z1 + zg) / 2, zg):
                    pb, _, _ = hit_at(z)
                    if pb is None:
                        break
                    pts.append((s * (abs(pb.x) - 0.006), y, z))
                rows.append(pts if len(pts) == 3 else None)
            verts, faces = [], []
            for a, b in zip(rows, rows[1:]):
                if a is None or b is None:
                    continue
                base = len(verts)
                verts += a + b
                for k in range(2):
                    faces.append((base + k, base + k + 1, base + 4 + k, base + 3 + k))
            if not faces:
                continue
            uv = tuple(src.data.uv_layers[0].data[0].uv) if src.data.uv_layers else None
            P.mesh_object(f"window_edge_{'L' if s < 0 else 'R'}", verts, faces, src.data.materials[0], uv=uv,
                          closed=False, facing=(-s, 0, 0))
            made += len(faces)
        if made:
            print(f"window edge strips: {made} faces on the frame between the rear pillars and the glass")

    def tuck_rear_wall(self, ob, tags, rear, near=0.05, behind=0.007, reach=0.10):
        """0.4.5b3: at a rounded rear corner the traced rear wall's edge runs forward along the side as a thin strip
        (the last rays still meet the corner, 10-25 cm ahead of the back) and crossed the pillar / quarter lining
        at a shallow angle: a saw-tooth edge down the rear pillars, on the Brick even sticking out past the pillar
        into the side window ("the back pillars look glitchy", Brick and Polyana, 26 Nov). Skipping those faces
        opened see-through slits (TrailRat, 0.4.5b2), so nothing is removed: every wall point up to `near` in front of
        the side lining (and the window_edge_strips laid first) moves sideways to just behind the lining's face
        (`behind`, never closer than 3 mm to the body); a point beside a window, ahead of where the lining ends, first
        moves back to the lining's end over glass only (up to `reach`), or lies flat on the frame. Points on a window's
        edge, and the faces they belong to, stay put (moving them opened the window wider or dragged a face across
        the glass). Checked on all 23 cars: no new see-through spots; the Boar keeps it off (cfg rear_tuck=False)."""
        import re
        S = self.sampler
        U = carref.U2B3
        Ui = U.inverted()
        self.window_edge_strips(rear)
        lin = {s_: [o for o in bpy.data.objects if o.type == "MESH"
                    and re.match(r"^(door|quarter|pillar\d+|roof_edge|window_edge)_" + s_ + "$", o.name)] for s_ in "LR"}

        def face_x(y, z, s):
            """|x| of the side lining's inner face at (y, z) on side s, or None where there is no lining."""
            best = None
            for o in lin["L" if s < 0 else "R"]:
                mi = o.matrix_world.inverted()
                ok, loc, _, _ = o.ray_cast(mi @ (U @ Vector((0.0, y, z))), (mi.to_3x3() @ (U @ Vector((s, 0, 0)))).normalized())
                if ok:
                    x = abs((Ui @ (o.matrix_world @ loc)).x)
                    best = x if best is None else min(best, x)
            return best

        me = ob.data
        # Faces with a corner on a window's edge stay as they are: moved out, a point beside the window dragged its
        # face across the glass (a dark wedge in the Boar's rear side windows).
        key = lambda co: (round(co.x, 4), round(co.y, 4), round(co.z, 4))
        frozen = set()
        for poly in me.polygons:
            if any(tags[i] == "glass" for i in poly.vertices):
                frozen.update(key(me.vertices[i].co) for i in poly.vertices)
        tags = ["glass" if key(v.co) in frozen else t for v, t in zip(me.vertices, tags)]
        moved = pulled = 0
        for vtx, tg in zip(me.vertices, tags):
            if tg == "glass":
                continue
            g = Ui @ vtx.co
            if abs(g.x) < 0.25:
                continue
            s = 1 if g.x > 0 else -1
            y, z = g.y, g.z
            f = face_x(y, z, s)
            if f is None:   # ahead of the lining's end (beside a window): onto the body's window frame there
                zz, frame = z, None
                while zz > z - reach and zz > rear:
                    pb, _, kd = S.hit((s * (abs(g.x) - 0.06), y, zz), (s, 0, 0))   # (from near by: the body has inner parts)
                    f = face_x(y, zz, s)
                    if f is not None or (pb is not None and kd != "glass"):
                        frame = None if f is not None else abs(pb.x) - 0.004
                        break
                    zz -= 0.005
                if frame is not None:   # flat on the frame (it covers it: pulled back to the lining, the frame showed)
                    if abs(g.x) < frame - near or (abs(g.x) >= frame and zz == z):
                        continue
                    pulled += zz != z
                    moved += 1
                    vtx.co = U @ Vector((s * max(frame, abs(g.x)), y, zz))
                    continue
                if f is None or abs(g.x) < f - near:
                    continue
                z = zz - 0.003 if zz != z else z
                f = face_x(y, z, s) or f
            if abs(g.x) < f - near or (abs(g.x) >= f + behind and z == g.z):
                continue
            target = f + behind
            pb, _, _ = S.hit((s * (f - 0.01), y, z), (s, 0, 0))   # the skin outside the lining
            if pb is not None and abs(pb.x) > f:
                target = min(target, abs(pb.x) - 0.003)
            if target < f + 0.005:
                continue   # no room behind the lining (closer, it flickered against it: Wombat pillar1_R)
            target = max(target, abs(g.x)) if z == g.z else target
            if target <= abs(g.x) and z == g.z:
                continue
            pulled += z != g.z
            moved += 1
            vtx.co = U @ Vector((s * target, y, z))
        # Second pass, along the lining's own surface: at a big rounded corner (the Polyana's C pillar) the bent side
        # lining and the wall both follow the curve about 1 cm apart and wove through each other. Any wall point up
        # to `cp_near` in front of a lining's inner face (side, roof edge or headliner) goes to `behind` under it.
        cp_near = 0.03
        cp_obs = [(o, -1 if o.name.endswith("_L") else 1 if o.name.endswith("_R") else 0)
                  for o in lin["L"] + lin["R"] + [bpy.data.objects.get("headliner")] if o is not None] if cp_near > 0 else []
        tucked = 0
        for vtx, tg in zip(me.vertices, tags):
            if tg == "glass":
                continue
            g = Ui @ vtx.co
            best = None
            for o, s in cp_obs:
                if s and g.x * s < 0.2:
                    continue
                mi = o.matrix_world.inverted()
                ok, loc, nrm, _ = o.closest_point_on_mesh(mi @ vtx.co, distance=cp_near)
                if not ok:
                    continue
                cp = Ui @ (o.matrix_world @ loc)
                n = (Ui @ (o.matrix_world.to_3x3().inverted().transposed() @ nrm)).normalized()
                inward = (-s * n.x if s else 0.0, -n.y)
                if max(inward) < 0.3:
                    continue   # an end or the outer side, not the face towards the cabin
                ahead = (g - cp).dot(n)
                if ahead < -behind + 1e-4 or (g - cp).length > cp_near:
                    continue
                if ((g - cp) - n * ahead).length > 0.002:
                    continue   # beside the lining's edge, not over its face: moving it would pull the wall open
                if best is None or (g - cp).length < best[0]:
                    best = ((g - cp).length, cp, n)
            if best is None:
                continue
            _, cp, n = best
            dep = 0.004   # (7 mm lay on the back of the TrailRat's headliner: flicker)
            pb, _, _ = S.hit(tuple(cp + n * 0.003), tuple(-n), 0.05)   # the skin behind the lining
            if pb is not None:
                dep = min(dep, (pb - cp).length - 0.003)
            if dep < 0.003:
                continue   # no room under the lining: closer, it flickered against it
            vtx.co = U @ (cp - n * dep)
            tucked += 1
        if cp_obs:
            print(f"rear wall: {tucked} points tucked under a lining face")
        me.update()
        # Faces squeezed to a line (zero area) cover nothing, but the flicker check read one as lying on the pillar
        # (Wombat): drop them.
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        flat = [f for f in bm.faces if f.calc_area() < 1e-7]
        if flat:
            bmesh.ops.delete(bm, geom=flat, context="FACES")
            bm.to_mesh(me)
            print(f"rear wall: {len(flat)} zero-size faces dropped")
        bm.free()
        me.update()
        print(f"rear wall: {moved} edge points tucked behind the side lining ({pulled} moved back from beside a window)")

    def rear_wall_uv(self, m):
        """The rear wall's one colour: the rear side panel below the windows (as the quarter lining beside it).
        Where that lining was built already, exactly its colour (its first UV); see rear_wall_mat for its material."""
        for nm in ("quarter_L", "quarter_R", "door_L", "door_R"):
            ob = bpy.data.objects.get(nm)
            if ob is not None and ob.data.uv_layers and ob.data.materials and ob.data.materials[0] == self.paint:
                print(f"rear wall colour: {nm}'s")
                return tuple(ob.data.uv_layers[0].data[0].uv)
        S = self.sampler
        best = None
        for y in ((m["floor"] + m["belt"]) / 2, (m["floor"] + m["belt"]) / 2 + 0.1):
            for z in (m["rear"] + 0.25, m["rear"] + 0.45, m["rear"] + 0.7):
                for sx in (-1, 1):
                    p, uv, kind = S.hit((sx * 0.2, y, z), (sx, 0, 0))
                    if kind == "paint" and S.shade(uv) >= S.AO_MIN and (best is None or S.shade(uv) > best[0]):
                        best = (S.shade(uv), uv)   # the least shaded spot: as light as the lining beside it
        if best:
            print(f"rear wall colour: the rear side panel's (shade {best[0]:.2f})")
            return best[1]
        return getattr(self, "fallback_uv", P.PAINT_UV)

    def rear_wall_mat(self):
        """The side lining's material when a car lines its sides in something else than the paint (vinyl: Rust Ox)."""
        for nm in ("quarter_L", "quarter_R", "door_L", "door_R"):
            ob = bpy.data.objects.get(nm)
            if ob is not None and ob.data.materials:
                return ob.data.materials[0]
        return self.paint

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
        # A wiper is painted or trim, never glass: the Tinny's windscreen panes are loose 4-corner pieces too, and
        # copied facing in, the game drew them as dark glass from the seat (0.4.5: "I cannot see out the front window").
        from mathutils.interpolate import poly_3d_calc
        S = self.sampler

        def glassy(isl):
            vset = {v.index for v in isl}
            for f in {f for v in isl for f in v.link_faces if all(w.index in vset for w in f.verts)}:
                poly = S.me.polygons[f.index]   # (same mesh: face and loop order as the sampler's)
                w = poly_3d_calc([S.me.vertices[v].co for v in poly.vertices], poly.center)
                uv = (sum(a * S.uv[li].uv[0] for a, li in zip(w, poly.loop_indices)),
                      sum(a * S.uv[li].uv[1] for a, li in zip(w, poly.loop_indices)))
                if S._px(S.mask, S.mask_px, uv)[1] > 0.5:
                    return True
            return False
        boxes, skipped = [], 0
        for isl in pieces:
            pts = [B2U @ v.co for v in isl]
            lo = Vector([min(p[i] for p in pts) for i in range(3)])
            hi = Vector([max(p[i] for p in pts) for i in range(3)])
            if glassy(isl):
                skipped += 1
                continue
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
        print(f"wiper copies: {npieces} panels" + (f" ({skipped} loose glass pieces left alone)" if skipped else ""))
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

    def pillar_trims(self, eye, min_w=0.07, overlap=0.012, overlap_out=0.025, depth=0.035, lift=0.015, shift=0.0, cap=True):
        """Solid trim over both A pillars. The inner skins copy the body's own pillar, but on many cars that is
        a thin flat strip seen from the seat ("a line with no body to it"). Rows of rays from the eye, one per
        degree of pitch, sweep sideways from the windscreen: glass, then the pillar (paint/trim), then the side
        glass. The trim spans the pillar plus `overlap` onto the windscreen and `overlap_out` towards the door
        (covering the door frame's front edge; at least min_w wide), lifted `lift` towards the eye so it sits
        in front of the glass, `depth` deep with a narrower inner face. Its ends run on along the pillar until
        they meet the dash below and the header or roof above. Run before inner_skins (they skip what it
        covers)."""
        from mathutils.bvhtree import BVHTree
        S = self.sampler
        e = Vector(eye)
        U2B3 = carref.U2B3
        dg = bpy.context.evaluated_depsgraph_get()
        verts_, polys_ = [], []
        for ob in bpy.data.objects:
            if ob.type != "MESH" or ob == self.body:
                continue
            ev = ob.evaluated_get(dg)
            me = ev.to_mesh()
            base = len(verts_)
            verts_.extend(ob.matrix_world @ v.co for v in me.vertices)
            polys_.extend([base + i for i in p.vertices] for p in me.polygons)
            ev.to_mesh_clear()
        ours = BVHTree.FromPolygons(verts_, polys_)

        def reach(start, direction, most=0.35, none=0.03):
            """How far along direction (game space) until our parts or the body: the trim's end runs that far
            (`none` if nothing is within `most`: the end is already at the header or dash)."""
            o, d = U2B3 @ start, (U2B3 @ direction).normalized()
            best = None
            for t in (ours, S.bvh):
                h = t.ray_cast(o, d, most)
                if h[0] is not None:
                    best = min(best if best is not None else most, h[3] + 0.02)
            return none if best is None else best
        made, built = [], {}

        def scan(sd, pi):
            """One row of rays at pitch pi: (state, first, last, uv, paint uv); state 3 = windscreen, pillar,
            side glass. uv is the pillar's first hit (often the windscreen's black rubber seal), paint uv the
            first painted hit on it (None if none): the trim takes its colour from that."""
            pitch = math.radians(pi)
            state, first, last, uv, gap, puv = 0, None, None, None, 0, None
            for yi in range(0, 321):
                yaw = math.radians(sd * yi * 0.25)
                d = Vector((math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)))
                p, uv_, kind = S.hit(tuple(e), tuple(d), 2.5)
                if p is None or kind == "light":
                    break
                if state == 0:              # waiting for the windscreen
                    if kind == "glass" and p.z - e.z > 0.15:
                        state = 1
                elif state == 1:            # on the windscreen; the pillar starts at the first non-glass
                    if kind in ("paint", "trim") and (p - e).length < 1.6:
                        state, first, last, uv = 2, p, p, uv_
                        if kind == "paint":
                            puv = uv_
                elif state == 2:            # on the pillar until the side glass
                    if kind == "glass":
                        # A sliver of glass between the windscreen frame and the door's front frame
                        # belongs to the pillar: only 2 degrees of glass end it.
                        gap += 1
                        if gap >= 8:
                            state = 3
                            break
                        continue
                    if kind not in ("paint", "trim") or (p - first).length > 0.25:
                        break
                    last, gap = p, 0
                    if kind == "paint" and puv is None:
                        puv = uv_
            return state, first, last, uv, puv

        for sd in (-1, 1):
            rows = []
            for pi in range(-35, 56):
                state, first, last, uv, puv = scan(sd, pi)
                if state == 3 and (first + last).x / 2 * sd > 0.4 and last.z - e.z > 0.05:
                    rows.append((pi, first, last, uv, puv))
            # The longest run of consecutive pitches whose middle moves on smoothly is the pillar (a row that
            # caught the windscreen's corner or the header instead jumps sideways).
            runs, cur = [], []
            for r in rows:
                if cur and (r[0] != cur[-1][0] + 1 or
                            ((r[1] + r[2]) / 2 - (cur[-1][1] + cur[-1][2]) / 2).length > 0.04):
                    runs.append(cur)
                    cur = []
                cur.append(r)
            if cur:
                runs.append(cur)
            run = max(runs, key=len, default=[])
            if len(run) < 5:
                print(f"pillar trim {'L' if sd < 0 else 'R'}: no pillar found ({len(run)} rows)")
                continue
            # Higher up, the rays past the pillar often meet the roof or door frame instead of the side glass,
            # so the rows above stop counting halfway up the pillar ("half a pillar"). Carry on along the
            # pillar's windscreen edge (still clear: glass, then the pillar) with the last row's width, while
            # that edge rises and moves on smoothly, up to the header (no windscreen in the row any more).
            width = run[-1][2] - run[-1][1]
            added = 0
            for pi in range(run[-1][0] + 1, 56):
                state, first, _, uv, puv = scan(sd, pi)
                prev = run[-1][1]
                if state < 2 or first.y <= prev.y or (first - prev).length > 0.05 or (first - e).length > 1.6:
                    break
                run.append((pi, first, first + width, uv, puv))
                added += 1
            # Smooth the edges over 5 rows (the rays step the edges by a few mm).
            def avg(i, j):
                pts = [run[k][j] for k in range(max(0, i - 2), min(len(run), i + 3))]
                return sum(pts, Vector()) / len(pts)
            edges = [(avg(i, 1), avg(i, 2)) for i in range(len(run))]
            # 0.4.5: no wider than 1.2x the pillar's usual width (median of the middle rows). Near the roof the rows
            # past the pillar meet the door frame or roof edge and the trim fanned out into a wedge or slab there
            # ("A pillar joins the roof oddly": Roamer, Woodman, Burro, Brick, Cumbre and more, drive 22 Nov).
            # (cfg trim_cap=False: not on cars where it cut into the pillar: Bull, Burro, Roamer, drive 25 Nov)
            mid_w = sorted((b - a).length for a, b in edges[len(edges) // 5: len(edges) - len(edges) // 5] or edges)
            cap_w = 1.2 * mid_w[len(mid_w) // 2]
            capped = 0
            for i, (a, b) in enumerate(edges):
                if cap and (b - a).length > cap_w:
                    edges[i] = (a, a + (b - a).normalized() * cap_w)
                    capped += 1
            # The ends run on along the pillar (direction of the last few rows) to the dash and the header.
            k_ = min(4, len(edges) - 1)
            mid = lambda i: (edges[i][0] + edges[i][1]) / 2
            down = (mid(0) - mid(k_)).normalized()
            up = (mid(-1) - mid(-1 - k_)).normalized()
            # 3 cm on into the dash: where the dash top slopes, the door-side corner stopped above it and a
            # wedge of the sill plus a sliver of the body showed at the pillar's foot (DingDing).
            lo_end = reach(mid(0) + (e - mid(0)).normalized() * lift, down) + 0.03
            # Up to the header or roof: the rows often stop short of it (DingDing L, TrailBurner: a gap under
            # the roof, 2026-10-27); reach() stops 2 cm into whatever it meets first.
            hi_end = reach(mid(-1) + (e - mid(-1)).normalized() * lift, up, most=0.30)
            edges.insert(0, (edges[0][0] + down * lo_end, edges[0][1] + down * lo_end))
            edges.append((edges[-1][0] + up * hi_end, edges[-1][1] + up * hi_end))
            secs = []
            for a, b in edges:            # a: windscreen side, b: door side
                across = (b - a).normalized()
                extra = max(0.0, min_w - (b - a).length - overlap - overlap_out)
                lo, ro = a - across * overlap, b + across * (overlap_out + extra)
                lo, ro = lo + across * shift, ro + across * shift   # per car: further towards the door
                c = (lo + ro) / 2
                inward = (e - c).normalized()
                lo, ro = lo + (e - lo).normalized() * lift, ro + (e - ro).normalized() * lift
                li = lo + inward * depth + (c - lo) * 0.3
                ri = ro + inward * depth + (c - ro) * 0.3
                secs.append((lo, li, ri, ro))
            verts = [tuple(v) for s_ in secs for v in s_]
            faces = []
            for i in range(len(secs) - 1):
                a, b = 4 * i, 4 * (i + 1)
                for j in range(4):
                    faces.append((a + j, a + (j + 1) % 4, b + (j + 1) % 4, b + j))
            faces.append((0, 1, 2, 3))
            n = 4 * (len(secs) - 1)
            faces.append((n + 3, n + 2, n + 1, n))
            side = "L" if sd < 0 else "R"
            # Colour: the pillar's paint (middle painted row). The first hit past the windscreen is often its
            # black rubber seal: the Protector and TrailBurner trims came out a different colour from the
            # pillars and from each other (2026-10-27).
            paints = [r[4] for r in run if r[4] is not None]
            mid_uv = paints[len(paints) // 2] if paints else run[len(run) // 2][3]
            colour = f"paint ({len(paints)}/{len(run)} rows)" if paints else "trim (no paint on this pillar)"
            w = [(b - a).length for a, b in edges[1:-1]]
            print(f"pillar trim {side}: {len(run)} rows ({added} along the windscreen edge), pillar {min(w) * 100:.1f}-{max(w) * 100:.1f} cm wide, "
                  f"ends run on {lo_end * 100:.0f} cm down, {hi_end * 100:.0f} cm up, colour {colour}"
                  + (f", {capped} rows narrowed to {cap_w * 100:.1f} cm" if capped else ""))
            built[side] = (verts, faces, mid_uv)
        # 0.4.5: both trims one colour, the header's (the strip above the windscreen they run into): each took its
        # own pillar's paint, and on two-tone and wood-sided liveries one side came out another colour ("left and
        # right A pillars have different colours": Grand Woodman, Woodman, Marshal). No header: the first side's.
        head = bpy.data.objects.get("header")
        if head is not None and head.data.uv_layers:
            one_uv, colour = tuple(head.data.uv_layers[0].data[0].uv), "the header's"
        elif built:
            one_uv, colour = built[sorted(built)[0]][2], f"pillar {sorted(built)[0]}'s"
        # A side where no pillar was found gets the other side's trim, mirrored (the bodies are symmetric): it showed
        # the body's own pillar there, another shape and colour (Tinny L, Blast Wagon R, Marshal L, Rust Ox R).
        if len(built) == 1:
            have = next(iter(built))
            verts, faces, uv_ = built[have]
            other = "R" if have == "L" else "L"
            built[other] = ([(-x, y, z) for x, y, z in verts], [tuple(reversed(f)) for f in faces], uv_)
            print(f"pillar trim {other}: none found, mirrored from {have}")
        for side, (verts, faces, _) in sorted(built.items()):
            ob = P.mesh_object(f"pillar_trim_{side}", verts, faces, self.paint, uv=one_uv, smooth=True)
            # Smooth along the pillar (one section per row: flat shading gave light/dark bands, one per row),
            # sharp at the four long corners and the end caps.
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            sharp = [ed for ed in bm.edges if len(ed.link_faces) == 2
                     and ed.link_faces[0].normal.angle(ed.link_faces[1].normal, 0.0) > math.radians(35)]
            bmesh.ops.split_edges(bm, edges=sharp)
            bm.to_mesh(ob.data)
            bm.free()
            made.append(side)
        if built:
            print(f"pillar trims: colour {colour} on both sides")
        return made

    def inner_skins(self, eye, seat=(0.0, 0.02, -0.12), max_dist=1.6, inset=0.003, open_boxes=()):
        """The game draws the car body from outside only, so from the seat the body's own pillars, window
        frames and roof edges are see-through wherever our lining doesn't cover them: the outside shows
        through the A pillars, the corners beside the windscreen and gaps above it ("pillars not connected").
        Rays from the eye (standard and with the usual seat offset, head straight and turned) find every
        painted or trim body face seen from behind with nothing of ours and no glass in front of it, within
        max_dist; each gets a copy facing inwards with the body's own paint layout (one ring of back-facing
        neighbours too, so no single faces are missed between rays), inset mm towards the cabin. From inside
        the body then looks like it does from outside. Run before frame_covers (it treats these as ours).
        open_boxes: [((x0, y0, z0), (x1, y1, z1))] in game coordinates; body faces with their centre inside one
        stay uncovered (see-through from the seat, as the game draws them): cfg skin_open (DingDing 0.4.4: the
        tall frame under the windscreen glass read as a border hiding the road)."""
        import bmesh
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

        neck = Vector((0, -0.07, -0.10))
        eyes = []
        for off in (Vector(), Vector(seat)):
            for hy in (0.0, -35.0, 35.0):
                r = Matrix.Rotation(math.radians(hy), 3, "Y")
                eyes.append(Vector(eye) + off - neck + r @ neck)
        found = set()
        for e in eyes:
            o0 = U2B3 @ e
            for yaw in [a * 0.5 for a in range(-230, 231)]:
                for pitch in [a * 0.5 for a in range(-110, 91)]:
                    cp = math.cos(math.radians(pitch))
                    d = (U2B3 @ Vector((math.sin(math.radians(yaw)) * cp, math.sin(math.radians(pitch)),
                                        math.cos(math.radians(yaw)) * cp))).normalized()
                    hb, ho = S.bvh.ray_cast(o0, d, max_dist), ours.ray_cast(o0, d, max_dist)
                    if hb[0] is None:
                        continue
                    if ho[0] is not None and ho[3] <= hb[3] and ho[1].dot(d) < 0:
                        continue        # one of our parts in front
                    if hb[1].dot(d) >= 0 and kind(hb[2], hb[0]) in ("paint", "trim"):
                        found.add(hb[2])
        # One ring of neighbours seen from behind as well (thin faces fall between the rays).
        bm = bmesh.new()
        bm.from_mesh(S.me)
        bm.faces.ensure_lookup_table()
        # Faces one of our parts already copies (the wiper copies: same place, facing the other way) stay
        # out: two copies would flicker.
        def covered(fi):
            f = S.me.polygons[fi]
            h = ours.ray_cast(f.center - f.normal * 0.0003, f.normal, 0.0006)
            return h[0] is not None and h[1].dot(f.normal) < -0.9
        small = {fi for fi in found if covered(fi)}
        found -= small
        e0 = U2B3 @ Vector(eye)
        grown = set(found)
        for fi in found:
            for v in bm.faces[fi].verts:
                for f in v.link_faces:
                    if f.index in grown or f.index in small:
                        continue
                    c = f.calc_center_median()
                    if (c - e0).length < max_dist and f.normal.dot(c - e0) > 0 and \
                            kind(f.index, c) in ("paint", "trim") and not covered(f.index):
                        grown.add(f.index)
        bm.free()

        # A face counts only if it's painted or trim all over (a ray near a glass face's edge can read the
        # paint next to it in the livery), and nothing of the glass lies on it (some cars have an opaque
        # face on the window glass, in the same place): otherwise the windows would be covered.
        def opaque(pi):
            poly = S.me.polygons[pi]
            vs = [S.me.vertices[v].co for v in poly.vertices]
            return all(kind(pi, q) in ("paint", "trim") for q in [poly.center] + [poly.center.lerp(v, 0.8) for v in vs])

        GLASS_ON = float(os.environ.get("GLASS_ON", "0.015"))

        def on_glass(pi):
            poly = S.me.polygons[pi]
            vs = [S.me.vertices[v].co for v in poly.vertices]
            n = poly.normal
            for q in [poly.center] + [poly.center.lerp(v, 0.7) for v in vs]:
                for sgn in (1, -1):
                    h = S.bvh.ray_cast(q - n * sgn * GLASS_ON, n * sgn, 2 * GLASS_ON)
                    if h[0] is not None and h[2] != pi and kind(h[2], h[0]) == "glass":
                        return True
            return False

        grown = {pi for pi in grown if opaque(pi) and not on_glass(pi)}
        if open_boxes:
            B2U_ = U2B3.inverted()

            def is_open(pi):
                c = B2U_ @ S.me.polygons[pi].center
                return any(all(lo[i] <= c[i] <= hi[i] for i in range(3)) for lo, hi in open_boxes)
            n_ = len(grown)
            grown = {pi for pi in grown if not is_open(pi)}
            print(f"inner skins: {n_ - len(grown)} body faces left open (skin_open)")
            if os.environ.get("SKIN_OPEN_LIST"):
                for pi in sorted(set(range(len(S.me.polygons))) - grown):
                    if is_open(pi):
                        poly = S.me.polygons[pi]
                        vs_ = [tuple(round(c, 3) for c in B2U_ @ S.me.vertices[v].co) for v in poly.vertices]
                        print("OPEN", pi, tuple(round(c, 3) for c in B2U_ @ poly.center), vs_)
        dbg = os.environ.get("SKIN_FACE")
        if dbg:
            fi = int(dbg)
            print(f"SKIN_FACE {fi}: found {fi in found} covered {covered(fi)} grown {fi in grown}")
        B2U = U2B3.inverted()
        e_ = Vector(eye)
        verts, faces, uvs = [], [], []
        shaded = 0
        # 0.4.5: a car with a floor covering (cfg floor_cover, styles_v2 sets low_cover = (height, material)): copies of
        # body faces down by the floor take that covering (Rust Ox: the step wells in the footwells were the livery's
        # dark green, "the floor is black").
        low_y, low_mat = getattr(self, "low_cover", (None, None))
        lv, lf = [], []
        for pi in sorted(grown):
            poly = S.me.polygons[pi]
            if low_y is not None and (B2U @ poly.center).y < low_y:
                b_ = len(lv)
                for vi in reversed(poly.vertices):
                    p = B2U @ S.me.vertices[vi].co
                    lv.append(tuple(p + (e_ - p).normalized() * inset))
                lf.append(tuple(range(b_, b_ + len(poly.vertices))))
                continue
            base = len(verts)
            # 0.4.5: a face whose paint spot the car's baked shading makes dark (in game: nearly black from the seat;
            # the inside of the body's outer skin is often a shaded spot outside) takes the plain body colour.
            dark = sum(S.shade(tuple(S.uv[li].uv)) for li in poly.loop_indices) / len(poly.loop_indices) < S.AO_MIN
            shaded += dark
            for vi, li in zip(reversed(poly.vertices), reversed(poly.loop_indices)):   # reversed: facing in
                p = B2U @ S.me.vertices[vi].co
                verts.append(tuple(p + (e_ - p).normalized() * inset))
                uvs.append(getattr(self, "fallback_uv", P.PAINT_UV) if dark else tuple(S.uv[li].uv))
            faces.append(tuple(range(base, base + len(poly.vertices))))
        if shaded:
            print(f"inner skins: {shaded} faces over shaded body spots take the plain body colour")
        if lf:
            P.mesh_object("inner_skins_low", lv, lf, low_mat, closed=False)
            print(f"inner skins: {len(lf)} faces by the floor in the floor covering")
        if faces:
            P.mesh_object("inner_skins", verts, faces, self.paint, uvs=uvs, closed=False)
        print(f"inner skins: {len(found)} body faces seen from behind, {len(faces)} copied with neighbours")
        return len(faces)

    def mirror_glass(self, name, which, outline, z, pos=(0, 0, 0), rot=None):
        """A mirror's glass for the mod's mirror cameras: a flat face in the object's x/y plane at local z,
        facing -z (towards the driver), UVs mirrored left/right (the camera picture shown as a mirror image),
        node extras mirror = rear / left / right."""
        xs = [x for x, _ in outline]
        ys = [y for _, y in outline]
        uvs = [(1 - (x - min(xs)) / (max(xs) - min(xs)), (y - min(ys)) / (max(ys) - min(ys))) for x, y in outline]
        mat = P.material("unlit:mirror_" + which, (0.55, 0.60, 0.66), rough=0.2)
        ob = P.mesh_object(name, [(x, y, z) for x, y in outline], [tuple(range(len(outline)))], mat, uvs=uvs,
                           closed=False, facing=(0, 0, -1))
        P.place(ob, pos, rot)
        ob["mirror"] = which
        return ob

    def side_mirrors(self, eye, out_min=0.03, weld=False):
        """The car's own outside mirrors: small separate body pieces outside the cabin, ahead of the eye and
        around eye height, with a flat face looking back at the driver. Each gets a mirror glass 3 mm in front
        of that face (a rectangle inside its outline, so a rim stays). Returns the sides found."""
        best = self._mirror_scan(eye, out_min, weld=False, y_hi=0.15)
        if weld and len(best) < 2:   # cfg mirror_weld (Rust Ox: van mirrors of loose 4-vertex quads, high up at eye + 0.21)
            extra = self._mirror_scan(eye, out_min, weld=True, y_hi=0.40)
            for side in extra:
                best.setdefault(side, extra[side])
        found = []
        for side, (_, plane, n0) in best.items():
            # Plane axes: a across (driver's right), b up; the glass is the outline's bounding box, 12% in.
            ax = n0.cross(Vector((0, 1, 0))).normalized()
            bx = ax.cross(n0).normalized()
            pts = plane   # (filled by _mirror_scan: the face's points, game space)
            o = sum(pts, Vector()) / len(pts)
            us = [(p - o).dot(ax) for p in pts]
            ws_ = [(p - o).dot(bx) for p in pts]
            # The glass follows the face's own outline (convex hull; many mirrors have cut corners), shrunk 24%
            # towards its middle so a rim stays.
            hull = _hull2d(list(zip(us, ws_)))
            hu = sum(p[0] for p in hull) / len(hull)
            hw = sum(p[1] for p in hull) / len(hull)
            outline = [(hu + (p[0] - hu) * 0.76, hw + (p[1] - hw) * 0.76) for p in hull]
            u0, u1 = min(p[0] for p in outline), max(p[0] for p in outline)
            w0, w1 = min(p[1] for p in outline), max(p[1] for p in outline)
            # Object space: x = a, y = b, -z = towards the driver (n0), placed at the outline's centre.
            from mathutils import Matrix
            rot = Matrix((ax, bx, -n0)).transposed()
            centre = o + n0 * 0.003
            self.mirror_glass(f"mirror_glass_{side}", side, outline, 0.0, tuple(centre), rot)
            found.append(f"{side} {abs(u1 - u0) * 100:.0f}x{abs(w1 - w0) * 100:.0f} cm at ({o.x:+.2f}, {o.y:.2f}, {o.z:+.2f})")
        print(f"side mirrors: {', '.join(found) if found else 'none found'}")
        return found

    def _mirror_scan(self, eye, out_min, weld, y_hi):
        """side_mirrors' search: {side: (score, points of the back face in game space, its normal)}.
        weld: merge vertices that share a position first (mirrors made of loose quads)."""
        import bmesh
        B2U = carref.U2B3.inverted()
        bm = bmesh.new()
        bm.from_mesh(self.body.data)
        if weld:
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
        bm.verts.ensure_lookup_table()
        seen, best = set(), {}
        e = Vector(eye)
        for v in bm.verts:
            if v.index in seen:
                continue
            stack, isl = [v], []
            seen.add(v.index)
            while stack:
                a = stack.pop()
                isl.append(a)
                for ed in a.link_edges:
                    o = ed.other_vert(a)
                    if o.index not in seen:
                        seen.add(o.index)
                        stack.append(o)
            if not 8 <= len(isl) <= 600:
                continue
            pts = [B2U @ q.co for q in isl]
            lo = Vector([min(p[i] for p in pts) for i in range(3)])
            hi = Vector([max(p[i] for p in pts) for i in range(3)])
            c = (lo + hi) / 2
            if max(hi - lo) > 0.45 or abs(c.x) < self.half + out_min or not (e.z - 0.2 < c.z < e.z + 1.3)                     or not (e.y - 0.65 < c.y < e.y + y_hi):
                continue
            # The face(s) looking back at the driver: the largest flat group facing backwards.
            faces = {f for q in isl for f in q.link_faces}
            back = []
            for f in faces:
                n = (B2U @ f.normal).normalized()
                fc = B2U @ f.calc_center_median()
                if n.z < -0.55 and n.dot(e - fc) > 0:
                    back.append((f, n, fc))
            if not back:
                continue
            f0, n0, _ = max(back, key=lambda t: t[0].calc_area())
            plane = [(f, n, fc) for f, n, fc in back if n.dot(n0) > 0.97]
            area = sum(f.calc_area() for f, _, _ in plane)
            if area < 0.004:
                continue
            side = "left" if c.x < 0 else "right"
            score = area - 0.02 * abs(c.y - e.y)
            if side not in best or score > best[side][0]:
                best[side] = (score, [B2U @ q.co for q in {q for f, _, _ in plane for q in f.verts}], n0)
        bm.free()
        return best

    def rear_view(self, eye, seen_min=0.35):
        """What the rear-view mirror would show from the driver's eye, like in a real car: the cabin and out
        through the rear window. Rays from the eye reflected off the mirror glass: blocked by our parts and by
        body faces the game draws (seen from the front, not glass), through glass and through body faces seen
        from behind (the game doesn't draw those). If less than seen_min of them get out of the car (no rear
        window, a solid cab back, a canvas tilt), the mirror shows the road behind instead: node extras
        view = road and vx/vy/vz = a camera spot just behind the car (car space, game coordinates); else view = car."""
        from mathutils.bvhtree import BVHTree
        from mathutils.interpolate import poly_3d_calc
        ob = bpy.data.objects.get("mirror_glass_rear")
        if ob is None:
            return None
        U2B3 = carref.U2B3
        B2U = U2B3.inverted()
        dg = bpy.context.evaluated_depsgraph_get()
        verts, polys, owner = [], [], []
        for o in bpy.data.objects:
            if o.type != "MESH" or o == self.body or o == ob:
                continue
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            base = len(verts)
            verts.extend(o.matrix_world @ v.co for v in me.vertices)
            polys.extend([base + i for i in p.vertices] for p in me.polygons)
            owner.extend([o.name] * len(me.polygons))
            ev.to_mesh_clear()
        ours = BVHTree.FromPolygons(verts, polys)
        S = self.sampler
        blockers = {}

        def kind(index, loc):
            poly = S.me.polygons[index]
            w = poly_3d_calc([S.me.vertices[v].co for v in poly.vertices], loc)
            uv = (sum(a * S.uv[li].uv[0] for a, li in zip(w, poly.loop_indices)),
                  sum(a * S.uv[li].uv[1] for a, li in zip(w, poly.loop_indices)))
            r, g, b = S._px(S.mask, S.mask_px, uv)
            return "glass" if g > 0.5 else "light" if r > 0.5 else "paint" if b > 0.5 else "trim"

        gv = [ob.matrix_world @ v.co for v in ob.data.vertices]   # Blender space
        c = sum(gv, Vector()) / len(gv)
        n = (ob.matrix_world.to_3x3() @ ob.data.polygons[0].normal).normalized()
        e = U2B3 @ Vector(eye)
        if n.dot(e - c) < 0:
            n = -n
        seen = total = 0
        for i in range(7):
            for j in range(4):
                # a point on the glass: bilinear over its 4 corners, 85% of the way out from the centre
                a, b_ = i / 6, j / 3
                q = (gv[0] * (1 - a) + gv[1] * a) * (1 - b_) + (gv[3] * (1 - a) + gv[2] * a) * b_
                q = c.lerp(q, 0.85)
                v = (q - e).normalized()
                r = v - 2 * v.dot(n) * n
                o, out = q + n * 0.005, True
                for _ in range(30):
                    hb, ho = S.bvh.ray_cast(o, r, 20.0), ours.ray_cast(o, r, 20.0)
                    db = hb[3] if hb[0] is not None else 1e9
                    do = ho[3] if ho[0] is not None else 1e9
                    if db == 1e9 and do == 1e9:
                        break
                    if do <= db:
                        if ho[1].dot(r) < 0:
                            out = False
                            blockers[owner[ho[2]]] = blockers.get(owner[ho[2]], 0) + 1
                            break
                        o = ho[0] + r * 1e-4
                        continue
                    if hb[1].dot(r) < 0 and kind(hb[2], hb[0]) != "glass":
                        out = False
                        blockers["car body"] = blockers.get("car body", 0) + 1
                        break
                    o = hb[0] + r * 1e-4
                total += 1
                seen += out
        frac = seen / max(total, 1)
        if blockers:
            print("rear view blocked by: " + ", ".join(f"{k_} {v_}" for k_, v_ in sorted(blockers.items(), key=lambda kv: -kv[1])[:5]))
        if frac >= seen_min:
            ob["view"] = "car"
            print(f"rear view: {frac * 100:.0f}% of the mirror looks out of the car: shows the cabin and rear window")
            return "car"
        pts = [B2U @ v.co for v in self.body.data.vertices]
        zmin = min(p.z for p in pts)
        ytop = max(p.y for p in pts)
        cg = B2U @ c
        ob["view"] = "road"
        ob["vx"], ob["vy"], ob["vz"] = 0.0, round(min(cg.y - 0.1, ytop - 0.1), 3), round(zmin - 0.05, 3)
        print(f"rear view: only {frac * 100:.0f}% of the mirror looks out of the car: shows the road from "
              f"({ob['vx']}, {ob['vy']}, {ob['vz']})")
        return "road"

    def wipers(self, blades, arms):
        """Closed copies of the body's wipers (which are single-sided and outside the glass).
        blades: [(lo, hi)] boxes; arms: [(pivot, tip)]."""
        for i, (lo, hi) in enumerate(blades):
            P.box(f"wiper_blade{i}", lo, hi, self.wiper)
        for i, (a, b) in enumerate(arms):
            self.beam(f"wiper_arm{i}", a, b, 0.014, 0.012, self.wiper)

    def body_copy(self, cut_boxes):
        """The game's own body as one of our parts, with pieces cut out (cfg body_cut): while the cockpit view is
        on, the mod switches the game's body off for our own car only and shows this instead (node extra
        hide_game_body). For a piece of the game's body the cockpit can't hide any other way (the game's mesh
        can't be changed by the mod). Same vertices, triangles, paint layout and normals as the game's mesh (normals
        from tools/export_body_normals.py); in game it gets the car's own paint material, livery, dirt and snow, so
        it looks the same. Cut: every separate piece of the mesh (faces joined by shared vertices) whose faces all
        have their centre inside one of cut_boxes [((x0, y0, z0), (x1, y1, z1))], game coordinates.
        DingDing 0.4.4: the dark box on the dash ahead of the driver (3 pieces, 38 triangles).
        Run last, just before export: nothing else may treat it as ours."""
        import json
        path = os.path.join(self.folder, f"{self.car}_body_LOD0.normals.json")
        with open(path) as f:
            normals = json.load(f)
        src = self.body.data
        if len(normals) != len(src.vertices):
            raise RuntimeError(f"{path}: {len(normals)} normals for {len(src.vertices)} vertices (re-export it)")
        U = carref.U2B3
        Ui = U.inverted()
        parent = list(range(len(src.vertices)))

        def root(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        for p in src.polygons:
            for v in p.vertices[1:]:
                parent[root(v)] = root(p.vertices[0])
        pieces = {}
        for p in src.polygons:
            pieces.setdefault(root(p.vertices[0]), []).append(p)

        def inside(c):
            g = Ui @ c
            return any(all(lo[i] <= g[i] <= hi[i] for i in range(3)) for lo, hi in cut_boxes)
        cut = set()
        for faces in pieces.values():
            if all(inside(p.center) for p in faces):
                cut.update(p.index for p in faces)
        keep = [p for p in src.polygons if p.index not in cut]
        me = bpy.data.meshes.new(self.car + "_body_copy")
        me.from_pydata([v.co.copy() for v in src.vertices], [], [list(p.vertices) for p in keep])
        uv = me.uv_layers.new(name="UVMap")
        suv = src.uv_layers[0].data
        i = 0
        for p in keep:
            for li in p.loop_indices:
                uv.data[i].uv = suv[li].uv
                i += 1
        me.update()
        me.normals_split_custom_set_from_vertices([(U @ Vector(n)).normalized() for n in normals])
        me.materials.append(self.paint)
        ob = bpy.data.objects.new("game_body", me)
        ob.matrix_world = self.body.matrix_world.copy()
        ob["hide_game_body"] = "1"
        bpy.context.scene.collection.objects.link(ob)
        print(f"BODY COPY: {len(keep)} of {len(src.polygons)} body faces, {len(cut)} cut out")
        return ob

    # ---- output ----
    def export(self, eye, assets, game_name=None):
        # The body copy stands in for the game's body (switched off meanwhile): it can't flicker against it.
        P.check_flicker(exclude=[self.body] + [o for o in bpy.data.objects if o.get("hide_game_body")], eye=eye)
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
