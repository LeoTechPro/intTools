[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$ErrorActionPreference = 'Stop'
$python = Get-Command python -ErrorAction Stop
& $python.Source (Join-Path $PSScriptRoot 'prointdata_google.py') @CliArgs
exit $LASTEXITCODE

