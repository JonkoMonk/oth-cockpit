using System;
using System.IO;

namespace OthCockpit;

// Everything the player can tune lives in jonkomonk.oth.cockpit.cfg (folder: see ModPaths).
// The file is re-read automatically while the game runs, so edits apply within ~2 seconds.
internal static class Settings
{
    static ConfigFile _cfg;
    static DateTime _lastWrite;

    public static ConfigEntry<bool> Enabled, ShowData;
    public static ConfigEntry<string> ToggleKey, DumpKey;
    public static ConfigEntry<float> OffsetX, OffsetY, OffsetZ, Pitch, FieldOfView;
    public static ConfigEntry<float> LookMouse, LookSpeed, LookReturn, LookIntoTurn;
    public static ConfigEntry<float> EarsToCentre;

    public static void Bind(ConfigFile cfg)
    {
        _cfg = cfg;

        Enabled = cfg.Bind("General", "Enabled", true,
            "Master switch. false = the mod does nothing.");
        ShowData = cfg.Bind("General", "ShowData", false,
            "Show the car data (speed, rpm, gear, lights...) as text at the top left while in the cockpit. For testing.");
        ToggleKey = cfg.Bind("Keys", "Toggle", "F6",
            "Key to switch the cockpit view on and off (zooming in past the closest chase view works too). Not F3/F8: the wheel mod uses those.");
        DumpKey = cfg.Bind("Keys", "Dump", "F9", "Key to write details about the car (parts, materials, sizes) to the log.");

        OffsetX = cfg.Bind("Seat", "OffsetX", 0f,
            "Move your head away from the car's standard eye position, metres (numpad keys in the cockpit change these). X: right is +.");
        OffsetY = cfg.Bind("Seat", "OffsetY", 0f, "Y: up is +.");
        OffsetZ = cfg.Bind("Seat", "OffsetZ", 0f, "Z: forward is +.");
        Pitch = cfg.Bind("Seat", "Pitch", 6f, "Look down by this many degrees.");
        FieldOfView = cfg.Bind("Seat", "FieldOfView", 85f, "Vertical field of view in degrees.");

        LookMouse = cfg.Bind("Look", "Mouse", 0.12f, "Look around with the mouse: degrees per mouse step. 0 = off.");
        LookSpeed = cfg.Bind("Look", "Speed", 140f,
            "Look around with the right stick or the game's camera keys: degrees per second at full tilt.");
        LookReturn = cfg.Bind("Look", "ReturnAfter", 1.5f,
            "Seconds without look input before the head turns back to the front. 0 = stay where you looked.");
        LookIntoTurn = cfg.Bind("Look", "IntoTurn", 30f,
            "Turn the head towards where you steer, degrees at full steering lock (from about 15 km/h). 0 = off.");

        EarsToCentre = cfg.Bind("Sound", "EarsToCentre", 0.7f,
            "In the cockpit, hear from this far towards the middle of the car (0 = from your seat, like the game: the car " +
            "then sounds almost only on one side; 1 = right in the middle: the same in both ears).");

        _lastWrite = File.Exists(cfg.ConfigFilePath) ? File.GetLastWriteTimeUtc(cfg.ConfigFilePath) : DateTime.MinValue;
    }

    // True when the file was edited outside the game and has been re-read.
    public static bool ReloadIfChanged()
    {
        var path = _cfg.ConfigFilePath;
        if (!File.Exists(path)) { _cfg.Save(); _lastWrite = File.GetLastWriteTimeUtc(path); return false; }
        var t = File.GetLastWriteTimeUtc(path);
        if (t == _lastWrite) return false;
        _lastWrite = t;
        _cfg.Reload();
        return true;
    }

    // After the mod itself changed a value (seat nudge keys): don't treat our own save as an outside edit.
    public static void Saved()
    {
        var path = _cfg.ConfigFilePath;
        if (File.Exists(path)) _lastWrite = File.GetLastWriteTimeUtc(path);
    }
}
