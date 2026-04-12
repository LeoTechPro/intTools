[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    Write-Host "publish_repo FAILED" -ForegroundColor Red
    Write-Host " - Python interpreter is required to run delivery/bin/publish_repo.py"
    exit 1
}

$enginePath = Join-Path (Split-Path $PSScriptRoot -Parent) "..\\delivery\\bin\\publish_repo.py"
$resolvedEngine = [System.IO.Path]::GetFullPath($enginePath)

if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
    & $python.Path -3 $resolvedEngine @Args
}
else {
    & $python.Path $resolvedEngine @Args
}

exit $LASTEXITCODE
