# Dot-sourced by scripts/check.ps1 and scripts/check-doc-references.ps1.
# Find-OverseerPython returns the interpreter command as an array (program, then any
# leading arguments such as '-3' for the Windows `py` launcher), or $null when none is found.
function Find-OverseerPython {
    param([string]$Explicit)
    if ($Explicit) { return , @($Explicit) }
    foreach ($candidate in @(@('py', '-3'), @('python3'), @('python'))) {
        $command = Get-Command $candidate[0] -ErrorAction SilentlyContinue
        if (-not $command) { continue }
        $leading = @($candidate | Select-Object -Skip 1)
        & $command.Source @leading -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) {
            $found = @($command.Source) + $leading
            return , $found
        }
    }
    return $null
}
