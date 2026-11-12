<#
.SYNOPSIS
  Run the Overseer test suite from PowerShell (Windows PowerShell 5.1 or pwsh).
.DESCRIPTION
  Equivalent of `python3 scripts/check`. Finds a Python 3.9+ interpreter, runs scripts/check
  with it from the repository root, and exits with that process's exit code.
  Select a specific interpreter with -Python or the OVERSEER_PYTHON environment variable.
  -ResolveOnly prints the interpreter that would be used and exits 0 without running tests.
  The suite runs on native Windows; tests that need tmux, a pty, /proc, or bubblewrap are
  skipped there with a stated reason. See docs/DEVELOPMENT.md.
#>
param(
    [string]$Python = $env:OVERSEER_PYTHON,
    [switch]$ResolveOnly
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'python-discovery.ps1')

$interpreter = Find-OverseerPython -Explicit $Python
if (-not $interpreter) {
    [Console]::Error.WriteLine('No Python 3.9+ found. Install Python 3 or set OVERSEER_PYTHON.')
    exit 2
}
if ($ResolveOnly) {
    Write-Output ('python: ' + ($interpreter -join ' '))
    exit 0
}
$leading = @($interpreter | Select-Object -Skip 1)
Push-Location $root
try {
    & $interpreter[0] @leading (Join-Path $root 'scripts/check')
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
