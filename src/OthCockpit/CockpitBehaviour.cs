using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;
#if MELON
using Il2Cpp;
using Il2CppCinemachine;
#else
using Cinemachine;
#endif

namespace OthCockpit;

// F8 switches to the driver's seat: the car's cockpit model (models\<car>.glb, made in Blender,
// fixed to the car) with working dials, lamps, steering wheel, pedals and levers.
// Numpad 8/2 4/6 9/3 move your head (forward/back, left/right, up/down), 7/1 tilt the view, +/- zoom.
// F9 writes details about the car to the log.
public class CockpitBehaviour : MonoBehaviour
{
    public CockpitBehaviour(IntPtr ptr) : base(ptr) { }

    bool _on;                      // cockpit shown right now
    bool _wanted;                  // the player chose the cockpit view (it hides in menus and comes back)
    float _nextReload;
    int _toggleVk, _dumpVk;
    string _keyNames;

    Transform _carOf;              // car the objects below were built for
    GameObject _cockpit, _camGo;
    CinemachineVirtualCamera _vcam;
    CinemachineFreeLook _chase;
    Vector3 _eye;                  // the model's standard eye position, car-local

    // A part that turns with a value: angle = a0 + (a1 - a0) * (value - zero) / (full - zero), about its local axis.
    sealed class Mover
    {
        public Transform T;
        public Quaternion Base;
        public Vector3 BasePos;
        public bool Slide;          // moves along its axis (metres) instead of turning about it (degrees)
        public Vector3 Axis;
        public string Drive;
        public float A0, A1, Zero, Full, Current, Side, Speed;   // Side: the gear lever's left/right tilt
    }
    readonly List<Mover> _movers = new();
    readonly List<(Material mat, Color color, string which)> _lamps = new();
    readonly List<Material> _backlights = new();
    readonly List<Material> _paintMats = new();
    // The game puts the livery (and dust, mud, snow, wetness) on each body part as a MaterialPropertyBlock,
    // not in the material; our painted parts copy the body's block.
    readonly List<MeshRenderer> _paintRenderers = new();
    Renderer _bodyRenderer;
    MaterialPropertyBlock _block;
    float _nextPaintSync;
    Material _gearMat;
    Color _gearColor;
    int _gearCells;
    string _status = "", _message = "";
    float _messageUntil;

    void Update()
    {
        float now = Time.unscaledTime;
        try
        {
            if (now >= _nextReload)
            {
                _nextReload = now + 2f;
                if (Settings.ReloadIfChanged()) { Plugin.Info("config reloaded"); PlaceSeat(); }
                if (_keyNames != Settings.ToggleKey.Value + Settings.DumpKey.Value)
                {
                    _keyNames = Settings.ToggleKey.Value + Settings.DumpKey.Value;
                    _toggleVk = Keys.Parse(Settings.ToggleKey.Value);
                    _dumpVk = Keys.Parse(Settings.DumpKey.Value);
                }
            }
            // Read every frame, so a press without a car doesn't switch the cockpit later.
            bool keyPressed = Keys.Pressed(_toggleVk), wheelPressed = WheelLink.TogglePressed();
            if (!Settings.Enabled.Value) { _wanted = false; if (_on) SetOn(false); WheelLink.SetCockpitActive(false); return; }

            bool haveCar = Car.Find(now);
            if (!haveCar)
            {
                // _wanted stays: after a respawn or reset you're back in the cockpit.
                if (_on) SetOn(false);
                if (_carOf != null) Teardown();
                WheelLink.SetCockpitActive(false);
                return;
            }
            if (_carOf != null && _carOf != Car.Root) Teardown();
            Car.Update();

            bool driving = Gate.Driving();
            if (keyPressed || wheelPressed) Want(!_wanted, keyPressed ? Settings.ToggleKey.Value : "wheel button");
            else if (driving && !_wanted && Gate.ZoomInPastClosest()) Want(true, "zoom in");
            else if (driving && _wanted && Gate.ZoomOut()) Want(false, "zoom out");
            if (Keys.Pressed(_dumpVk)) Dump();

            // Shown only while driving: menus, map, camp and photo mode get the game's own cameras back.
            bool show = _wanted && driving;
            if (show != _on) SetOn(show);
            WheelLink.SetCockpitActive(_on);
            if (_on) { SeatKeys(); Animate(Time.deltaTime); Head(Time.deltaTime); Ears.Follow(_carOf, _camGo.transform); }
        }
        catch (Exception e) { Plugin.ErrorOnce("update", e); Say(e.Message); }
    }

    // The player switching the cockpit on or off (key, wheel button or zoom; "how" goes to the log).
    void Want(bool want, string how)
    {
        if (want && !File.Exists(ModelPath()))
        {
            Say($"No cockpit for the {Car.Name.Replace("Car_", "")} yet.", 3f);
            return;
        }
        _wanted = want;
        if (want) Say($"Cockpit view ({Settings.ToggleKey.Value} or zoom out to leave, mouse or right stick to look around)", 5f);
        Plugin.Info($"cockpit {(want ? "wanted" : "not wanted")} ({how})");
    }

    static string ModelPath() => Path.Combine(ModPaths.ModelDir, Car.Name + ".glb");

    void Say(string text, float seconds = 6f)
    {
        _message = text;
        _messageUntil = Time.unscaledTime + seconds;
    }

    void SetOn(bool on)
    {
        if (on && !Build()) { _wanted = false; return; }
        _on = on;
        if (_cockpit != null) _cockpit.SetActive(on);
        if (_camGo != null)
        {
            _camGo.SetActive(on);
            if (_chase != null) _vcam.m_Priority = _chase.m_Priority + 1;
        }
        if (on)
        {
            // The livery may have changed in the garage since the cockpit was built.
            var paint = FindPaint(Car.Root, out _);
            if (paint != null) foreach (var m in _paintMats) m.CopyPropertiesFromMaterial(paint);
            _nextPaintSync = 0f;
            Look.Reset();
        }
        else Ears.Restore();
        Plugin.Info($"cockpit {(on ? "ON" : "off")}  [{Car.Describe()}]");
    }

    bool Build()
    {
        if (_carOf == Car.Root && _cockpit != null && _camGo != null) return true;
        Teardown();
        var car = Car.Root;
        string path = ModelPath();
        if (!File.Exists(path))
        {
            Plugin.Info($"no cockpit model: {path}");
            return false;
        }
        var paint = FindPaint(car, out var paintRenderer);
        int layer = paintRenderer != null ? paintRenderer.gameObject.layer : car.gameObject.layer;
        Plugin.Info($"car paint: {(paintRenderer != null ? paintRenderer.name : "none")} -> {(paint != null ? paint.name + " / " + paint.shader.name : "none")}");

        var model = GlbModel.Load(path);
        Materials.BeginBuild();
        var built = GlbBuilder.Build(model, "OthCockpit", paint, layer);
        _cockpit = built.Root;
        _cockpit.transform.SetParent(car, false);
        _cockpit.transform.localPosition = Vector3.zero;
        _cockpit.transform.localRotation = Quaternion.identity;
        Plugin.Info($"model {Path.GetFileName(path)}: {model.Nodes.Count} nodes, {model.Meshes.Count} meshes, {model.Materials.Count} materials, " +
                    $"{model.Images.Count} images, pictures loaded by: {GlbBuilder.TextureLoader}");

        _eye = built.Nodes.TryGetValue("eye", out var eyeNode) ? eyeNode.localPosition : new Vector3(-0.4f, 1.6f, -0.4f);
        _movers.Clear(); _lamps.Clear(); _backlights.Clear(); _gearMat = null;
        _paintMats.Clear();
        _paintRenderers.Clear();
        _bodyRenderer = paintRenderer;
        foreach (var kv in built.ByName) if (kv.Key.StartsWith("paint:")) _paintMats.Add(kv.Value);
        foreach (var (t, n) in built.All)
        {
            var r = t.GetComponent<MeshRenderer>();
            var rm = r != null ? r.sharedMaterial : null;
            if (rm != null && _paintMats.Exists(m => m.Pointer == rm.Pointer)) _paintRenderers.Add(r);
            if (n.Extras.TryGetValue("drive", out var drive))
            {
                string axis = n.Extras.TryGetValue("axis", out var ax) ? ax : "z";
                _movers.Add(new Mover
                {
                    T = t, Base = t.localRotation, BasePos = t.localPosition, Drive = drive,
                    Slide = n.Extras.TryGetValue("move", out var mv) && mv == "slide",
                    Axis = axis == "x" ? Vector3.right : axis == "y" ? Vector3.up : Vector3.forward,
                    A0 = n.Num("a0", 0), A1 = n.Num("a1", 0), Zero = n.Num("zero", 0), Full = n.Num("full", 1),
                    // Needles and the wheel follow quickly, levers move like a hand would.
                    Speed = drive is "handbrake" or "lowrange" or "gear" ? 8f : 15f,
                });
            }
            var mat = MaterialOf(t);
            if (mat == null) continue;
            if (n.Extras.TryGetValue("lamp", out var lamp)) _lamps.Add((mat, BaseColor(mat), lamp));
            if (n.Extras.ContainsKey("backlight")) _backlights.Add(mat);
            if (n.Extras.TryGetValue("display", out var disp) && disp == "gear")
            {
                _gearMat = mat;
                _gearColor = BaseColor(mat);
                _gearCells = (int)n.Num("cells", 8);
                mat.SetTextureScale("_BaseMap", new Vector2(1f / _gearCells, 1f));
            }
        }

        // Our own Cinemachine camera in the driver's seat, one priority above the game's chase camera.
#pragma warning disable CS0618
        var zoom = UnityEngine.Object.FindObjectOfType<ExtraCameraControls>();
#pragma warning restore CS0618
        _chase = zoom != null ? zoom.freeLookCamera : null;
        _camGo = new GameObject("OthCockpit Camera");
        _camGo.transform.SetParent(car, false);
        _vcam = _camGo.AddComponent<CinemachineVirtualCamera>();
        if (_chase != null) _vcam.m_Lens = _chase.m_Lens;
        _vcam.m_Priority = _chase != null ? _chase.m_Priority + 1 : 100;
        _camGo.SetActive(false);
        _cockpit.SetActive(false);
        _carOf = car;
        PlaceSeat();
        Plugin.Info($"cockpit built for {Car.Name}: eye {_eye}, chase cam {(_chase != null ? _chase.name : "NOT FOUND")}, " +
                    $"{_movers.Count} moving parts, {_lamps.Count} lamps, {_backlights.Count} lit dials, gear display {(_gearMat != null)}");
        return true;
    }

    static Material MaterialOf(Transform t)
    {
        var mr = t.GetComponent<MeshRenderer>();
        return mr != null ? mr.sharedMaterial : null;
    }

    static Color BaseColor(Material m) => m.HasProperty("_BaseColor") ? m.GetColor("_BaseColor") : Color.white;

    Vector3 Seat => _eye + new Vector3(Settings.OffsetX.Value, Settings.OffsetY.Value, Settings.OffsetZ.Value);

    void Head(float dt)
    {
        var rot = Look.Update(dt, out var swing);
        _camGo.transform.localPosition = Seat + swing;
        _camGo.transform.localRotation = rot;
    }

    void PlaceSeat()
    {
        if (_camGo == null) return;
        _camGo.transform.localPosition = Seat;
        _camGo.transform.localRotation = Quaternion.Euler(Settings.Pitch.Value, 0f, 0f);
        var lens = _vcam.m_Lens;
        lens.FieldOfView = Settings.FieldOfView.Value;
        lens.NearClipPlane = 0.02f;
        _vcam.m_Lens = lens;
    }

    void SeatKeys()
    {
        const float step = 0.02f;
        bool changed = true;
        if (Keys.Pressed(Keys.NumPad8)) Settings.OffsetZ.Value += step;
        else if (Keys.Pressed(Keys.NumPad2)) Settings.OffsetZ.Value -= step;
        else if (Keys.Pressed(Keys.NumPad6)) Settings.OffsetX.Value += step;
        else if (Keys.Pressed(Keys.NumPad4)) Settings.OffsetX.Value -= step;
        else if (Keys.Pressed(Keys.NumPad9)) Settings.OffsetY.Value += step;
        else if (Keys.Pressed(Keys.NumPad3)) Settings.OffsetY.Value -= step;
        else if (Keys.Pressed(Keys.NumPad7)) Settings.Pitch.Value -= 2f;
        else if (Keys.Pressed(Keys.NumPad1)) Settings.Pitch.Value += 2f;
        else if (Keys.Pressed(Keys.Subtract)) Settings.FieldOfView.Value += 5f;
        else if (Keys.Pressed(Keys.Add)) Settings.FieldOfView.Value -= 5f;
        else changed = false;
        if (!changed) return;
        // Round so the settings file stays readable.
        Settings.OffsetX.Value = (float)Math.Round(Settings.OffsetX.Value, 3);
        Settings.OffsetY.Value = (float)Math.Round(Settings.OffsetY.Value, 3);
        Settings.OffsetZ.Value = (float)Math.Round(Settings.OffsetZ.Value, 3);
        Settings.Saved();
        PlaceSeat();
        Plugin.Info($"seat: offset ({Settings.OffsetX.Value:0.00}, {Settings.OffsetY.Value:0.00}, {Settings.OffsetZ.Value:0.00}) " +
                    $"pitch {Settings.Pitch.Value:0} fov {Settings.FieldOfView.Value:0}");
    }

    static float Value(string drive) => drive switch
    {
        "rpm" => Car.Rpm,
        "speed" => Car.SpeedKmh,
        "steer" => Car.Steer,
        "throttle" => Car.Throttle,
        "brake" => Car.Brake,
        "clutch" => Car.Clutch,
        "handbrake" => Car.Handbrake ? 1f : 0f,
        "lowrange" => Car.LowRange ? 1f : 0f,
        "fuel" => Car.Fuel,
        "temp" => float.IsNaN(Car.OutsideTempC) ? 0f : Car.OutsideTempC,
        _ => 0f,
    };

    // Gear lever positions (H pattern): forward/back tilt and left/right tilt, degrees.
    static (float fwd, float side) GearPosition(int gear) => gear switch
    {
        < 0 => (-12f, -9f),         // reverse: right and back
        1 => (12f, 9f), 2 => (-12f, 9f),
        3 => (12f, 0f), 4 => (-12f, 0f),
        5 => (12f, -9f), 6 => (-12f, -9f),
        _ => (0f, 0f),              // neutral
    };

    // Twice a second: livery, dirt and snow follow the outside of the car.
    void SyncPaint()
    {
        if (Time.unscaledTime < _nextPaintSync || _bodyRenderer == null) return;
        _nextPaintSync = Time.unscaledTime + 0.5f;
        _block ??= new MaterialPropertyBlock();
        _block.Clear();
        _bodyRenderer.GetPropertyBlock(_block);
        foreach (var r in _paintRenderers) if (r != null) r.SetPropertyBlock(_block);
    }

    void Animate(float dt)
    {
        SyncPaint();
        foreach (var m in _movers)
        {
            if (m.Drive == "gear")
            {
                var (fwd, side) = GearPosition(Car.Gear);
                m.Current += (fwd - m.Current) * (1f - Mathf.Exp(-dt * m.Speed));
                m.Side += (side - m.Side) * (1f - Mathf.Exp(-dt * m.Speed));
                m.T.localRotation = m.Base * Quaternion.AngleAxis(m.Current, Vector3.right) * Quaternion.AngleAxis(m.Side, Vector3.forward);
                continue;
            }
            float f = Mathf.Clamp01((Value(m.Drive) - m.Zero) / (m.Full - m.Zero));
            // With the wheel mod: the cockpit wheel turns exactly as far as the real one (clockwise = right).
            if (m.Drive == "steer" && WheelLink.TryAngle(out float deg)) f = (-deg - m.A0) / (m.A1 - m.A0);
            m.Current += (f - m.Current) * (1f - Mathf.Exp(-dt * m.Speed));
            float amount = m.A0 + (m.A1 - m.A0) * m.Current;
            if (m.Slide) m.T.localPosition = m.BasePos + m.Base * m.Axis * amount;
            else m.T.localRotation = m.Base * Quaternion.AngleAxis(amount, m.Axis);
        }

        foreach (var (mat, color, which) in _lamps)
        {
            bool lit = which switch
            {
                "handbrake" => Car.Handbrake,
                "headlights" => Car.Headlights,
                "lowrange" => Car.LowRange,
                "engine" => !Car.EngineRunning,
                _ => false,
            };
            Materials.SetColor(mat, lit ? color : color * 0.12f, "_BaseColor");
            Materials.SetGlow(mat, lit ? color * 3f : Color.black);
        }

        // Dials light up with the headlights, like a real car at night.
        var back = Car.Headlights ? new Color(0.55f, 0.5f, 0.42f) : Color.black;
        foreach (var mat in _backlights) Materials.SetGlow(mat, back);

        if (_gearMat != null)
        {
            int cell = Car.Gear < 0 ? 0 : Mathf.Clamp(Car.Gear + 1, 1, _gearCells - 1);
            _gearMat.SetTextureOffset("_BaseMap", new Vector2((float)cell / _gearCells, 0f));
            Materials.SetColor(_gearMat, Car.EngineRunning ? _gearColor : _gearColor * 0.12f, "_BaseColor");
            Materials.SetGlow(_gearMat, Car.EngineRunning ? _gearColor * 2.5f : Color.black);
        }
        _status = Car.Describe();
    }

    // The car's main paint material: the largest body panel.
    static Material FindPaint(Transform car, out Renderer best)
    {
        best = null;
        float bestVol = 0f;
        foreach (var r in car.GetComponentsInChildren<Renderer>())
        {
            if (!IsBodyPanel(r)) continue;
            var s = r.bounds.size;
            float vol = s.x * s.y * s.z;
            if (vol > bestVol) { bestVol = vol; best = r; }
        }
        return best != null ? best.sharedMaterial : null;
    }

    static bool IsBodyPanel(Renderer r)
    {
        if (r == null || !r.enabled || r.sharedMaterial == null || r.GetComponent<MeshFilter>() == null) return false;
        for (var t = r.transform; t != null; t = t.parent) if (t.name == "OthCockpit") return false;
        string layer = LayerMask.LayerToName(r.gameObject.layer) ?? "";
        if (layer.Contains("FX") || layer.Contains("Transparent")) return false;
        string what = (r.sharedMaterial.shader != null ? r.sharedMaterial.shader.name : "") + " " + r.name + " " + r.sharedMaterial.name;
        foreach (var bad in new[] { "Shadow", "Decal", "Particle", "Light", "Lens", "Flare", "Glass", "Window", "Transparent", "Wheel", "Tire", "Tyre", "Trax" })
            if (what.IndexOf(bad, StringComparison.OrdinalIgnoreCase) >= 0) return false;
        return true;
    }

    void Teardown()
    {
        Ears.Restore();
        if (_cockpit != null) UnityEngine.Object.Destroy(_cockpit);
        if (_camGo != null) UnityEngine.Object.Destroy(_camGo);
        _cockpit = _camGo = null;
        _vcam = null;
        _movers.Clear(); _lamps.Clear(); _backlights.Clear(); _gearMat = null;
        _carOf = null;
        _on = false;
    }

    // F9: what the Blender work needs about this car, into the log.
    void Dump()
    {
        var car = Car.Root;
        var sb = new StringBuilder($"=== car dump: {Car.Name} ===\n{Car.Describe()}\n");
        var seen = new HashSet<IntPtr>();
        foreach (var r in car.GetComponentsInChildren<Renderer>(false))
        {
            var mf = r.GetComponent<MeshFilter>();
            if (mf == null || !r.enabled) continue;   // particles and switched-off accessories
            var mesh = mf.sharedMesh;
            var lp = car.InverseTransformPoint(r.transform.position);
            sb.Append($"  '{PathOf(r.transform, car)}' layer {LayerMask.LayerToName(r.gameObject.layer)} body {IsBodyPanel(r)} " +
                      $"at ({lp.x:0.00}, {lp.y:0.00}, {lp.z:0.00}) mesh '{(mesh != null ? mesh.name : "-")}' " +
                      $"materials [{string.Join(", ", MaterialNames(r))}]\n");
            foreach (var m in r.sharedMaterials)
                if (m != null && seen.Add(m.Pointer)) sb.Append($"    material {Materials.Describe(m)}\n");
        }
        Plugin.Info(sb.ToString());
        Say("Car details written to the log.", 3f);
    }

    static IEnumerable<string> MaterialNames(Renderer r)
    {
        foreach (var m in r.sharedMaterials) yield return m != null ? m.name : "null";
    }

    static string PathOf(Transform t, Transform root)
    {
        var parts = new List<string>();
        for (; t != null && t != root; t = t.parent) parts.Insert(0, t.name);
        return string.Join("/", parts);
    }

    GUIStyle _style;

    void OnGUI()
    {
        bool msg = Time.unscaledTime < _messageUntil;
        if (!msg && !(_on && Settings.ShowData.Value)) return;
        try
        {
            if (_style == null)
            {
                _style = new GUIStyle(GUI.skin.label) { fontSize = 20, fontStyle = FontStyle.Bold };
                _style.normal.textColor = Color.yellow;
            }
            string text = (msg ? _message + "\n" : "") + (_on && Settings.ShowData.Value ? _status : "");
            GUI.Label(new Rect(20, 20, 1900, 90), text, _style);
        }
        catch (Exception e) { Plugin.ErrorOnce("overlay", e); }
    }
}
