using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace OthCockpit;

// Working mirrors (plan: PLAN-mirrors.md). The model marks each mirror's glass with the node extra
// mirror = rear / left / right (a flat face, UVs already mirrored left/right). For each one a small camera
// renders into a texture shown on that glass. The camera looks along the driver's line of sight reflected in
// the mirror, with the angle the glass covers from the eye, so the picture moves like a real mirror when the
// head moves. Cameras only exist with the cockpit and only run while it shows.
//  - Rear-view mirror: the camera sits just behind the car (the model's vx/vy/vz) and shows the road behind.
//    [Mirrors] RearView = Car instead shows the cabin and out through the back like a real car (the model aims
//    the glass at the rear window); in most cars that view is mostly load space.
//  - Side mirrors: their glass is the car's own; they're aimed along the car's flank, a little out and down,
//    from the standard eye position, as a driver would set them.
//  - [Mirrors] Quality: Low / Medium / High / Ultra (or Custom) sets size, update rate, distance and shadows.
internal static class Mirrors
{
    sealed class Mirror
    {
        public string Which;
        public Transform Glass;
        public Vector3 Centre, Normal, Up;   // glass-local
        public Vector3 AimNormal;            // car-local: the normal a driver would set (side mirrors)
        public bool Road;                    // rear-view mirror showing the road from behind the car
        public Vector3 RoadFrom;             // car-local camera spot for Road
        public Quaternion RoadFix = Quaternion.identity;   // car-local: lifts the road view to [Mirrors] RearViewTilt
        public float Width, Height;          // metres
        public Camera Cam;
        public RenderTexture Texture;
    }

    // What each quality level means.
    readonly struct Level
    {
        public readonly bool Sides, Shadows;
        public readonly float Resolution, Far;
        public readonly int Every;
        public Level(bool sides, float res, int every, float far, bool shadows)
        { Sides = sides; Resolution = res; Every = every; Far = far; Shadows = shadows; }
    }

    static Level Current() => Settings.MirrorQualityLevel.Value switch
    {
        Settings.MirrorQuality.Low => new Level(false, 0.5f, 3, 150f, false),
        Settings.MirrorQuality.Medium => new Level(true, 0.75f, 2, 250f, false),
        Settings.MirrorQuality.High => new Level(true, 1.0f, 2, 500f, false),
        Settings.MirrorQuality.Ultra => new Level(true, 1.5f, 1, 900f, true),
        _ => new Level(Settings.SideMirrors.Value, Mathf.Clamp(Settings.MirrorResolution.Value, 0.25f, 2f),
                       Math.Max(1, (int)Settings.MirrorUpdateEvery.Value), 400f, false),
    };

    static readonly List<Mirror> _mirrors = new();
    static Transform _car;
    static Level _level;
    static int _frame;
    static float _sumDt, _logAt, _gpuiCheckAt;
    static int _frames;

    // After a cockpit is built (and when the settings change): a camera and texture for every mirror glass.
    // eye: the model's standard eye position, car-local.
    public static void Setup(GlbBuilder.Result built, Transform car, Vector3 eye)
    {
        Teardown();
        if (!Settings.MirrorsOn.Value) return;
        _car = car;
        _level = Current();
        var main = Camera.main;
        var found = new List<string>();
        foreach (var (t, n) in built.All)
        {
            if (!n.Extras.TryGetValue("mirror", out var which)) continue;
            if (which != "rear" && !_level.Sides) continue;
            try
            {
                var m = Make(t, n, which, main, car, eye);
                if (m == null) continue;
                _mirrors.Add(m);
                found.Add($"{which}{(m.Road ? " (road)" : "")} {m.Texture.width}x{m.Texture.height} ({m.Width * 100:0}x{m.Height * 100:0} cm)");
            }
            catch (Exception e) { Plugin.ErrorOnce("mirror " + which, e); }
        }
        _frame = 0; _sumDt = 0f; _frames = 0; _logAt = Time.unscaledTime + 30f;
        Plugin.Info($"mirrors ({Settings.MirrorQualityLevel.Value}): {(found.Count > 0 ? string.Join(", ", found) : "none in this model")}");
    }

    static Mirror Make(Transform t, GlbModel.Node node, string which, Camera main, Transform car, Vector3 eye)
    {
        var mf = t.GetComponent<MeshFilter>();
        if (mf == null) mf = t.GetComponentInChildren<MeshFilter>();
        var mr = mf != null ? mf.GetComponent<MeshRenderer>() : null;
        if (mf == null || mr == null || mf.sharedMesh == null) return null;
        var glass = mf.transform;
        var verts = mf.sharedMesh.vertices;
        var tris = mf.sharedMesh.triangles;
        if (verts.Length < 3 || tris.Length < 3) return null;
        var centre = Vector3.zero;
        foreach (var v in verts) centre += v;
        centre /= verts.Length;
        var normal = Vector3.Cross(verts[tris[1]] - verts[tris[0]], verts[tris[2]] - verts[tris[0]]).normalized;
        // Size across and up in the glass plane (the up axis: the one closest to the car's up).
        var upCar = glass.InverseTransformDirection(car.up);
        var up = Vector3.ProjectOnPlane(upCar, normal).normalized;
        var across = Vector3.Cross(up, normal).normalized;
        float u0 = float.MaxValue, u1 = float.MinValue, w0 = float.MaxValue, w1 = float.MinValue;
        foreach (var v in verts)
        {
            float u = Vector3.Dot(v - centre, across), w = Vector3.Dot(v - centre, up);
            u0 = Math.Min(u0, u); u1 = Math.Max(u1, u); w0 = Math.Min(w0, w); w1 = Math.Max(w1, w);
        }
        var scale = glass.lossyScale;
        float width = (u1 - u0) * Math.Abs(scale.x), height = (w1 - w0) * Math.Abs(scale.y);
        if (width < 0.01f || height < 0.01f) return null;

        // Side mirrors: aimed from the standard eye along the car's flank, 14° out and 3° down (at 6° the
        // flank and what hangs on it, the DingDing's jerrycans, filled half the mirror).
        var centreCar = car.InverseTransformPoint(glass.TransformPoint(centre));
        var aim = Vector3.zero;
        if (which != "rear")
        {
            var back = new Vector3(Mathf.Sign(centreCar.x) * 0.25f, -0.05f, -1f).normalized;
            aim = ((eye - centreCar).normalized + back).normalized;
        }
        // Rear-view mirror: the road from behind the car where the model asks for it (or the setting does).
        bool road = false;
        var roadFrom = Vector3.zero;
        if (which == "rear")
        {
            // Auto = the road for every car: through the cabin (Car) the mirror mostly showed the load space
            // and the rear wall (JonkoMonk, 2026-10-25), not what's behind.
            road = Settings.RearView.Value != Settings.RearViewMode.Car;
            if (road)
                roadFrom = node.Extras.ContainsKey("vz")
                    ? new Vector3(node.Num("vx", 0f), node.Num("vy", 1.5f), node.Num("vz", -2.5f))
                    : RoadSpot(car, centreCar);
        }
        // The glass is aimed down through the cabin at the rear window, which pointed the road view at the
        // ground behind the car (2026-11-06). Keep how it moves with the head, but start it from this tilt.
        var roadFix = Quaternion.identity;
        if (road)
        {
            var n = car.InverseTransformDirection(glass.TransformDirection(normal)).normalized;
            if (Vector3.Dot(n, eye - centreCar) < 0f) n = -n;
            var neutral = Vector3.Reflect((centreCar - eye).normalized, n);
            var flat = new Vector2(neutral.x, neutral.z).magnitude;
            var wanted = new Vector3(neutral.x, flat * Mathf.Tan(Settings.RearViewTilt.Value * Mathf.Deg2Rad), neutral.z).normalized;
            roadFix = Quaternion.FromToRotation(neutral, wanted);
            Plugin.Info($"rear-view road: the glass aims {Mathf.Asin(neutral.y) * Mathf.Rad2Deg:0.0} deg, shown at {Settings.RearViewTilt.Value:0.0} deg");
        }

        // Texture: rear 512 wide, side 320 high (times the quality's resolution), the glass's shape.
        float res = _level.Resolution;
        int tw, th;
        if (which == "rear") { tw = (int)(512 * res); th = (int)(tw * height / width); }
        else { th = (int)(320 * res); tw = (int)(th * width / height); }
        tw = Mathf.Clamp(tw, 32, 1024); th = Mathf.Clamp(th, 32, 1024);
        var rt = new RenderTexture(tw, th, 16) { name = "OthCockpit mirror " + which };
        rt.Create();

        var mat = mr.material;   // this glass's own copy
        foreach (var p in new[] { "_BaseMap", "_MainTex" }) if (mat.HasProperty(p)) mat.SetTexture(p, rt);
        Materials.SetColor(mat, Color.white, "_BaseColor", "_Color");

        var go = new GameObject("OthCockpit Mirror " + which);
        go.transform.SetParent(car, false);
        var cam = go.AddComponent<Camera>();
        cam.targetTexture = rt;
        // The road view starts half a metre out: spare wheels and jerrycans on the back don't fill it.
        cam.nearClipPlane = road ? 0.5f : 0.03f;
        cam.farClipPlane = _level.Far;
        cam.allowHDR = false;
        cam.allowMSAA = false;
        if (main != null)
        {
            cam.depth = main.depth - 1;
            cam.cullingMask = main.cullingMask;
            cam.clearFlags = main.clearFlags;
            cam.backgroundColor = main.backgroundColor;
            cam.useOcclusionCulling = main.useOcclusionCulling;
        }
        try
        {
            var data = go.AddComponent<UniversalAdditionalCameraData>();
            data.renderPostProcessing = false;
            data.renderShadows = _level.Shadows;
            data.antialiasing = AntialiasingMode.None;
            data.requiresDepthTexture = false;
            data.requiresColorTexture = false;
        }
        catch (Exception e) { Plugin.Warn($"mirror {which}: URP camera settings not applied ({e.Message})"); }
        Instancer.AddComponent(go);   // trees, grass and rocks are drawn only for GPU Instancer's cameras
        cam.enabled = false;
        go.SetActive(false);
        return new Mirror
        {
            Which = which, Glass = glass, Centre = centre, Normal = normal, Up = up, AimNormal = aim,
            Road = road, RoadFrom = roadFrom, RoadFix = roadFix, Width = width, Height = height, Cam = cam, Texture = rt,
        };
    }

    // Behind the car at the mirror's height (older models without vx/vy/vz): from the car's renderers.
    static Vector3 RoadSpot(Transform car, Vector3 mirrorCar)
    {
        float zmin = -2.5f;
        try
        {
            foreach (var r in car.GetComponentsInChildren<Renderer>())
            {
                var b = r.bounds;
                for (int i = 0; i < 8; i++)
                {
                    var p = car.InverseTransformPoint(new Vector3(i % 2 == 0 ? b.min.x : b.max.x, (i / 2) % 2 == 0 ? b.min.y : b.max.y,
                                                                  i < 4 ? b.min.z : b.max.z));
                    if (p.z < zmin && p.z > -8f) zmin = p.z;
                }
            }
        }
        catch { }
        return new Vector3(0f, mirrorCar.y - 0.1f, zmin - 0.05f);
    }

    public static void SetActive(bool on)
    {
        foreach (var m in _mirrors)
            if (m.Cam != null) { m.Cam.gameObject.SetActive(on); m.Cam.enabled = false; }
    }

    // Every frame while the cockpit shows, after the head has moved: aim each mirror camera, and let it
    // render on its turn (every frame, every 2nd, ... per the quality; the mirrors take turns).
    public static void Tick(Vector3 eye, float dt)
    {
        if (_mirrors.Count == 0 || _car == null) return;
        _frame++;
        int every = Math.Max(1, _level.Every);
        for (int i = 0; i < _mirrors.Count; i++)
        {
            var m = _mirrors[i];
            if (m.Cam == null || m.Glass == null) continue;
            var centre = m.Glass.TransformPoint(m.Centre);
            var normal = m.Which == "rear" ? m.Glass.TransformDirection(m.Normal).normalized : _car.TransformDirection(m.AimNormal).normalized;
            if (Vector3.Dot(normal, eye - centre) < 0f) normal = -normal;   // the side facing the driver
            var view = centre - eye;
            float dist = view.magnitude;
            if (dist < 0.05f) continue;
            var look = Vector3.Reflect(view / dist, normal);
            if (m.Road) look = _car.rotation * m.RoadFix * Quaternion.Inverse(_car.rotation) * look;
            var up = Vector3.ProjectOnPlane(_car.up, look);
            var from = m.Road ? _car.TransformPoint(m.RoadFrom) : centre + normal * 0.005f;
            m.Cam.transform.SetPositionAndRotation(from, Quaternion.LookRotation(look, up.sqrMagnitude > 1e-6f ? up : Vector3.up));
            // The angle the glass covers from the eye; side mirrors are a little convex (they show more), and
            // the road view a bit wider (no cabin around it to judge distance by).
            float wide = m.Road ? 1.3f : m.Which == "rear" ? 1.0f : 1.35f;
            m.Cam.fieldOfView = Mathf.Clamp(2f * Mathf.Atan(m.Height * 0.5f / dist) * Mathf.Rad2Deg * wide, 2f, 90f);
            m.Cam.aspect = m.Width / m.Height;
            m.Cam.enabled = (_frame + i) % every == 0;
            if (m.Cam.enabled && Time.unscaledTime >= _gpuiCheckAt) Instancer.Ensure(m.Cam);
        }
        if (Time.unscaledTime >= _gpuiCheckAt) _gpuiCheckAt = Time.unscaledTime + 1f;
        // Once in a while: the frame time with the mirrors running, to pick the quality.
        _sumDt += dt; _frames++;
        if (Time.unscaledTime >= _logAt && _frames > 0)
        {
            Plugin.Info($"mirrors ({Settings.MirrorQualityLevel.Value}): {_mirrors.Count} running, every {every} frame(s), " +
                        $"average frame {_sumDt / _frames * 1000f:0.0} ms over the last {_frames} frames");
            _sumDt = 0f; _frames = 0; _logAt = Time.unscaledTime + 30f;
        }
    }

    public static void Teardown()
    {
        foreach (var m in _mirrors)
        {
            try
            {
                if (m.Cam != null) UnityEngine.Object.Destroy(m.Cam.gameObject);
                if (m.Texture != null) { m.Texture.Release(); UnityEngine.Object.Destroy(m.Texture); }
            }
            catch (Exception e) { Plugin.ErrorOnce("mirror teardown", e); }
        }
        _mirrors.Clear();
    }
}
