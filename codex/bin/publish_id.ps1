[CmdletBinding()]
param(
    [switch]$NoPush,
    [switch]$NoDeploy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$enginePath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\delivery\bin\publish_id.ps1"))
if (-not (Test-Path -LiteralPath $enginePath)) {
    throw "publish_id engine adapter not found: $enginePath"
}

& $enginePath -NoPush:$NoPush -NoDeploy:$NoDeploy

exit $LASTEXITCODE
