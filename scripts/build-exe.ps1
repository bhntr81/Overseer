<#
.SYNOPSIS
  Build dist\Overseer.exe: one file, Python included, the mascot as its icon.
.DESCRIPTION
  PyInstaller is needed only to build; Overseer itself stays standard-library only.
  The release workflow runs this script; install.cmd runs it too when PyInstaller
  can be installed. -NoInstall skips installing PyInstaller.
#>
param([switch]$NoInstall)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'python-discovery.ps1')
$python = Find-OverseerPython -Explicit $env:OVERSEER_PYTHON
if (-not $python) { throw 'No Python 3.9+ found. Install Python from python.org.' }
$py = $python[0]; $lead = @($python | Select-Object -Skip 1)
Push-Location $root
try {
    if (-not $NoInstall) { & $py @lead -m pip install --quiet --upgrade pyinstaller; if ($LASTEXITCODE) { throw 'pip install pyinstaller failed' } }
    # The icon is pre-rendered in overseer\assets (python -m overseer.mascot); the
    # assets folder is bundled so the window finds its icon inside the .exe too.
    & $py @lead -m PyInstaller --noconfirm --clean --onefile --windowed --name Overseer `
        --icon overseer\assets\overseer.ico --add-data "overseer\assets;overseer\assets" `
        --collect-submodules overseer Overseer.pyw
    if ($LASTEXITCODE) { throw 'PyInstaller failed' }
    Write-Output (Join-Path $root 'dist\Overseer.exe')
} finally { Pop-Location }
