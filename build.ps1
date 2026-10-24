# Builds the cockpit mod and its models (all output outside OneDrive) and installs them into every game
# folder that runs the matching loader (the real game and the test copies), like the wheel mod's build.ps1.
#   1. Blender: dial pictures (blender\dials.py) + cockpit models (blender\build_<car>.py) -> %USERPROFILE%\dev\oth-cockpit-build\assets
#      The model scripts use the car body exported from the game (tools\export_car.py) in %USERPROFILE%\dev\oth-cockpit-build\cars\<car>.
#   2. dotnet:  OthCockpit.Melon.dll (MelonLoader) and OthCockpit.dll (BepInEx, references from %USERPROFILE%\dev\oth-bep-test\game)
#   3. Install: MelonLoader -> Mods\OthCockpit.Melon.dll + UserData\OthCockpit\models\Car_*.glb
#               BepInEx     -> BepInEx\plugins\OthCockpit.dll + BepInEx\plugins\OthCockpit\models\Car_*.glb
# Usage: powershell -File build.ps1 [-NoModels] [-NoInstall]
param(
    [switch]$NoModels,
    [switch]$NoInstall
)
$ErrorActionPreference = "Stop"
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
$root = "$env:USERPROFILE\dev\oth-cockpit-build"
$assets = "$root\assets"
$blender = "$env:USERPROFILE\dev\tools\blender\blender.exe"

function Blender([string]$script, [string[]]$scriptArgs) {
    & $blender -b --factory-startup -P (Join-Path $PSScriptRoot "blender\$script") -- @scriptArgs | Select-String -Pattern "wrote|Error|Traceback|FLICKER"
    if ($LASTEXITCODE -ne 0) { throw "Blender failed on $script" }
}

if (-not $NoModels) {
    New-Item -ItemType Directory -Force -Path $assets | Out-Null
    Blender "dials.py" @($assets)
    # Hand-built cockpits, then every car of blender\cars_config.py through the generic builder.
    Blender "build_dingding.py" @($assets, "$root\cars\DingDing")
    Blender "build_protector.py" @($assets, "$root\cars\Protector")
    $generic = @('Baguette', 'BlastWagon', 'Boar', 'Brick', 'BullV1', 'Burro', 'Cumbre', 'GrandWoodman', 'Grizzly', 'Lynx',
                 'Mammoth', 'Marshal', 'Polyana', 'Roamer', 'RustOx', 'Timberbox', 'Tinny', 'TrailBurner', 'TrailRat',
                 'Wombat', 'Woodman')
    foreach ($car in $generic) { Blender "build_car.py" @($assets, "$root\cars", $car) }
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
        Copy-Item $dll $mods -Force
        Copy-Item "$assets\Car_*.glb" $models -Force
        Write-Host "Installed into $game"
    }
}
