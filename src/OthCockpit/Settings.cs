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
    public enum MirrorQuality { Low, Medium, High, Ultra, Custom }
    public enum RearViewMode { Auto, Car, Road }
    public static ConfigEntry<bool> MirrorsOn, SideMirrors;
    public static ConfigEntry<MirrorQuality> MirrorQualityLevel;
    public static ConfigEntry<RearViewMode> RearView;
    public static ConfigEntry<float> MirrorResolution, MirrorUpdateEvery, RearViewTilt, MirrorWide, RearViewSize;

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

        MirrorsOn = cfg.Bind("Mirrors", "Enabled", true,
            "Working mirrors: the rear-view mirror and the car's side mirrors show what's behind you. Each mirror is one more " +
            "picture of the world per frame, so they cost some frame rate. false = plain mirrors.");
        MirrorQualityLevel = cfg.Bind("Mirrors", "Quality", MirrorQuality.Medium,
            "How good the mirrors look, and how much frame rate they cost. Low = only the rear-view mirror, blurry, not every " +
            "frame (slow PCs); Medium = all mirrors, sharp enough, every other frame; High = sharper, how far you see doubles; " +
            "Ultra = sharpest, every frame, shadows (fast PCs). Custom = the three settings below.");
        RearView = cfg.Bind("Mirrors", "RearView", RearViewMode.Auto,
            "What the rear-view mirror shows. Car = like in a real car: the cabin and out through the rear window. " +
            "Road = only the road behind the car. Auto = Road (the default).");
        RearViewTilt = cfg.Bind("Mirrors", "RearViewTilt", -3f,
            "Where the rear-view mirror's road view points, degrees: 0 = level with the horizon in the middle, negative = more road, positive = more sky.");
        // A real flat mirror shows a sliver of the world: realistic, but too little to use (JonkoMonk, 2026-11-07).
        MirrorWide = cfg.Bind("Mirrors", "WideAngle", 2.2f,
            "How much the mirrors show, like a convex wide-angle mirror: 1 = a real flat mirror (realistic, shows little), " +
            "2.2 = about twice as much (default), up to 3.");
        RearViewSize = cfg.Bind("Mirrors", "RearViewSize", 1.5f,
            "Size of the rear-view mirror: 1 = the model's real size, 1.5 = half as big again (default), up to 2. " +
            "Bigger shows a bigger picture but hides more of the windscreen.");
        SideMirrors = cfg.Bind("Mirrors", "SideMirrors", true, "(Custom quality) Also the outside mirrors (false = only the rear-view mirror: cheaper).");
        MirrorResolution = cfg.Bind("Mirrors", "Resolution", 1f,
            "(Custom quality) Sharpness of the mirror pictures: 1 = normal, 0.5 = half (faster), 2 = double.");
        MirrorUpdateEvery = cfg.Bind("Mirrors", "UpdateEvery", 2f,
            "(Custom quality) Draw each mirror every this many frames (1 = every frame: smoothest, slowest; 2 = every other frame, the mirrors take turns).");

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
