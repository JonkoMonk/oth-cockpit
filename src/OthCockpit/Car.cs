using System;
using UnityEngine;
#if MELON
using Il2Cpp;   // MelonLoader puts the game's namespace-less classes here
using Il2CppVehiclePhysics;
using Il2CppDistantLands.Cozy;
#else
using VehiclePhysics;
using DistantLands.Cozy;
#endif

namespace OthCockpit;

// The local player's car and everything the dials show. Each value is read on its own, so one
// missing piece (e.g. a networked property before the car has spawned) doesn't hide the rest.
internal static class Car
{
    public static VehicleInput Input { get; private set; }
    public static VPVehicleController Vehicle { get; private set; }
    public static NetworkedVehicleStatus Status { get; private set; }
    public static LightsController Lights { get; private set; }
    public static Transform Root => Input != null ? Input.transform : null;
    public static string Name => Input != null ? Input.gameObject.name.Replace("(Clone)", "").Trim() : "";

    // Live values, refreshed by Update().
    public static float SpeedKmh, Rpm, MaxRpm, IdleRpm, Steer, Throttle, Brake, Clutch, FuelRate;
    public static int Gear;
    public static bool Handbrake, LowRange, Headlights, EngineRunning;
    public static float OutsideTempC = float.NaN;   // the game's weather keeps Fahrenheit

    // The game has no fuel tank, so the gauge shows a pretend one: full at the start of each drive,
    // emptied by the engine's real fuel use (VPP's fuel rate, grams per second).
    public const float TankGrams = 40000f;
    public static float Fuel = 1f;

    static float _nextSearch;

    // True while we have a car. Looks for one at most every 2 s.
    public static bool Find(float now)
    {
        if (Input != null && Input.gameObject != null && Input.gameObject.activeInHierarchy) return true;
        if (Input != null) { Plugin.Info("car gone"); Input = null; Vehicle = null; Status = null; Lights = null; }
        if (now < _nextSearch) return false;
        _nextSearch = now + 2f;
#pragma warning disable CS0618   // FindObjectsOfType is old but present in this Unity build
        foreach (var vi in UnityEngine.Object.FindObjectsOfType<VehicleInput>())
#pragma warning restore CS0618
        {
            bool mine;
            try { mine = vi.HasInputAuthority; } catch { continue; }   // not spawned yet
            if (!mine) continue;
            Input = vi;
            Vehicle = vi.GetComponent<VPVehicleController>();
            Status = vi.GetComponentInChildren<NetworkedVehicleStatus>();
            Lights = FindLights(vi);
            Fuel = 1f;
            MaxRpm = IdleRpm = 0;
            try { MaxRpm = Vehicle.engine.maxRpm; IdleRpm = Vehicle.engine.idleRpm; } catch { }
            Plugin.Info($"car found: {Name} (vehicle {(Vehicle != null)}, status {(Status != null)}, lights {(Lights != null)}, idle {IdleRpm:0} max {MaxRpm:0} rpm)");
            return true;
        }
        return false;
    }

    // The lights controller isn't below the car object: look in its parents, then among all of them for ours.
    static LightsController FindLights(VehicleInput vi)
    {
        var l = vi.GetComponentInChildren<LightsController>() ?? vi.GetComponentInParent<LightsController>();
        if (l != null) return l;
#pragma warning disable CS0618
        var all = UnityEngine.Object.FindObjectsOfType<LightsController>();
#pragma warning restore CS0618
        LightsController notOther = null;
        foreach (var c in all)
        {
            var t = c.transform;
            if (t.IsChildOf(vi.transform) || vi.transform.IsChildOf(t) || t.root == vi.transform.root) return c;
            try { if (!c.isOtherCar) notOther = c; } catch { }
        }
        Plugin.Info($"lights: {all.Length} controllers in the scene, none in our car's hierarchy; using {(notOther != null ? notOther.name : "none")}");
        return notOther;
    }

    public static void Update()
    {
        if (Input == null) return;
        try
        {
            var rb = Vehicle != null ? Vehicle.cachedRigidbody : null;
            SpeedKmh = rb != null ? rb.velocity.magnitude * 3.6f : 0f;
        }
        catch { }
        try
        {
            var d = Vehicle.data;
            int input = Channel.Input, veh = Channel.Vehicle;
            Steer = d.Get(input, InputData.Steer) / 10000f;
            Throttle = d.Get(input, InputData.Throttle) / 10000f;
            Brake = d.Get(input, InputData.Brake) / 10000f;
            Clutch = d.Get(input, InputData.Clutch) / 10000f;
            Rpm = d.Get(veh, VehicleData.EngineRpm) / 1000f;
            FuelRate = d.Get(veh, VehicleData.EngineFuelRate) / 1000f;
        }
        catch { }
        Fuel = Mathf.Clamp01(Fuel - FuelRate * Time.deltaTime / TankGrams);
        if (Status != null)
        {
            try { Gear = Status.GearboxGear; } catch { }
            try { Handbrake = Status.HandbrakeSet; } catch { }
            try { LowRange = Status.GearboxIsLowTransferCase; } catch { }
            try { EngineRunning = Status.EngineRunning; } catch { }
        }
        // The car's own input object knows the headlight switch; the lights controller is a fallback.
        try { Headlights = Input.HeadlightsOn; }
        catch { if (Lights != null) try { Headlights = Lights.AreHeadlightsOn; } catch { } }
        try
        {
            var w = CozyWeather.instance;
            var c = w != null ? w.climateModule : null;
            OutsideTempC = c != null ? (c.currentTemperature - 32f) * 5f / 9f : float.NaN;
        }
        catch { OutsideTempC = float.NaN; }
    }

    public static string Describe() =>
        $"{Name}  {SpeedKmh:0} km/h  {Rpm:0}/{MaxRpm:0} rpm  gear {Gear}{(LowRange ? " LOW" : "")}  " +
        $"handbrake {(Handbrake ? "ON" : "off")}  lights {(Headlights ? "ON" : "off")}  " +
        $"engine {(EngineRunning ? "running" : "off")}  steer {Steer:0.00} thr {Throttle:0.00} brk {Brake:0.00} clu {Clutch:0.00}  " +
        $"fuel {Fuel * 100:0}% ({FuelRate:0.00} g/s)  outside {OutsideTempC:0} °C";
}
