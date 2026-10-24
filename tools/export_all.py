# Exports every car in a cars bundle as modelling reference (never shipped): body mesh (OBJ), textures
# (PNG), material settings, and placement.json (scale + offset of the body mesh inside the car prefab).
# Reads the bundle once. Usage: python -I export_all.py <cars bundle> <out folder> [Car names...]
import json
import os
import sys

sys.path.insert(0, os.path.expandvars(r"%USERPROFILE%\dev\tools\pylibs"))
import UnityPy  # noqa: E402

bundle, out_root = sys.argv[1:3]
only = set(sys.argv[3:])
env = UnityPy.load(bundle)

objs = {}
for obj in env.objects:
    if obj.type.name in ("Mesh", "Texture2D", "Material", "GameObject"):
        objs.setdefault(obj.type.name, []).append(obj)

# Car names from the prefab roots ("Car_X") that have a body mesh "X_body_LOD0".
# The game's own spelling slips: Polyana's body is "Polyana_bodu_LOD0". Read as "_body_LOD0".
BODY_SUFFIXES = ("_body_LOD0", "_bodu_LOD0")
meshes = {}
for o in objs["Mesh"]:
    n = o.peek_name()
    for suffix in BODY_SUFFIXES[1:]:
        if n.endswith(suffix):
            n = n[:-len(suffix)] + "_body_LOD0"
    meshes[n] = o
cars = sorted(n[:-len("_body_LOD0")] for n in meshes if n.endswith("_body_LOD0"))
if only:
    cars = [c for c in cars if c in only]
print("cars:", ", ".join(cars))


def transform_of(go_obj):
    g = go_obj.read()
    for c in g.m_Component:
        comp = c.component if hasattr(c, "component") else c[1]
        o = comp.deref()
        if o.type.name == "Transform":
            return o.read()
    return None


body_gos = {}
for o in objs["GameObject"]:
    n = o.peek_name()
    for suffix in BODY_SUFFIXES:
        if n.endswith(suffix):
            body_gos.setdefault(n[:-len(suffix)] + "_body_LOD0", o)

for car in cars:
    out = os.path.join(out_root, car)
    os.makedirs(out, exist_ok=True)
    # Placement: walk the transform chain from the body up to the car root, composing scale and offset
    # (the chains seen so far have no rotations).
    tr = transform_of(body_gos[car + "_body_LOD0"]) if car + "_body_LOD0" in body_gos else None
    scale, off, chain = 1.0, [0.0, 0.0, 0.0], []
    while tr is not None:
        p, r, s = tr.m_LocalPosition, tr.m_LocalRotation, tr.m_LocalScale
        chain.append({"name": tr.m_GameObject.deref().peek_name(), "pos": [p.x, p.y, p.z],
                      "rot": [r.x, r.y, r.z, r.w], "scale": [s.x, s.y, s.z]})
        f = tr.m_Father
        tr = f.deref().read() if f and f.path_id else None
    # Compose child -> root: v_parent = pos + scale * v_child. The root (Car_X) itself is the car's space,
    # its own position in the prefab doesn't count.
    for link in chain[:-1]:
        scale *= link["scale"][0]
        off = [link["pos"][i] + link["scale"][i] * off[i] for i in range(3)]
    rotated = any(abs(l["rot"][3]) < 0.9999 for l in chain)
    with open(os.path.join(out, "placement.json"), "w") as f:
        json.dump({"scale": scale, "offset": off, "rotated": rotated, "chain": chain}, f, indent=1)
    print(f"{car}: scale {scale:.3f} offset ({off[0]:.4f}, {off[1]:.4f}, {off[2]:.4f}){' ROTATED' if rotated else ''}")

    mesh = meshes[car + "_body_LOD0"].read()
    with open(os.path.join(out, f"{car}_body_LOD0.obj"), "w") as f:
        f.write(mesh.export())
    # Extra body parts that matter inside the cabin (e.g. a roll cage), same placement as the body.
    for extra in ("rollcage",):
        m = meshes.get(f"{car}_{extra}_LOD0")
        if m is not None:
            with open(os.path.join(out, f"{car}_{extra}_LOD0.obj"), "w") as f:
                f.write(m.read().export())
            print(f"  + {extra}")
    for t in objs["Texture2D"]:
        n = t.peek_name()
        if n.startswith(car + "_") and ("skin" in n or n.endswith("_masks") or n.endswith("_AO_Dirty") or n.endswith("_lights")):
            path = os.path.join(out, n + ".png")
            if not os.path.exists(path):
                t.read().image.save(path)
