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
    static FieldInfo _active, _degrees, _lookX, _lookY, _toggles, _cockpitActive, _cockpitInstalled, _intoTurn, _intoTurnSet;
    static FieldInfo _wheelShows, _upChecked, _upLatest, _upInstalled, _upWhatsNew, _upUrl, _upPopup, _upDontShow;
    static string _upShared;
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

    // The F3 menu's "Cockpit: look into turns" (wheel mod 1.2.0+): shows our value, and a change made there
    // comes back as a request. Returns the new value when the menu changed it, else null.
    public static float? SyncIntoTurn(float current)
    {
        Find();
        if (_intoTurn == null || _intoTurnSet == null) return null;
        try
        {
            float want = (float)_intoTurnSet.GetValue(null);
            if (want >= 0f) { _intoTurnSet.SetValue(null, -1f); _intoTurn.SetValue(null, want); return want; }
            if ((float)_intoTurn.GetValue(null) != current) _intoTurn.SetValue(null, current);
        }
        catch { }
        return null;
    }

    // Update notice (wheel mod 1.2.0+, link v4): hands our update check's result to the wheel mod, which shows
    // one message for both mods. True = the wheel mod shows it (we show no message of our own).
    public static bool ShareUpdate(UpdateCheck.Found newer, bool done, bool popup)
    {
        Find();
        if (_wheelShows == null || _upChecked == null || _upLatest == null || _upPopup == null || _upDontShow == null) return false;
        try
        {
            if (!(bool)_wheelShows.GetValue(null)) return false;
            string state = $"{done}|{newer?.Latest}|{popup}";
            if (state != _upShared)
            {
                if (newer != null)
                {
                    _upInstalled?.SetValue(null, newer.Installed);
                    _upWhatsNew?.SetValue(null, newer.WhatsNew);
                    _upUrl?.SetValue(null, newer.Url);
                }
                _upPopup.SetValue(null, popup);
                _upLatest.SetValue(null, newer?.Latest);
                _upChecked.SetValue(null, done);
                _upShared = state;
            }
            return true;
        }
        catch { return false; }
    }

    // "Don't show this again" ticked in the wheel mod's message for this cockpit version (once, else null).
    public static string TakeDontShow()
    {
        if (_upDontShow == null) return null;
        try
        {
            var v = (string)_upDontShow.GetValue(null);
            if (v != null) _upDontShow.SetValue(null, null);
            return v;
        }
        catch { return null; }
    }

    // True once the wheel mod's link was looked for (found or not), so the cockpit knows whether to show its own message.
    public static bool Searched => _active != null || _logged;

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
            // Version 3 and up: the cockpit's "look into turns" in the wheel mod's F3 menu (Camera page).
            _intoTurn = Field(t, "CockpitIntoTurn", typeof(float));
            _intoTurnSet = Field(t, "CockpitIntoTurnSet", typeof(float));
            // Version 4 and up: one update message for both mods, shown by the wheel mod.
            _wheelShows = Field(t, "WheelShowsUpdates", typeof(bool));
            _upChecked = Field(t, "CockpitUpdateChecked", typeof(bool));
            _upLatest = Field(t, "CockpitUpdateLatest", typeof(string));
            _upInstalled = Field(t, "CockpitUpdateInstalled", typeof(string));
            _upWhatsNew = Field(t, "CockpitUpdateWhatsNew", typeof(string));
            _upUrl = Field(t, "CockpitUpdateUrl", typeof(string));
            _upPopup = Field(t, "CockpitUpdatePopup", typeof(bool));
            _upDontShow = Field(t, "CockpitUpdateDontShow", typeof(string));
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
