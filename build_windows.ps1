Param(
    [string]$RepoRoot = (Split-Path -Parent $MyInvocation.MyCommand.Path)
)

$ErrorActionPreference = "Stop"

Set-Location $RepoRoot

Write-Host "Syncing dependencies (stats + dev)..."
uv sync --extra stats --extra dev

Write-Host "Building onedir executable..."
uv run pyinstaller --noconsole --onedir --name wotiti --icon "src/assets/wotiti.ico" --hidden-import=tkinter.filedialog --hidden-import=winsound --collect-submodules sklearn --collect-submodules scipy --exclude-module torch --add-data "src/assets;assets" src/main.py

Write-Host "Placing data/ next to EXE..."
$distDir = Join-Path $RepoRoot "dist\wotiti"
$dataSrc = Join-Path $RepoRoot "data"
$dataDst = Join-Path $distDir "data"

if (!(Test-Path $distDir)) {
    throw "Build output not found: $distDir"
}

if (Test-Path $dataDst) {
    Remove-Item -Recurse -Force $dataDst
}

Copy-Item -Recurse -Force $dataSrc $dataDst

# Ensure sounds directory exists
$soundsDst = Join-Path $dataDst "sounds"
if (!(Test-Path $soundsDst)) {
    New-Item -ItemType Directory -Path $soundsDst | Out-Null
}

# Do not ship developer-local config with absolute paths.
$configDst = Join-Path $dataDst "config.json"
if (Test-Path $configDst) {
    Remove-Item -Force $configDst
}

# Ship an empty runtime database (app creates schema on first start).
$dbDst = Join-Path $dataDst "app_database.db"
if (Test-Path $dbDst) {
    Remove-Item -Force $dbDst
}
New-Item -ItemType File -Path $dbDst | Out-Null

# Create helper scripts for per-user autostart (Task-Manager visible).
$toolsDir = Join-Path $distDir "tools"
if (!(Test-Path $toolsDir)) {
    New-Item -ItemType Directory -Path $toolsDir | Out-Null
}

$enableAutostart = @'
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$distDir = Split-Path -Parent $scriptDir
$exePath = Join-Path $distDir "wotiti.exe"

if (!(Test-Path $exePath)) {
    throw "wotiti.exe nicht gefunden: $exePath"
}

$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$valueName = "WoTiTi"
$valueData = '"' + $exePath + '"'

New-Item -Path $runKey -Force | Out-Null
Set-ItemProperty -Path $runKey -Name $valueName -Value $valueData -Type String

Write-Host "Autostart aktiviert (HKCU Run): $valueName"
Write-Host "Pfad: $exePath"
'@

$disableAutostart = @'
$ErrorActionPreference = "Stop"

$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$valueName = "WoTiTi"

if (Get-ItemProperty -Path $runKey -Name $valueName -ErrorAction SilentlyContinue) {
    Remove-ItemProperty -Path $runKey -Name $valueName
    Write-Host "Autostart deaktiviert: $valueName"
}
else {
    Write-Host "Kein Autostart-Eintrag gefunden: $valueName"
}
'@

Set-Content -Path (Join-Path $toolsDir "enable_autostart.ps1") -Value $enableAutostart -Encoding UTF8
Set-Content -Path (Join-Path $toolsDir "disable_autostart.ps1") -Value $disableAutostart -Encoding UTF8

Write-Host "Build complete: $distDir\wotiti.exe"
