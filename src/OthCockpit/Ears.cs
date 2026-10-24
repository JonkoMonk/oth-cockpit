using System;
using UnityEngine;
#if MELON
using Il2CppFMODUnity;
#else
using FMODUnity;
#endif

namespace OthCockpit;

// The game hears through an FMOD StudioListener on its camera, so in the cockpit you hear from the
// driver's head, 40 cm beside the middle of the car. The car's own sounds come from its middle, low
// down (engine) and from the wheels, and that close they ended up almost only in the right ear (left
// in right-hand drive cars). While the cockpit is shown our own listener takes over at your head,
// moved [Sound] EarsToCentre of the way towards the middle of the car: still a little from the side,
// but in both ears. The game's listener is paused (its settings copied) and back when you leave.
// The OTH VR mod has its own listener at your VR head ("OthVr Ears", it does the same shift); while
// that one is on, ours steps aside and leaves the game's listener to it.
internal static class Ears
{
    const string VrEarsName = "OthVr Ears";
    static GameObject _go;
    static StudioListener _ours, _game;
    static GameObject _vrEars;
    static float _nextVrSearch;

    public static void Follow(Transform car, Transform head)
    {
        float centre = Mathf.Clamp01(Settings.EarsToCentre.Value);
        if (centre <= 0f) { Restore(); return; }
        if (VrEarsOn()) { StepAside(); return; }
        try
        {
            var main = Camera.main;
            var game = main != null ? main.GetComponent<StudioListener>() : null;
            if (game == null) return;
            if (game != _game) Restore();
            if (_go == null)
            {
                _go = new GameObject("OthCockpit Ears");
                UnityEngine.Object.DontDestroyOnLoad(_go);
                _go.SetActive(false);
                _ours = _go.AddComponent<StudioListener>();
            }
            var local = car.InverseTransformPoint(head.position);
            local.x *= 1f - centre;
            _go.transform.SetPositionAndRotation(car.TransformPoint(local), head.rotation);
            if (_game == null)
            {
                _game = game;
                _ours.attenuationObject = game.attenuationObject;
                _ours.nonRigidbodyVelocity = game.nonRigidbodyVelocity;
                game.enabled = false;
                _go.SetActive(true);
                Plugin.Info($"sound: listening from the cockpit seat, {centre * 100f:0}% towards the middle of the car (game listener paused)");
            }
        }
        catch (Exception e) { Plugin.ErrorOnce("ears", e); Restore(); }
    }

    public static void Restore()
    {
        try
        {
            if (_go != null && _go.activeSelf) _go.SetActive(false);
            if (_game != null) _game.enabled = true;
        }
        catch (Exception e) { Plugin.ErrorOnce("ears restore", e); }
        _game = null;
    }

    // The VR mod's listener took over: drop ours without switching the game's back on (VR holds it
    // paused and restores it itself).
    static void StepAside()
    {
        try { if (_go != null && _go.activeSelf) _go.SetActive(false); }
        catch (Exception e) { Plugin.ErrorOnce("ears step aside", e); }
        _game = null;
    }

    static bool VrEarsOn()
    {
        if (_vrEars == null)
        {
            if (Time.unscaledTime < _nextVrSearch) return false;
            _nextVrSearch = Time.unscaledTime + 1f;
            _vrEars = GameObject.Find(VrEarsName);   // finds active objects only
            if (_vrEars == null) return false;
        }
        return _vrEars.activeInHierarchy;
    }
}
