[CmdletBinding()]
param(
    [switch]$NoPush,
    [switch]$NoDeploy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$enginePath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\delivery\bin\publish_data.ps1"))
if (-not (Test-Path -LiteralPath $enginePath)) {
    throw "publish_data engine adapter not found: $enginePath"
}

& $enginePath -NoPush:$NoPush -NoDeploy:$NoDeploy

exit $LASTEXITCODE
