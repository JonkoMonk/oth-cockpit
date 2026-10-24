# Exports one car's body mesh (OBJ) and textures (PNG) from the game's cars bundle, as modelling reference.
# Usage: python -I export_car.py <bundle> <CarName e.g. DingDing> <out dir>
import sys, os, json
sys.path.insert(0, os.path.expandvars(r"%USERPROFILE%\dev\tools\pylibs"))
import UnityPy
bundle, car, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
env = UnityPy.load(bundle)
for obj in env.objects:
    t = obj.type.name
    if t not in ("Mesh", "Texture2D", "Material"):
        continue
    name = obj.peek_name()
    if not (name.startswith(car + "_") or name == car):
        continue
    d = obj.read()
    if t == "Mesh" and ("body_LOD0" in name or "collider" in name or "wheel_LOD0" in name):
        with open(os.path.join(out, name + ".obj"), "w") as f:
            f.write(d.export())
        print("mesh", name, d.m_VertexCount if hasattr(d, "m_VertexCount") else "")
    elif t == "Texture2D":
        img = d.image
        img.save(os.path.join(out, name + ".png"))
        print("tex", name, img.size)
    elif t == "Material":
        tree = obj.read_typetree()
        props = tree.get("m_SavedProperties", {})
        info = {"shader": str(tree.get("m_Shader")), "floats": props.get("m_Floats"), "colors": props.get("m_Colors"),
                "textures": [(k, v.get("m_Texture")) for k, v in props.get("m_TexEnvs", [])]}
        with open(os.path.join(out, name + ".material.json"), "w") as f:
            json.dump(info, f, indent=1, default=str)
        print("material", name)
