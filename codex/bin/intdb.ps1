[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolPath = Join-Path $PSScriptRoot "..\..\intdb\intdb.ps1"
& $toolPath @CliArgs
exit $LASTEXITCODE
