# Prints each car's engine idle / peak / max rpm from the car prefabs (VPVehicleController.engine),
# to scale the rev counters. Usage: python -I car_engines.py <cars bundle>
import sys, os
sys.path.insert(0, os.path.expandvars(r"%USERPROFILE%\dev\tools\pylibs"))
import UnityPy
env = UnityPy.load(sys.argv[1])
roots = {}
for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    try:
        tree = obj.read_typetree()
    except Exception:
        continue
    eng = tree.get("engine")
    if not isinstance(eng, dict) or "maxRpm" not in eng:
        continue
    go = tree.get("m_GameObject")
    name = "?"
    try:
        name = obj.read().m_GameObject.deref().peek_name()
    except Exception:
        pass
    print(f"{name:28s} idle {eng.get('idleRpm')} peak {eng.get('peakRpm')} max {eng.get('maxRpm')}")
