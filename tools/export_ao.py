# 0.4.5: saves each car's baked shading (_AO_Texture of its body material) as <cars>/<folder>/<folder>_AO.png, the build
# uses it (carref.PaintSampler.shade) so parts never take their colour from a dark spot (black in game).
# Usage (Blender's Python): python -I export_ao.py <cars_assets_all_*.bundle> <cars folder>
import sys, os
sys.path.insert(0, os.path.expandvars(r"%USERPROFILE%\dev\tools\pylibs"))
import UnityPy
bundle, cars = sys.argv[1:3]
folders = {f.lower(): f for f in os.listdir(cars) if os.path.isdir(os.path.join(cars, f))}
alias = {"bull": "BullV1"}
env = UnityPy.load(bundle)
by_id = {o.path_id: o for o in env.objects if o.type.name == "Texture2D"}
for obj in env.objects:
    if obj.type.name != "Material":
        continue
    n = obj.peek_name()
    folder = alias.get(n.lower()) or folders.get(n.lower())
    if not folder:
        continue
    tree = obj.read_typetree()
    tex = dict((k, v) for k, v in tree["m_SavedProperties"]["m_TexEnvs"])
    pid = tex.get("_AO_Texture", {}).get("m_Texture", {}).get("m_PathID")
    t = by_id.get(pid)
    if t is None:
        print(n, "no AO", pid); continue
    d = t.read()
    out = os.path.join(cars, folder, f"{folder}_AO.png")
    d.image.save(out)
    print(n, "->", out, d.m_Name, d.image.size)
