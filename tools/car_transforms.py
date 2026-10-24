# Prints the transform chain (local position / rotation / scale) from a named part up to the car root.
import sys, os
sys.path.insert(0, os.path.expandvars(r"%USERPROFILE%\dev\tools\pylibs"))
import UnityPy
bundle, part = sys.argv[1:3]
env = UnityPy.load(bundle)
gos = [o for o in env.objects if o.type.name == "GameObject" and o.peek_name() == part]
print(len(gos), "objects named", part)
for go in gos[:3]:
    g = go.read()
    tr = None
    for c in g.m_Component:
        comp = c.component if hasattr(c, "component") else c[1]
        o = comp.deref()
        if o.type.name == "Transform":
            tr = o.read(); break
    chain = []
    while tr is not None:
        name = tr.m_GameObject.deref().peek_name()
        p, r, s = tr.m_LocalPosition, tr.m_LocalRotation, tr.m_LocalScale
        chain.append(f"  {name}: pos ({p.x:.4f},{p.y:.4f},{p.z:.4f}) rot ({r.x:.4f},{r.y:.4f},{r.z:.4f},{r.w:.4f}) scale ({s.x:.4f},{s.y:.4f},{s.z:.4f})")
        f = tr.m_Father
        tr = f.deref().read() if f and f.path_id else None
    print("\n".join(chain)); print("--")
