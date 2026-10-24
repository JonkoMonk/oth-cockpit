using System.IO;

namespace OthCockpit;

// Where the mod keeps its files. Set by the loader entry point before anything else runs.
//   BepInEx:     BepInEx\config\jonkomonk.oth.cockpit.cfg  +  BepInEx\plugins\OthCockpit\ (models)
//   MelonLoader: UserData\OthCockpit\jonkomonk.oth.cockpit.cfg  +  UserData\OthCockpit\ (models)
internal static class ModPaths
{
    public static string Loader { get; private set; }
    public static string SettingsFile { get; private set; }
    public static string DataDir { get; private set; }     // models\ lives here
    public static string ModelDir => Path.Combine(DataDir, "models");

    public static void Init(string loader, string settingsDir, string dataDir)
    {
        Loader = loader;
        SettingsFile = Path.Combine(settingsDir, Plugin.Guid + ".cfg");
        DataDir = dataDir;
    }
}
