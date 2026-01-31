Param(
    [string]$RepoRoot = (Split-Path -Parent $MyInvocation.MyCommand.Path)
)

$ErrorActionPreference = "Stop"

Set-Location $RepoRoot

Write-Host "Syncing dependencies (stats + dev)..."
uv sync --extra stats --extra dev

Write-Host "Building onedir executable..."
pyinstaller --noconsole --onedir --name wotiti src/main.py --add-data "src/assets;assets"

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

Write-Host "Build complete: $distDir\wotiti.exe"
