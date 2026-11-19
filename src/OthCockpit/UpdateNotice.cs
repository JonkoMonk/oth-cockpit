using System.Collections.Generic;

namespace OthCockpit;

// Update notice in the cockpit mod. With OTH Wheel 1.2.0+ installed, the wheel mod shows one message for both
// mods (we hand our result over through WheelLink). Without it (or with an older one) we show our own,
// once per game start, on a menu screen. The log always has the result.
internal static class UpdateNotice
{
    public const string NexusPage = "https://www.nexusmods.com/overthehill/mods/90";
    const string Footer = "Nothing is downloaded by itself: install it like the last one (Install.bat updates and keeps your settings). " +
                          "No more checks: [Updates] Check = false in the cockpit's settings file.";

    static bool _shown, _open, _byWheel;

    public static void Start() => UpdateCheck.Start(Plugin.Name, Plugin.Version, "JonkoMonk/oth-cockpit", NexusPage);

    public static void Update(float now)
    {
        UpdateCheck.Tick();
        bool byWheel = WheelLink.ShareUpdate(UpdateCheck.Newer, UpdateCheck.Done, UpdateCheck.WantsPopup);
        if (byWheel != _byWheel)
        {
            _byWheel = byWheel;
            if (byWheel) Plugin.Info("update notice: OTH Wheel shows it (one message for both mods)");
        }
        string ticked = WheelLink.TakeDontShow();
        if (ticked != null)
        {
            UpdateCheck.DontShowFor.Value = ticked;
            Settings.Saved();
            Plugin.Info($"update notice: 'Don't show this again' ticked for {ticked} (in OTH Wheel's message)");
        }
    }

    public static void OnGUI(float now)
    {
        UpdatePopup.Idle();
        if (_byWheel || !WheelLink.Searched) return;
        var newer = UpdateCheck.Newer;
        if (newer == null) return;
        bool canShow = UpdatePopup.OnMenuScreen(now);
        if (!_open)
        {
            if (_shown || !UpdateCheck.WantsPopup || !canShow) return;
            _shown = _open = true;
            Plugin.Info($"update notice: shown ({newer.Mod} {newer.Latest})");
        }
        // Stays until closed; hidden while not on a menu screen (it comes back there).
        if (!canShow) return;
        if (!UpdatePopup.Draw(new List<UpdateCheck.Found> { newer }, Footer, out bool dontShow)) return;
        _open = false;
        if (dontShow) { UpdateCheck.DontShowFor.Value = newer.Latest; Settings.Saved(); }
        Plugin.Info($"update notice: closed{(dontShow ? ", 'Don't show this again' ticked" : "")}");
    }
}
