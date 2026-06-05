$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$VenvDir = Join-Path $RepoRoot ".venv-desktop"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$Requirements = Join-Path $RepoRoot "requirements-desktop.txt"
$SpecFile = Join-Path $RepoRoot "packaging\windows\IntelligentCampusGuide.spec"
$DistDir = Join-Path $RepoRoot "dist"
$BuildDir = Join-Path $RepoRoot "build"
$DesktopExe = Join-Path $DistDir "IntelligentCampusGuide\IntelligentCampusGuide.exe"

if (-not (Test-Path -LiteralPath $PythonExe)) {
    py -3 -m venv $VenvDir
}

& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r $Requirements
& $PythonExe -m PyInstaller $SpecFile --noconfirm --clean --distpath $DistDir --workpath $BuildDir

if (-not (Test-Path -LiteralPath $DesktopExe)) {
    throw "Desktop executable was not produced: $DesktopExe"
}

& $DesktopExe --smoke
if ($LASTEXITCODE -ne 0) {
    throw "Desktop smoke check failed with exit code $LASTEXITCODE"
}

Write-Host "Built desktop app: $DesktopExe"
