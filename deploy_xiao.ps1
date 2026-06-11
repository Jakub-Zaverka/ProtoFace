$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$controllerDir = Join-Path $scriptDir "controller"
$settingsPath = Join-Path $controllerDir "settings.toml"

if (-not (Test-Path -LiteralPath $controllerDir -PathType Container)) {
    throw "Controller directory not found: $controllerDir"
}

if (-not (Get-Command pio -ErrorAction SilentlyContinue)) {
    throw "PlatformIO command 'pio' was not found in PATH. Restart VS Code/terminal after adding PlatformIO to PATH."
}

if (-not (Test-Path -LiteralPath $settingsPath -PathType Leaf)) {
    throw "Missing controller settings.toml. Copy controller/settings.example.toml to controller/settings.toml first."
}

Push-Location $controllerDir
try {
    pio run --target upload
    pio device monitor
}
finally {
    Pop-Location
}
