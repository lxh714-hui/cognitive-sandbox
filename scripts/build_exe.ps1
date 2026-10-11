$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Spec = Join-Path $ProjectRoot "CognitiveSandbox.spec"
$DistPath = Join-Path $ProjectRoot "dist"
$WorkPath = Join-Path $ProjectRoot "build\pyinstaller"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Project interpreter not found at $Python. Create .venv and install the dev dependencies first."
}
if (-not (Test-Path -LiteralPath $Spec)) {
    throw "PyInstaller spec not found at $Spec."
}

& $Python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is missing. Install the declared dev dependencies with: .\.venv\Scripts\python.exe -m pip install -e '.[dev]'"
}

& $Python -m PyInstaller --noconfirm --clean --distpath $DistPath --workpath $WorkPath $Spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$Executable = Join-Path $DistPath "CognitiveSandbox\CognitiveSandbox.exe"
if (-not (Test-Path -LiteralPath $Executable)) {
    throw "Build completed without the expected executable: $Executable"
}

Write-Host "Build succeeded: $Executable"
