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

$enginePath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\delivery\bin\publish_bundle_dint.ps1"))
if (-not (Test-Path -LiteralPath $enginePath)) {
    throw "publish_bundle_dint engine adapter not found: $enginePath"
}

& $enginePath -Repo:$Repo -All:$All -NoPush:$NoPush -NoDeploy:$NoDeploy
exit $LASTEXITCODE
