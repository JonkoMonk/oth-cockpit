using System;
using System.Reflection;
using UnityEngine;

namespace OthCockpit;

// Bridge to the OTH Wheel mod through its public static class OthWheel.CockpitLink:
//  - the real steering wheel's angle, so the cockpit wheel turns 1:1 with it,
//  - its camera buttons (look around) and its "cockpit view" button,
//  - and back to it: whether the cockpit is on, so its camera buttons stop moving the chase camera.
// Found by name at runtime, so neither mod needs the other: without the wheel mod the cockpit wheel
// follows the game's steering and the mouse/stick/keys do the looking.
internal static class WheelLink
{
    const string TypeName = "OthWheel.CockpitLink";
    const BindingFlags Static = BindingFlags.Public | BindingFlags.Static;
    static FieldInfo _active, _degrees, _lookX, _lookY, _toggles, _cockpitActive, _cockpitInstalled;
    static float _nextSearch;
    static bool _logged, _lastCockpitActive;
    static int _lastToggles = int.MinValue;

    // The real wheel's angle from centre in degrees (+ = right), when a wheel is connected and set up.
    public static bool TryAngle(out float degrees)
    {
        degrees = 0f;
        Find();
        if (_active == null) return false;
        try
        {
            if (!(bool)_active.GetValue(null)) return false;
            degrees = (float)_degrees.GetValue(null);
            return true;
        }
        catch { return false; }
    }

    // The wheel's camera buttons: x + = look right, y + = look up.
    public static Vector2 Look()
    {
        if (_lookX == null || _lookY == null) return Vector2.zero;
        try { return new Vector2((float)_lookX.GetValue(null), (float)_lookY.GetValue(null)); }
        catch { return Vector2.zero; }
    }

    // True once per press of the wheel's "cockpit view" button.
    public static bool TogglePressed()
    {
        Find();
        if (_toggles == null) return false;
        try
        {
            int n = (int)_toggles.GetValue(null);
            bool pressed = _lastToggles != int.MinValue && n != _lastToggles;
            _lastToggles = n;
            return pressed;
        }
        catch { return false; }
    }

    // Tell the wheel mod whether the cockpit is on (its camera buttons then look around here).
    public static void SetCockpitActive(bool on)
    {
        if (_cockpitActive == null || on == _lastCockpitActive) return;
        try { _cockpitActive.SetValue(null, on); _lastCockpitActive = on; } catch { }
    }

    static void Find()
    {
        if (_active != null || Time.unscaledTime < _nextSearch) return;
        _nextSearch = Time.unscaledTime + 5f;
        // Only our own assemblies by name (the wheel mod learned the hard way: never enumerate all types).
        foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
        {
            if (!asm.GetName().Name.StartsWith("OthWheel", StringComparison.Ordinal)) continue;
            var t = asm.GetType(TypeName);
            if (t == null) continue;
            var active = t.GetField("Active", Static);
            var degrees = t.GetField("WheelDegrees", Static);
            if (active == null || degrees == null || active.FieldType != typeof(bool) || degrees.FieldType != typeof(float)) continue;
            _active = active;
            _degrees = degrees;
            // Version 2 and up: camera buttons, cockpit button, cockpit state.
            _lookX = Field(t, "LookX", typeof(float));
            _lookY = Field(t, "LookY", typeof(float));
            _toggles = Field(t, "CockpitToggles", typeof(int));
            _cockpitActive = Field(t, "CockpitActive", typeof(bool));
            _cockpitInstalled = Field(t, "CockpitInstalled", typeof(bool));
            try { _cockpitInstalled?.SetValue(null, true); } catch { }
            var version = t.GetField("Version", Static);
            Plugin.Info($"wheel mod found ({asm.GetName().Name}, link v{version?.GetValue(null) ?? "?"}): cockpit wheel turns with the real one" +
                        (_toggles != null ? ", wheel buttons look around and switch the cockpit" : ""));
            return;
        }
        if (!_logged) { _logged = true; Plugin.Info("wheel mod link not found (fine without the wheel mod): the cockpit wheel follows the game's steering"); }
    }

    static FieldInfo Field(Type t, string name, Type type)
    {
        var f = t.GetField(name, Static);
        return f != null && f.FieldType == type ? f : null;
    }
}
