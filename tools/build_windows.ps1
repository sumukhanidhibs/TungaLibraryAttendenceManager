param(
    [string]$IsccPath = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not [Environment]::Is64BitOperatingSystem -or $env:OS -ne 'Windows_NT') {
    throw 'Build on Windows x64.'
}
python -c "import sys,struct; assert sys.version_info[:3] == (3,11,9); assert struct.calcsize('P') == 8"
if ($LASTEXITCODE -ne 0) { throw 'Use Python 3.11.9 x64.' }
if (-not (Test-Path $IsccPath)) { throw "Inno Setup 6.4.3 compiler not found: $IsccPath" }
python -m pip install --requirement requirements-windows.lock
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
python -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }
python -m pip freeze | Set-Content build-environment.txt
python -m PyInstaller --clean --noconfirm TungaLibrary.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
& $IsccPath installer\TungaLibrary.iss
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }
$hash = (Get-FileHash installer\Output\TungaLibrarySetup.exe -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  TungaLibrarySetup.exe" | Set-Content installer\Output\TungaLibrarySetup.exe.sha256 -Encoding ascii
