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
    Write-Host "publish_data FAILED" -ForegroundColor Red
    Write-Host " - Python interpreter is required to run delivery/bin/publish_data.py"
    exit 1
}

$wrapperPath = Join-Path (Split-Path $PSScriptRoot -Parent) "..\\delivery\\bin\\publish_data.py"
$resolvedWrapper = [System.IO.Path]::GetFullPath($wrapperPath)

$args = @()
if ($NoPush) {
    $args += "--no-push"
}
if ($NoDeploy) {
    $args += "--no-deploy"
}

if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
    & $python.Path -3 $resolvedWrapper @args
}
else {
    & $python.Path $resolvedWrapper @args
}

exit $LASTEXITCODE
