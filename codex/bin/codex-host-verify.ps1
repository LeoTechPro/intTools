[CmdletBinding()]
param(
    [string]$BindingOrigin = "codex/bin/codex-host-verify.ps1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "python runtime is required for codex-host-verify"
}

$enginePath = Join-Path $PSScriptRoot "codex_host_verify.py"
$cliArgs = @($enginePath, "--binding-origin", $BindingOrigin) + $args

if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
    & $python.Path -3 @cliArgs
} else {
    & $python.Path @cliArgs
}
exit $LASTEXITCODE
