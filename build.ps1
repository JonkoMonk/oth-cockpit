# Builds the cockpit mod and its models (all output outside OneDrive) and installs them into every game
# folder that runs the matching loader (the real game and the test copies), like the wheel mod's build.ps1.
#   1. Blender: the v2 cockpit models (blender\build_car_v2.py, every car of blender\cars_v2.py)
#      -> %USERPROFILE%\dev\oth-cockpit-build\assets_v2 (the dial pictures must be there: blender\dials.py makes
#      lamps.png + gears.png, blender\dials_v2style.py the v2 dials; each runs only if its pictures are missing).
#      The model scripts use the car body exported from the game (tools\export_car.py) in %USERPROFILE%\dev\oth-cockpit-build\cars\<car>.
#   2. dotnet:  OthCockpit.Melon.dll (MelonLoader) and OthCockpit.dll (BepInEx, references from %USERPROFILE%\dev\oth-bep-test\game)
#   3. Install: MelonLoader -> Mods\OthCockpit.Melon.dll + UserData\OthCockpit\models\Car_*.glb
#               BepInEx     -> BepInEx\plugins\OthCockpit.dll + BepInEx\plugins\OthCockpit\models\Car_*.glb
#      The models already in a game folder are copied to %USERPROFILE%\dev\oth-cockpit-build\backup_models_<date>\ first
#      (once a day per folder).
# Usage: powershell -File build.ps1 [-NoModels] [-NoInstall] [-Cars DingDing,Burro]   (-Cars: names from cars_v2.py)
# (The old v1 builders, build_car.py / build_dingding.py / build_protector.py, are no longer run.)
param(
    [switch]$NoModels,
    [switch]$NoInstall,
    [string[]]$Cars
)
$ErrorActionPreference = "Stop"
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
$root = "$env:USERPROFILE\dev\oth-cockpit-build"
$assets = "$root\assets_v2"
$blender = "$env:USERPROFILE\dev\tools\blender\blender.exe"

function Blender([string]$script, [string[]]$scriptArgs) {
    & $blender -b --factory-startup -P (Join-Path $PSScriptRoot "blender\$script") -- @scriptArgs | Select-String -Pattern "wrote|Error|Traceback|FLICKER|BLOCKED"
    if ($LASTEXITCODE -ne 0) { throw "Blender failed on $script" }
}

if (-not $NoModels) {
    New-Item -ItemType Directory -Force -Path $assets | Out-Null
    if (-not (Test-Path "$assets\lamps.png") -or -not (Test-Path "$assets\gears.png")) { Blender "dials.py" @($assets) }
    if (-not (Test-Path "$assets\v2_speedo_black.png")) {
        python (Join-Path $PSScriptRoot "blender\dials_v2style.py") $assets   # needs cairosvg
        if ($LASTEXITCODE -ne 0) { throw "dials_v2style.py failed (pip install cairosvg)" }
    }
    if (-not $Cars) {
        $Cars = @('DingDing', 'Burro', 'Protector', 'Tinny', 'TrailRat', 'BullV1', 'TrailBurner', 'Cumbre', 'Woodman',
                  'GrandWoodman', 'Timberbox', 'BlastWagon', 'Boar', 'Lynx', 'Wombat', 'Brick', 'Roamer', 'Polyana',
                  'Grizzly', 'Baguette', 'Mammoth', 'Marshal', 'RustOx')
    }
    foreach ($car in $Cars) { Blender "build_car_v2.py" @($assets, "$root\cars", $car) }
}

foreach ($proj in "OthCockpit.Melon", "OthCockpit") {
    dotnet build (Join-Path $PSScriptRoot "src\$proj\$proj.csproj") -c Release --nologo -v q
    if ($LASTEXITCODE -ne 0) { throw "Build failed ($proj)" }
}

if (-not $NoInstall) {
    if (Get-Process "over the hill" -ErrorAction SilentlyContinue) { throw "Close the game first, the files are locked while it runs." }
    $games = @("C:\Program Files (x86)\Steam\steamapps\common\over the hill",
               "$env:USERPROFILE\dev\oth-ml-test\game", "$env:USERPROFILE\dev\oth-bep-test\game")
    foreach ($game in $games) {
        if (Test-Path "$game\MelonLoader") {
            $dll = "$root\bin\OthCockpit.Melon\Release\net6.0\OthCockpit.Melon.dll"; $mods = "$game\Mods"; $models = "$game\UserData\OthCockpit\models"
        } elseif (Test-Path "$game\BepInEx\core") {
            $dll = "$root\bin\OthCockpit\Release\net6.0\OthCockpit.dll"; $mods = "$game\BepInEx\plugins"; $models = "$game\BepInEx\plugins\OthCockpit\models"
        } else { continue }
        New-Item -ItemType Directory -Force -Path $mods, $models | Out-Null
        $old = Get-ChildItem "$models\Car_*.glb" -ErrorAction SilentlyContinue
        $backup = "$root\backup_models_$(Get-Date -Format yyyy-MM-dd)\$(Split-Path (Split-Path $game -Parent) -Leaf)_$(Split-Path $game -Leaf)"
        if ($old -and -not (Test-Path $backup)) {
            New-Item -ItemType Directory -Force -Path $backup | Out-Null
            $old | Copy-Item -Destination $backup
            Write-Host "Backed up $($old.Count) models to $backup"
        }
        Copy-Item $dll $mods -Force
        Copy-Item "$assets\Car_*.glb" $models -Force
        Write-Host "Installed into $game"
    }
}
