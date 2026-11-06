using System;
using System.Collections.Generic;
using UnityEngine;
#if MELON
using Il2CppGPUInstancerPro;
#else
using GPUInstancerPro;
#endif

namespace OthCockpit;

// The game draws its trees, grass and rocks with GPU Instancer Pro, which draws only for the cameras in its
// own camera list (the mirrors showed no trees). Each mirror camera gets a GPUICamera component (that puts it
// on the list), and Ensure() checks now and then that it is still on it (cameras that are switched off can be
// dropped). Its occlusion culling stays off: it would judge each mirror by that mirror's previous picture.
// Same approach as the VR mod's eye cameras.
internal static class Instancer
{
    static readonly HashSet<int> _logged = new();

    public static void AddComponent(GameObject go)
    {
        try
        {
            var gpui = go.AddComponent<GPUICamera>();
            gpui._enableOcclusionCulling = false;
        }
        catch (Exception e) { Plugin.Warn($"GPU Instancer camera not added to {go.name} ({e.Message})"); }
    }

    public static void Ensure(Camera cam)
    {
        try
        {
            var rs = GPUIRenderingSystem.Instance;
            var provider = rs != null ? rs.CameraDataProvider : null;
            if (provider == null) return;
            int id = cam.GetInstanceID();
            rs._ignoreCameraIIDCollection?.Remove(id);
            if (provider.ContainsKey(id)) return;
            provider.AddCamera(cam);
            if (_logged.Add(id)) Plugin.Info($"GPU Instancer: {cam.name} added to its camera list (trees in the mirror)");
        }
        catch (Exception e) { Plugin.ErrorOnce("gpui ensure", e); }
    }
}
