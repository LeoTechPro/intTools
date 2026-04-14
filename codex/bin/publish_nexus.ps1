[CmdletBinding()]
param(
    [switch]$NoPush,
    [switch]$NoDeploy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$enginePath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\delivery\bin\publish_nexus.ps1"))
if (-not (Test-Path -LiteralPath $enginePath)) {
    throw "publish_nexus engine adapter not found: $enginePath"
}

& $enginePath -NoPush:$NoPush -NoDeploy:$NoDeploy

exit $LASTEXITCODE
