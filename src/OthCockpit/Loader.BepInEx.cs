using System.IO;
using BepInEx;
using BepInEx.Unity.IL2CPP;

namespace OthCockpit;

// BepInEx 6 (IL2CPP) entry point. Builds OthCockpit.dll for BepInEx\plugins\.
[BepInPlugin(Plugin.Guid, Plugin.Name, Plugin.Version)]
public class BepInExEntry : BasePlugin
{
    public override void Load()
    {
        Plugin.SetLog(s => Log.LogInfo(s), s => Log.LogWarning(s), s => Log.LogError(s));
        ModPaths.Init("BepInEx", Paths.ConfigPath, Path.Combine(Paths.PluginPath, "OthCockpit"));
        Plugin.Start();
        AddComponent<CockpitBehaviour>();
        Plugin.Info($"loaded under BepInEx, enabled={Settings.Enabled.Value}, models in {ModPaths.ModelDir}");
    }
}
