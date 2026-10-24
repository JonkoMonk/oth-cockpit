# v2 instrument check: can the driver read every dial? Ray-casts from the eye to points on each dial face,
# warning lamp and the gear display and names what blocks them; lists instruments that overlap each other
# on the same face. fit_wheel() moves the steering wheel a few cm up or down so the rim, spokes and hub
# block as little of the instruments as possible (runs after the build, before the export).
import math

import bpy
from mathutils import Matrix, Vector

import parts as P

GAUGES = ("tacho", "speedo", "fuel", "temp")
LAMPS = ("handbrake", "engine", "headlights", "lowrange")
WEIGHT = {"tacho": 3, "speedo": 3, "fuel": 1.5, "temp": 1.5, "gear": 2}   # lamps 1
WHEEL_TOP = ("steering_wheel", "column", "stalk")                         # moved together (children follow)
WHEEL_PART = ("steering_wheel", "wheel_", "horn_", "column", "stalk")


def instruments():
    """name -> (face object, names of its own parts: hitting those first still counts as visible)."""
    obs = bpy.data.objects
    out = {}
    for k in GAUGES:
        if k + "_face" in obs:
            out[k] = (obs[k + "_face"], {f"{k}_ring", f"{k}_face", f"{k}_needle", f"{k}_cap"})
    for k in LAMPS:
        if "lamp_" + k in obs:
            out["lamp_" + k] = (obs["lamp_" + k], {"lamp_" + k})
    if "gear_display" in obs:
        out["gear"] = (obs["gear_display"], {"gear_display", "gear_window"})
    return out


def _points(face):
    mw = face.matrix_world
    vs = [mw @ v.co for v in face.data.vertices]
    c = sum(vs, Vector()) / len(vs)
    step = max(1, len(vs) // 8)
    return [c] + [c + (v - c) * f for v in vs[::step] for f in (0.45, 0.85)]


def _blocker(dg, eye, p, own, skip):
    d = p - eye
    dist = d.length
    d.normalize()
    o = eye.copy()
    for _ in range(20):
        left = dist - (o - eye).length - 0.0015
        if left <= 0:
            return None
        ok, loc, _n, _i, ob, _m = bpy.context.scene.ray_cast(dg, o, d, distance=left)
        if not ok:
            return None
        if ob.name in own:
            return None
        if ob.name not in skip:
            return ob.name
        o = loc + d * 0.0005
    return None


def blocked(eye, skip):
    """name -> (fraction of its sample points hidden, {blocker: count})."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    e = P.U2B3 @ Vector(eye)
    res = {}
    for name, (face, own) in instruments().items():
        pts = _points(face)
        by = {}
        for p in pts:
            b = _blocker(dg, e, p, own, skip)
            if b:
                by[b] = by.get(b, 0) + 1
        res[name] = (sum(by.values()) / len(pts), by)
    return res


def _wheel_cost(res):
    cost = 0.0
    for name, (_f, by) in res.items():
        n = sum(c for b, c in by.items() if b.startswith(WHEEL_PART))
        total = len(_points(instruments()[name][0]))
        cost += WEIGHT.get(name, 1) * n / total
    return cost


def _move_wheel(obs, base, dy):
    t = P.U2B @ Matrix.Translation((0, dy, 0)) @ P.U2B.inverted()
    for ob, m in zip(obs, base):
        ob.matrix_basis = t @ m


def fit_wheel(eye, skip, lowest=0.07, highest=0.03):
    """Tries the wheel from `highest` above to `lowest` below where the layout put it and keeps the
    height that hides the least of the instruments (small moves win a tie)."""
    obs = [o for o in bpy.data.objects if o.parent is None and o.name.startswith(WHEEL_TOP)]
    base = [o.matrix_basis.copy() for o in obs]
    best = None
    for i in range(int(round((lowest + highest) / 0.01)) + 1):
        dy = highest - i * 0.01
        _move_wheel(obs, base, dy)
        cost = _wheel_cost(blocked(eye, skip)) + 0.04 * abs(dy) / 0.01
        if best is None or cost < best[0] - 1e-6:
            best = (cost, dy)
    _move_wheel(obs, base, best[1])
    print(f"FIT: wheel moved {best[1] * 100:+.0f} cm (cost {best[0]:.2f})")
    return best[1]


def _axis(ob, v):
    """World direction of the object's own GAME axis v (meshes are built in game axes, see parts.py)."""
    return (ob.matrix_world.to_3x3() @ (P.U2B3 @ Vector(v))).normalized()


def _top_level(group):
    return [o for o in group if o.parent is None or o.parent not in group]


def _world_y_range(group):
    ys = [(o.matrix_world @ v.co).z for o in group if o.type == "MESH" for v in o.data.vertices]   # Blender z = game y
    return min(ys), max(ys)


def slide(group, eye, skip, lo_y, hi_y, reach=0.08, step=0.005):
    """Slides one instrument cluster (its dials, lamps, gear display and housing, all made in one go) up or
    down to where the steering wheel and everything else hides the least of its instruments. The cluster
    stays between lo_y and hi_y (game y). Small moves win a tie."""
    obs = _top_level(group)
    base = [o.matrix_basis.copy() for o in obs]
    names = {o.name for o in group}
    bpy.context.view_layer.update()
    y0, y1 = _world_y_range(group)
    best = None
    for i in range(int(round(2 * reach / step)) + 1):
        dy = -reach + i * step
        if y1 + dy > max(hi_y, y1) + 1e-6 or y0 + dy < min(lo_y, y0) - 1e-6:
            continue
        _move_wheel(obs, base, dy)
        res = {n: v for n, v in blocked(eye, skip).items() if instruments()[n][0].name in names}
        cost = sum(WEIGHT.get(n, 1) * frac for n, (frac, _by) in res.items()) + 0.02 * abs(dy) / 0.01
        if best is None or cost < best[0] - 1e-6:
            best = (cost, dy)
    if best is None:
        best = (0.0, 0.0)
    _move_wheel(obs, base, best[1])
    print(f"FIT: cluster '{obs[0].name if obs else '?'}' moved {best[1] * 100:+.1f} cm (cost {best[0]:.2f})")
    return best[1]


HOUSINGS = ("{}_can", "{}_tube", "rect_{}", "square_{}", "pod_{}", "{}_hood", "{}_bowl")


def _group(name):
    """The objects that move with one instrument: its own parts plus a housing made only for it."""
    obs = bpy.data.objects
    if name in GAUGES:
        names = [f"{name}_ring", f"{name}_face", f"needle_{name}"] + [h.format(name) for h in HOUSINGS]
    elif name == "gear":
        names = ["gear_window", "gear_display"]
    else:
        names = [name]
    return [obs[n] for n in names if n in obs]


def _backing(group, eye, skip):
    """How many points around the instrument's outline have a surface right behind them (not hanging in the air)."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    own = {o.name for o in group}
    pts = []
    for o in group:
        if o.type == "MESH":
            mw = o.matrix_world
            vs = [mw @ v.co for v in o.data.vertices]
            c = sum(vs, Vector()) / len(vs)
            pts += [c + (v - c) * 1.05 for v in vs[::max(1, len(vs) // 12)]]
    hits = 0
    for p in pts:
        d = (p - eye).normalized()
        o = p.copy()
        for _ in range(8):
            ok, loc, _n, _i, ob, _m = bpy.context.scene.ray_cast(dg, o, d, distance=0.10)
            if not ok:
                break
            if ob.name not in own:
                hits += 1
                break
            o = loc + d * 0.0005
    return hits, len(pts)


def _housings(name):
    own = instruments()[name][1] if name in instruments() else set()
    return [o for o in _group(name) if o.type == "MESH" and o.name not in own]


def _aabb(o):
    vs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(v[i] for v in vs) for i in range(3)], [max(v[i] for v in vs) for i in range(3)]


def _touch(a, b, gap=0.001):
    (a0, a1), (b0, b1) = a, b
    return all(a0[i] < b1[i] + gap and b0[i] < a1[i] + gap for i in range(3))


def nudge(eye, skip, eye_dys=(0.0, 0.02), shrinks=(1.0, 0.95, 0.9, 0.85), reach=0.03, step=0.005, side=0.02):
    """Last step for instruments the cluster slide couldn't clear: shrinks each still-hidden one a little
    and/or moves it (with its own housing) a few cm, whatever hides the least at every eye height in
    eye_dys. It must keep a surface behind it, not overlap another instrument and not hide the others more.
    Small changes win a tie, so the car's layout stays as it was drawn."""
    eyes = [Vector(eye) + Vector((0, dy, 0)) for dy in eye_dys]

    def score():
        tot = {}
        for e in eyes:
            for n, (frac, _by) in blocked(e, skip).items():
                tot[n] = tot.get(n, 0) + WEIGHT.get(n, 1) * frac
        return tot

    base_score = score()
    todo = sorted((n for n, v in base_score.items() if v >= 0.10 * WEIGHT.get(n, 1)), key=lambda n: -base_score[n])
    for name in todo:
        group = _group(name)
        if not group:
            continue
        face = instruments()[name][0]
        c = P.U2B3.inverted() @ face.matrix_world.translation   # game coordinates
        base = [o.matrix_world.copy() for o in group]
        e0 = P.U2B3 @ Vector(eye)
        back0, nback = _backing(group, e0, skip)
        ov0 = {frozenset((a, b)) for a, b, _d in overlaps()}
        mine = _housings(name)
        others = [_aabb(o) for n in instruments() if n != name for o in _housings(n)]
        start = score()
        best = None
        for s in shrinks:
            for i in range(int(round(2 * reach / step)) + 1):
                dy = -reach + i * step
                for dx in (0.0, -side / 2, side / 2, -side, side):
                    t = P.U2B @ Matrix.Translation(c + Vector((dx, dy, 0))) @ Matrix.Diagonal((s, s, 1, 1)) \
                        @ Matrix.Translation(-c) @ P.U2B.inverted()
                    for o, m in zip(group, base):
                        o.matrix_world = t @ m
                    sc = score()
                    if any(sc[n] > start[n] + 0.01 for n in sc if n != name):
                        continue   # never hide another instrument more
                    if min(_backing(group, e0, skip)[0], back0) < back0:
                        continue
                    ov = {frozenset((a, b)) for a, b, _d in overlaps()}
                    if any(name in p for p in ov - ov0):
                        continue
                    if (s, dx, dy) != (1.0, 0.0, 0.0) and any(_touch(_aabb(o), b) for o in mine for b in others):
                        continue   # its housing would run into another instrument's housing (flicker)
                    cost = sum(sc.values()) + 0.02 * (abs(dy) + abs(dx)) / 0.01 + 0.03 * (1 - s) / 0.05
                    if best is None or cost < best[0] - 1e-6:
                        best = (cost, s, dx, dy, sc[name])
            if best and best[4] < 0.01:
                break   # cleared at this size: no need to shrink more
        if best is None:
            best = (0, 1.0, 0.0, 0.0, start[name])
        _cost, s, dx, dy, left = best
        t = P.U2B @ Matrix.Translation(c + Vector((dx, dy, 0))) @ Matrix.Diagonal((s, s, 1, 1)) @ Matrix.Translation(-c) \
            @ P.U2B.inverted()
        for o, m in zip(group, base):
            o.matrix_world = t @ m
        bpy.context.view_layer.update()
        if (s, dx, dy) != (1.0, 0.0, 0.0):
            print(f"NUDGE: {name} {(1 - s) * 100:.0f}% smaller, moved x {dx * 100:+.1f} y {dy * 100:+.1f} cm "
                  f"(hidden score {start[name]:.2f} -> {left:.2f})")


def _plane_shape(face, own):
    """Centre, axes and outline of an instrument in its face plane: ('circle', r) or ('rect', hx, hy)."""
    mw = face.matrix_world
    c = mw @ Vector()
    ax, ay = _axis(face, (1, 0, 0)), _axis(face, (0, 1, 0))
    pts = []
    for n in own:
        ob = bpy.data.objects.get(n)
        if ob is None or ob.type != "MESH" or n.endswith(("_needle", "_cap")):
            continue
        pts += [((ob.matrix_world @ v.co) - c) for v in ob.data.vertices]
    if face.name == "gear_display":
        return c, ax, ay, ("rect", max(abs(p.dot(ax)) for p in pts), max(abs(p.dot(ay)) for p in pts))
    return c, ax, ay, ("circle", max(math.hypot(p.dot(ax), p.dot(ay)) for p in pts))


def overlaps():
    """Pairs of instruments on (nearly) the same face whose outlines overlap."""
    ins = instruments()
    shapes = {n: _plane_shape(f, own) for n, (f, own) in ins.items()}
    nz = {n: _axis(ins[n][0], (0, 0, 1)) for n in ins}
    found = []
    names = sorted(ins)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ca, ax, ay, sa = shapes[a]
            cb, _, _, sb = shapes[b]
            d = cb - ca
            if abs(d.dot(nz[a])) > 0.02:
                continue   # one stands well in front of the other: the ray check covers that
            x, y = d.dot(ax), d.dot(ay)
            if sa[0] == "rect":
                (x, y), sa, sb = (-x, -y), sb, sa
            ra = sa[1]
            if sb[0] == "circle":
                gap = math.hypot(x, y) - ra - sb[1]
            else:
                qx, qy = max(abs(x) - sb[1], 0), max(abs(y) - sb[2], 0)
                gap = math.hypot(qx, qy) - ra
            if gap < -0.001:
                found.append((a, b, -gap))
    return found


def report(eye, skip):
    res = blocked(eye, skip)
    n = 0
    for name, (frac, by) in sorted(res.items()):
        if frac >= 0.10:
            n += 1
            who = ", ".join(f"{b} {c}" for b, c in sorted(by.items(), key=lambda t: -t[1]))
            print(f"BLOCKED: {name} {frac * 100:.0f}% hidden ({who})")
    ov = overlaps()
    for a, b, depth in ov:
        print(f"OVERLAP: {a} and {b} overlap by {depth * 1000:.0f} mm")
    print(f"instrument check: {n} blocked, {len(ov)} overlapping")
    return res, ov
