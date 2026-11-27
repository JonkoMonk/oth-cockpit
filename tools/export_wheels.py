# 0.4.5: per car the wheel anchors (car-local game coordinates) and the tyre radius from the game's car prefab, as
# <cars>/<folder>/wheels.json; styles_v2.wheel_arches puts covers over the rear tyres where they reach into the cabin.
# Usage (Blender's Python): python -I export_wheels.py <cars_assets_all_*.bundle> <cars folder>
import sys, os, json
sys.path.insert(0, os.path.expandvars(r"%USERPROFILE%\dev\tools\pylibs"))
import UnityPy
bundle, cars_dir = sys.argv[1], sys.argv[2]
env = UnityPy.load(bundle)
gos = {}
for o in env.objects:
    if o.type.name == "GameObject":
        gos.setdefault(o.peek_name(), []).append(o)
def comps(go):
    for c in go.m_Component:
        comp = c.component if hasattr(c, "component") else c[1]
        yield comp.deref()
def tr_of(go):
    for o in comps(go):
        if o.type.name == "Transform":
            return o.read()
def find(tr, name, pos=(0, 0, 0), scale=(1, 1, 1), out=None):
    out = [] if out is None else out
    g = tr.m_GameObject.deref().read()
    p, s = tr.m_LocalPosition, tr.m_LocalScale
    pos2 = (pos[0] + p.x * scale[0], pos[1] + p.y * scale[1], pos[2] + p.z * scale[2])   # (no rotations on this path)
    sc2 = (scale[0] * s.x, scale[1] * s.y, scale[2] * s.z)
    out.append((g.m_Name, pos2, sc2, g))
    for ch in tr.m_Children:
        find(ch.deref().read(), name, pos2, sc2, out)
    return out
result = {}
for folder in os.listdir(cars_dir):
    game = {"BullV1": "Bull"}.get(folder, folder)
    roots = gos.get("Car_" + game) or gos.get("Car_" + game.capitalize())
    if not roots:
        print(folder, "no prefab"); continue
    nodes = find(tr_of(roots[0].read()), None)
    wheels = {n: p for n, p, s, g in nodes if n in ("WheelRL", "WheelRR", "WheelFL", "WheelFR")}
    radius = width = None
    for n, p, s, g in nodes:
        for c in comps(g):
            if c.type.name == "MeshFilter":
                mf = c.read()
                try:
                    me = mf.m_Mesh.deref()
                except Exception:
                    continue
                mn = me.peek_name() or ""
                if "tyre" in mn.lower() or "wheel" in mn.lower():
                    m = me.read()
                    e = m.m_LocalAABB.m_Extent
                    r = max(e.y * s[1], e.z * s[2]); w = 2 * e.x * s[0]
                    if radius is None or r > radius:
                        radius, width = r, w
    result[folder] = dict(wheels={k: [round(v, 3) for v in p] for k, p in wheels.items()},
                          radius=round(radius, 3) if radius else None, width=round(width, 3) if width else None)
    print(folder, result[folder])
    with open(os.path.join(cars_dir, folder, "wheels.json"), "w") as f:
        json.dump(result[folder], f)
