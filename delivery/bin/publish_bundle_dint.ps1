[CmdletBinding()]
param(
    [ValidateSet("data", "assess", "crm", "id", "nexus")]
    [string]$Repo,

    [switch]$All,
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
    throw "python runtime is required for publish_bundle_dint"
}

$scriptPath = Join-Path $PSScriptRoot "publish_bundle_dint.py"
$cliArgs = @($scriptPath, "--binding-origin", "delivery/bin/publish_bundle_dint.ps1")
if (-not [string]::IsNullOrWhiteSpace($Repo)) { $cliArgs += @("--repo", $Repo) }
if ($All) { $cliArgs += "--all" }
if ($NoPush) { $cliArgs += "--no-push" }
if ($NoDeploy) { $cliArgs += "--no-deploy" }

if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
    & $python.Path -3 @cliArgs
} else {
    & $python.Path @cliArgs
}
exit $LASTEXITCODE
