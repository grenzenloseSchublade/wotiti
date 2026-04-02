Param(
    [string]$RepoRoot = (Split-Path -Parent $MyInvocation.MyCommand.Path)
)

$ErrorActionPreference = "Stop"

Set-Location $RepoRoot

Write-Host "Syncing dependencies (stats + dev)..."
uv sync --extra stats --extra dev

Write-Host "Building onedir executable..."
uv run pyinstaller --noconsole --onedir --name wotiti --icon "src/assets/wotiti.ico" --hidden-import=tkinter.filedialog --collect-submodules sklearn --collect-submodules scipy --exclude-module torch --add-data "src/assets;assets" src/main.py

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

Write-Host "Build complete: $distDir\wotiti.exe"
