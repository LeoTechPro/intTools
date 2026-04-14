[CmdletBinding()]
param(
    [switch]$NoPush,
    [switch]$NoDeploy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "python runtime is required for publish_brain_dev"
}

$scriptPath = Join-Path $PSScriptRoot "publish_brain_dev.py"
$cliArgs = @($scriptPath, "--binding-origin", "delivery/bin/publish_brain_dev.ps1")
if ($NoPush) { $cliArgs += "--no-push" }
if ($NoDeploy) { $cliArgs += "--no-deploy" }

if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
    & $python.Path -3 @cliArgs
} else {
    & $python.Path @cliArgs
}
exit $LASTEXITCODE
