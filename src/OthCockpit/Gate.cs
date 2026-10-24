using UnityEngine;
#if MELON
using Il2Cpp;
#endif

namespace OthCockpit;

// When the cockpit may show: only while the game is actually driving (not in menus, the map, camp,
// photo mode, cutscenes or on foot), and how the game's zoom asks for the cockpit.
internal static class Gate
{
    static ExtraCameraControls _zoom;
    static float _nextZoomSearch, _lastTarget = float.NaN;

    public static bool Driving()
    {
        try
        {
            var gi = GameInput.instance;
            if (gi != null && !gi.playerInputActions.Driving.enabled) return false;
        }
        catch { }
        try
        {
            var cvm = ControllerVibrationManager.Instance;
            if (cvm != null && cvm.pauseMenuOpen) return false;
        }
        catch { }
        return true;
    }

    // Zooming in once more while the chase camera is already as close as it goes (mouse wheel, D-pad,
    // or the wheel mod's zoom buttons) asks for the cockpit; zooming out leaves it.
    public static bool ZoomInPastClosest()
    {
        try
        {
            var zoom = Zoom();
            if (zoom == null) return false;
            bool wasClosest = !float.IsNaN(_lastTarget) && _lastTarget <= zoom.minZoom + 0.01f;
            _lastTarget = zoom.targetZoomMultiplier;
            return wasClosest && GameInput.instance.playerInputActions.CameraOrbitAndZoom.CameraZoomIn.WasPressedThisFrame();
        }
        catch { return false; }
    }

    public static bool ZoomOut()
    {
        try { return GameInput.instance.playerInputActions.CameraOrbitAndZoom.CameraZoomOut.WasPressedThisFrame(); }
        catch { return false; }
    }

    static ExtraCameraControls Zoom()
    {
        if (_zoom != null || Time.unscaledTime < _nextZoomSearch) return _zoom;
        _nextZoomSearch = Time.unscaledTime + 2f;
#pragma warning disable CS0618
        _zoom = Object.FindObjectOfType<ExtraCameraControls>();
#pragma warning restore CS0618
        return _zoom;
    }
}
