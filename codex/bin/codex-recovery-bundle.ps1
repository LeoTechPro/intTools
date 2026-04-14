[CmdletBinding()]
param(
    [string]$BindingOrigin = "codex/bin/codex-recovery-bundle.ps1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "python runtime is required for codex-recovery-bundle"
}

$enginePath = Join-Path $PSScriptRoot "codex_recovery_bundle.py"
$cliArgs = @($enginePath, "--binding-origin", $BindingOrigin) + $args

if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
    & $python.Path -3 @cliArgs
} else {
    & $python.Path @cliArgs
}
exit $LASTEXITCODE
