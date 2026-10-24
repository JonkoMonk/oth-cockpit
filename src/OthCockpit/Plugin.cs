using System;
using System.Collections.Generic;

namespace OthCockpit;

// First-person cockpit view for over the hill: a low-poly interior with working dials,
// loaded at runtime from .glb models made in Blender.
// Loader-independent core. The BepInEx and MelonLoader entry points (Loader.*.cs) set up paths
// and logging, call Start, then put CockpitBehaviour on a GameObject.
public static class Plugin
{
    public const string Guid = "jonkomonk.oth.cockpit", Name = "OTH Cockpit", Version = "0.3.0", Author = "JonkoMonk";

    static Action<string> _info = Console.WriteLine, _warn = Console.WriteLine, _error = Console.WriteLine;
    static readonly HashSet<string> _reported = new();

    public static void SetLog(Action<string> info, Action<string> warn, Action<string> error)
    {
        _info = info; _warn = warn; _error = error;
    }

    public static void Start()
    {
        Settings.Bind(new ConfigFile(ModPaths.SettingsFile));
    }

    public static void Info(string s) => _info(s);
    public static void Warn(string s) => _warn(s);
    public static void Error(string s) => _error(s);

    // Update runs every frame; report each kind of failure only once instead of flooding the log.
    public static void ErrorOnce(string where, Exception e)
    {
        lock (_reported)
            if (!_reported.Add(where)) return;
        _error($"{where}: {e.GetType().Name}: {e.Message}\n{e.StackTrace}");
    }
}
