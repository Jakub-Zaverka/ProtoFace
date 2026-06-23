param(
    [string]$Environment = "matrixportal_s3",
    [string]$Port = "COM7",
    [switch]$Monitor,
    [switch]$Clean
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Join-Path $scriptDir "main_controller"

$ErrorActionPreference = "Stop"

if (-not (Get-Command pio -ErrorAction SilentlyContinue)) {
    throw "PlatformIO CLI 'pio' was not found. Install the VS Code PlatformIO extension or add PlatformIO to PATH."
}

Push-Location $projectDir
try {
    if ($Clean) {
        pio run -e $Environment -t clean
    }

    pio run -e $Environment
    pio run -e $Environment -t upload --upload-port $Port

    if ($Monitor) {
        pio device monitor --port $Port --baud 115200
    }
}
finally {
    Pop-Location
    pio device monitor --port $Port --baud 115200
}
