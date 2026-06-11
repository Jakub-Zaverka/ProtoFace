$ErrorActionPreference = "Stop"

# Najdi CIRCUITPY disk
$board = Get-Volume -FileSystemLabel "CIRCUITPY" | Select-Object -First 1

if (-not $board) {
    Write-Host "CIRCUITPY drive not found." -ForegroundColor Red
    exit 1
}

$target = "$($board.DriveLetter):\"
$source = Join-Path $PSScriptRoot "src"

if (-not (Test-Path $source)) {
    Write-Host "Folder src/ not found." -ForegroundColor Red
    exit 1
}

Write-Host "Source:   $source"
Write-Host "Target:   $target"


$confirm = Read-Host "Continue? [y/N]"

if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Cancelled."
    exit 0
}

robocopy $source $target /E `
    /XD ".git" ".venv" "__pycache__" `
    /XF "settings.toml" `
    /R:2 /W:1

# Robocopy exit codes:
# 0-7 = success / normal changes
# 8+  = error
if ($LASTEXITCODE -ge 8) {
    Write-Host "Deploy failed. Robocopy exit code: $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Force CircuitPython autoreload
$reloadFile = Join-Path $target ".reload"
(Get-Date).ToString("o") | Set-Content -Path $reloadFile -Encoding ASCII

Write-Host ""
Write-Host "Deploy done. Matrix Portal should reload code.py." -ForegroundColor Green

$port = Read-Host "COM port, napr. COM5"
Write-Host "Press CTRL-D to reload Matrix Portal"
py -m serial.tools.miniterm $port 115200