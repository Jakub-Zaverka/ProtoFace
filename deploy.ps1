$ErrorActionPreference = "Stop"

# Najdi CIRCUITPY disk
$board = Get-Volume -FileSystemLabel "CIRCUITPY" | Select-Object -First 1

if (-not $board) {
    Write-Host "CIRCUITPY disk nebyl nalezen." -ForegroundColor Red
    exit 1
}

$target = "$($board.DriveLetter):\"
$source = Join-Path $PSScriptRoot "src"

if (-not (Test-Path $source)) {
    Write-Host "Složka src/ nebyla nalezena." -ForegroundColor Red
    exit 1
}

Write-Host "Zdroj: $source"
Write-Host "Cíl:   $target"
Write-Host ""
Write-Host "Tento script bude kopírovat soubory na CIRCUITPY."
Write-Host "Nic nebude mazat."
Write-Host ""

$confirm = Read-Host "Pokračovat? [y/N]"

if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Zrušeno."
    exit 0
}

robocopy $source $target /E `
    /XD ".git" ".venv" "__pycache__" `
    /XF "settings.toml" `
    /R:2 /W:1

# Robocopy má zvláštní exit kódy:
# 0–7 znamená úspěch nebo běžné změny, 8+ znamená chyba
if ($LASTEXITCODE -ge 8) {
    Write-Host "Deploy selhal. Robocopy exit code: $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Deploy hotový." -ForegroundColor Green