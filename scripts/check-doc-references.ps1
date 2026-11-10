<#
.SYNOPSIS
  PowerShell equivalent of `python3 scripts/check-doc-references [document]`.
.DESCRIPTION
  Runs the Python checker with the same interpreter discovery as scripts/check.ps1 and
  exits with its exit code (0 ok, 1 unresolved references, 2 missing document or no Python).
#>
param(
    [string]$Document,
    [string]$Python = $env:OVERSEER_PYTHON
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'python-discovery.ps1')

$interpreter = Find-OverseerPython -Explicit $Python
if (-not $interpreter) {
    [Console]::Error.WriteLine('No Python 3.9+ found. Install Python 3 or set OVERSEER_PYTHON.')
    exit 2
}
$leading = @($interpreter | Select-Object -Skip 1)
$arguments = @((Join-Path $root 'scripts/check-doc-references'))
if ($Document) { $arguments += $Document }
Push-Location $root
try {
    & $interpreter[0] @leading @arguments
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
