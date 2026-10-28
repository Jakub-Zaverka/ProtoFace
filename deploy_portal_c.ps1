[CmdletBinding()]
param(
    [string]$Port,
    [switch]$FirmwareOnly,
    [switch]$Monitor,
    [switch]$BuildOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$project = Join-Path $PSScriptRoot 'src_c'
$pioCommand = Get-Command pio -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $pioCommand) {
    throw "PlatformIO 'pio' not found in PATH. Open a terminal with PlatformIO installed."
}
if (-not (Test-Path -LiteralPath (Join-Path $project 'platformio.ini') -PathType Leaf)) {
    throw "C++ project not found: $project"
}
if (-not $FirmwareOnly -and -not (Test-Path -LiteralPath (Join-Path $project 'data/settings.toml') -PathType Leaf)) {
    throw 'Missing src_c/data/settings.toml. Copy your settings from CIRCUITPY, or copy src_c/settings.example.toml there and edit it.'
}

function Invoke-Pio {
    param([string[]]$PioArguments)
    & $pioCommand @PioArguments
    if ($LASTEXITCODE -ne 0) {
        throw "PlatformIO failed (exit $LASTEXITCODE): pio $($PioArguments -join ' ')"
    }
}

function Get-SerialDevices {
    $raw = & $pioCommand device list --json-output
    if ($LASTEXITCODE -ne 0) { throw 'Could not enumerate serial ports.' }
    if (-not $raw) { return }
    $raw -join "`n" | ConvertFrom-Json
}

function Get-PortalCandidates {
    param([object[]]$Devices)
    # MatrixPortal S3 Arduino/CircuitPython/TinyUF2, plus ESP32-S3 ROM USB.
    # ROM VID/PID alone cannot distinguish two connected ESP32-S3 boards.
    $Devices | Where-Object {
        $_.hwid -match '(?i)(239A:(8125|0125|8126)|303A:1001)'
    }
}

function Get-SerialIdentity {
    param($Device)
    if ($Device.hwid -match '(?i)SER=([^ ]+)') { return $Matches[1] }
    return ''
}

function Find-Portal {
    param([string]$RequestedPort, [string]$Identity, [int]$WaitSeconds = 0)
    $deadline = [DateTime]::UtcNow.AddSeconds($WaitSeconds)
    do {
        $devices = @(Get-SerialDevices)
        if ($RequestedPort) {
            $matching = @($devices | Where-Object { $_.port -eq $RequestedPort })
            if ($matching.Count -eq 1) { return $matching[0] }
        }
        else {
            $candidates = @(Get-PortalCandidates -Devices $devices)
            if ($Identity) {
                $sameBoard = @($candidates | Where-Object { (Get-SerialIdentity $_) -eq $Identity })
                if ($sameBoard.Count -eq 1) { return $sameBoard[0] }
            }
            if ($candidates.Count -eq 1) { return $candidates[0] }
            if ($candidates.Count -gt 1) {
                throw "Multiple possible boards: $($candidates.port -join ', '). Disconnect other boards or specify -Port COMx."
            }
        }
        if ([DateTime]::UtcNow -ge $deadline) { break }
        Start-Sleep -Milliseconds 500
    } while ($true)
    throw 'MatrixPortal serial port not found. Press RESET, or hold BOOT, press/release RESET, release BOOT, then retry with -Port COMx.'
}

Write-Host "Project: $project"
Invoke-Pio -PioArguments @('run', '-d', $project)
if (-not $FirmwareOnly) {
    Invoke-Pio -PioArguments @('run', '-d', $project, '-t', 'buildfs')
}
if ($BuildOnly) {
    Write-Host 'Build completed. Nothing uploaded.' -ForegroundColor Green
    return
}

$board = Find-Portal -RequestedPort $Port
$identity = Get-SerialIdentity $board
Write-Host "Uploading firmware via $($board.port). Close other serial monitors."
Invoke-Pio -PioArguments @('run', '-d', $project, '-t', 'upload', '--upload-port', $board.port)

if (-not $FirmwareOnly) {
    # 1200-baud reset can switch COM7 -> ROM COM4 -> application COM7.
    # Re-enumerate instead of reusing the original port unconditionally.
    Write-Host 'Waiting for the board after firmware upload. Press RESET if needed.'
    $board = Find-Portal -Identity $identity -WaitSeconds 30
    Invoke-Pio -PioArguments @('run', '-d', $project, '-t', 'uploadfs', '--upload-port', $board.port)
}

Write-Host 'Deployment completed. Press RESET if the application does not start.' -ForegroundColor Green
if ($Monitor) {
    Write-Host 'Waiting for the serial monitor port. Press RESET if needed. Ctrl+C closes the monitor.'
    $board = Find-Portal -Identity $identity -WaitSeconds 30
    Invoke-Pio -PioArguments @('device', 'monitor', '-d', $project, '--port', $board.port, '--baud', '115200')
}
