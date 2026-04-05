[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONUTF8 = "1"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "python (или py) не найден в PATH"
}

$scriptPath = Join-Path $scriptDir "lib\intdb.py"
if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
    & $python.Source -3 $scriptPath @CliArgs
} else {
    & $python.Source $scriptPath @CliArgs
}
exit $LASTEXITCODE
