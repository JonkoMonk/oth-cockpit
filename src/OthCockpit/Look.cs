using System;
using UnityEngine;
using UnityEngine.InputSystem;
#if MELON
using Il2Cpp;
#endif

namespace OthCockpit;

// Head movement in the cockpit:
//  - looking around with the mouse, the controller's right stick or the game's camera keys
//    (CameraOrbitAndZoom.MoveCamera*); the head swings back to the front after a moment without input,
//  - looking into a corner: the head turns a little towards where you steer.
// The head turns about the neck (a bit behind and below the eyes), like a real one.
internal static class Look
{
    public static float Yaw, Pitch;           // degrees from straight ahead; pitch + = down
    static float _turn, _idle;
    static bool _loggedMouse, _loggedStick, _loggedKeys, _loggedWheel;
    static readonly Vector3 Neck = new(0f, -0.07f, -0.10f);   // from the eyes

    public static void Reset() { Yaw = Pitch = _turn = 0f; _idle = 0f; }

    // Returns the head rotation; eyeOffset = where the eyes end up relative to the standard eye point.
    public static Quaternion Update(float dt, out Vector3 eyeOffset)
    {
        Vector2 rate = Vector2.zero;   // degrees per second
        bool input = false;

        if (InputAllowed())
        {
            float sens = Settings.LookMouse.Value;
            if (sens > 0f)
            {
                var mouse = Mouse.current;
                var d = mouse != null ? mouse.delta.ReadValue() : Vector2.zero;
                if (d.sqrMagnitude > 0.5f)
                {
                    Yaw += d.x * sens;
                    Pitch -= d.y * sens;
                    input = true;
                    if (!_loggedMouse) { _loggedMouse = true; Plugin.Info("look: mouse input seen"); }
                }
            }
            float speed = Settings.LookSpeed.Value;
            var pad = Gamepad.current;
            var stick = pad != null ? pad.rightStick.ReadValue() : Vector2.zero;
            var keys = CameraKeys();
            if (stick.magnitude > 0.15f)
            {
                rate = stick * speed;
                if (!_loggedStick) { _loggedStick = true; Plugin.Info("look: right stick input seen"); }
            }
            else if (keys.magnitude > 0.15f)
            {
                rate = keys * speed;
                if (!_loggedKeys) { _loggedKeys = true; Plugin.Info($"look: game camera keys input seen {keys}"); }
            }
            // The wheel mod's camera buttons (Moza D-pad), already in look directions.
            var wheel = WheelLink.Look();
            if (wheel.magnitude > 0.1f)
            {
                rate = wheel * speed;
                if (!_loggedWheel) { _loggedWheel = true; Plugin.Info("look: wheel camera buttons seen"); }
            }
            if (rate != Vector2.zero)
            {
                Yaw += rate.x * dt;
                Pitch -= rate.y * dt;
                input = true;
            }
        }

        Yaw = Mathf.Clamp(Yaw, -150f, 150f);
        Pitch = Mathf.Clamp(Pitch, -45f, 50f);
        _idle = input ? 0f : _idle + dt;
        float back = Settings.LookReturn.Value;
        if (back > 0f && _idle > back)
        {
            float k = 1f - Mathf.Exp(-dt * 5f);
            Yaw -= Yaw * k;
            Pitch -= Pitch * k;
        }

        // Look into the corner (fades in from walking pace, so manoeuvring when parked stays calm).
        float into = Settings.LookIntoTurn.Value * Car.Steer * Mathf.Clamp01((Car.SpeedKmh - 3f) / 12f);
        _turn += (into - _turn) * (1f - Mathf.Exp(-dt * 3f));

        var rot = Quaternion.Euler(Settings.Pitch.Value + Pitch, Yaw + _turn, 0f);
        eyeOffset = -Neck + rot * Neck;   // the eyes swing round the neck
        return rot;
    }

    // Look input only while the game is driving (not in menus, the map, photo mode...).
    static bool InputAllowed()
    {
        try
        {
            var gi = GameInput.instance;
            return gi != null && gi.playerInputActions.Driving.enabled && Application.isFocused;
        }
        catch { return Application.isFocused; }
    }

    static Vector2 CameraKeys()
    {
        try
        {
            var cam = GameInput.instance.playerInputActions.CameraOrbitAndZoom;
            return new Vector2(cam.MoveCameraRight.ReadValue<float>() - cam.MoveCameraLeft.ReadValue<float>(),
                               cam.MoveCameraUp.ReadValue<float>() - cam.MoveCameraDown.ReadValue<float>());
        }
        catch { return Vector2.zero; }
    }
}
