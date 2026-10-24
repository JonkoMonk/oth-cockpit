# OTH Cockpit (alpha): first-person view from the driver's seat in *over the hill*

Sit **inside** your car in **over the hill** (Funselektor, Steam): a first-person view with a real interior in the game's low-poly style. Working dials (speed, revs, fuel, outside temperature), warning lights, a gear display, and a steering wheel, pedals and levers that move with your input. Painted parts take your car's livery, dust and mud. Every car in the game has a cockpit.

Watch it in action: [mod spotlight video](https://youtu.be/rHvPhiTygKQ). Download: [OTH Cockpit on Nexus Mods](https://www.nexusmods.com/overthehill/mods/90).

Works with keyboard, controller or steering wheel. With [OTH Wheel](https://github.com/JonkoMonk/oth-wheel) ([Nexus Mods](https://www.nexusmods.com/overthehill/mods/83)) the cockpit's steering wheel turns exactly like your real one.

**Alpha:** many cars still have rough spots: parts in the wrong place, dials partly hidden behind the wheel, and small visual glitches around the windscreen pillars and window frames (the TrailBurner and Protector, for example). We're working on it. Screenshots of what looks wrong are very welcome in the Issues.

## Download and install

From [Nexus Mods](https://www.nexusmods.com/overthehill/mods/90) or the [Releases](../../releases) page: `OTH-Cockpit-v…-alpha.zip`, or `OTH-Wheel-and-Cockpit-v….zip` for both mods.

1. Close the game and extract the zip.
2. Double-click `Install.bat` and follow the pop-ups. It finds the game, installs MelonLoader if you have no mod loader (or uses your BepInEx), and never changes original game files.
3. Start the game (the first start takes 1–2 minutes), get in a car and press **F6**, or zoom the camera all the way in and then once more.

Uninstall: `Uninstall.bat`. The installer lives in the OTH Wheel repository; both mods share it.

## How to use

- **Get in / out:** F6, or zoom in past the closest chase view / zoom out.
- **Look around:** mouse or gamepad right stick; the head turns back to the front by itself and leans into corners a bit.
- **Seat:** numpad 8/2, 4/6, 9/3 move it; 7/1 tilt the view; +/- zoom.
- Settings: `UserData\OthCockpit\jonkomonk.oth.cockpit.cfg` (MelonLoader) or `BepInEx\config\jonkomonk.oth.cockpit.cfg`, re-read while the game runs.

## How it's made

- `src/` is the mod (C#, net6.0, MelonLoader and BepInEx from one code base). It reads each car's cockpit from a `.glb` model with its own small glTF reader, builds Unity meshes with the car's own paint shader, and moves needles, lamps and levers from the car's data.
- `blender/` holds the Blender scripts that build the cockpits (`build_car_v2.py` with the per-car character in `cars_v2.py`, shared parts in `kit.py` / `styles_v2.py` / `signatures_v2.py`, dial faces from `dials_v2style.py`). They measure each car's body with rays so the interior fits it.
- `tools/` exports the car bodies from your own game install as a modelling reference (`export_all.py`, run with Python and UnityPy). No game files are in this repository.

Build the models: `blender -b --factory-startup -P blender/build_car_v2.py -- <assets folder> <exported cars folder> <Car>`. Build the mod: `build.ps1 -NoModels` (references the game's generated interop assemblies; paths in `src/Directory.Build.props`).

All the code and models were made by Claude (Anthropic's AI) in conversations with JonkoMonk, who designed, tested and decided how it should look.

## Licence

MIT, see [LICENSE](LICENSE).
