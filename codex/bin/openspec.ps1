[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolPath = Join-Path $PSScriptRoot "..\tools\openspec\node_modules\.bin\openspec"
if (-not (Test-Path $toolPath)) {
    Write-Error "openspec не установлен локально. Запустите: $PSScriptRoot\..\tools\install_tools.sh"
}

& node $toolPath @CliArgs
exit $LASTEXITCODE
