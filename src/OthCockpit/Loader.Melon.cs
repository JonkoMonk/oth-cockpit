using System.IO;
using Il2CppInterop.Runtime.Injection;
using MelonLoader;
using MelonLoader.Utils;
using UnityEngine;

[assembly: MelonInfo(typeof(OthCockpit.MelonEntry), OthCockpit.Plugin.Name, OthCockpit.Plugin.Version, OthCockpit.Plugin.Author)]
[assembly: MelonGame("Funselektor", "over the hill")]

namespace OthCockpit;

// MelonLoader 0.7 entry point. Builds OthCockpit.Melon.dll for Mods\.
public class MelonEntry : MelonMod
{
    public override void OnInitializeMelon()
    {
        var log = LoggerInstance;
        Plugin.SetLog(s => log.Msg(s), s => log.Warning(s), s => log.Error(s));
        var dataDir = Path.Combine(MelonEnvironment.UserDataDirectory, "OthCockpit");
        ModPaths.Init("MelonLoader", dataDir, dataDir);
        Plugin.Start();
    }

    // Unity objects only once the engine is fully up.
    public override void OnLateInitializeMelon()
    {
        ClassInjector.RegisterTypeInIl2Cpp<CockpitBehaviour>();
        var go = new GameObject("OthCockpit");
        Object.DontDestroyOnLoad(go);
        go.hideFlags = HideFlags.HideAndDontSave;
        go.AddComponent<CockpitBehaviour>();
        Plugin.Info($"loaded under MelonLoader, enabled={Settings.Enabled.Value}, models in {ModPaths.ModelDir}");
    }
}
