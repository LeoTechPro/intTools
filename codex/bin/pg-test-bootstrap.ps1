[CmdletBinding(DefaultParameterSetName="Doctor")]
param(
    [Parameter(ParameterSetName="File", Mandatory = $true)]
    [string]$Path,

    [Parameter(Mandatory = $true)]
    [switch]$Write,

    [Parameter(Mandatory = $true)]
    [string]$ConfirmTarget,

    [Parameter(ParameterSetName="Doctor")]
    [switch]$Doctor
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($PSCmdlet.ParameterSetName -ne "Doctor") {
    if (-not $Write) {
        throw "pg-test-bootstrap requires -Write for mutating operations."
    }
    if ($ConfirmTarget -ne "punkt_b_test") {
        throw "Set -ConfirmTarget punkt_b_test to continue."
    }
}

Write-Host "==========================================" -ForegroundColor Magenta
Write-Host "YOU ARE CONNECTING TO TEST" -ForegroundColor Magenta
Write-Host "ROLE = intdata_test_bootstrap" -ForegroundColor Magenta
Write-Host "DB   = punkt_b_test" -ForegroundColor Magenta
Write-Host "MODE = DISPOSABLE TEST BOOTSTRAP" -ForegroundColor Magenta
Write-Host "==========================================" -ForegroundColor Magenta

$intdb = Join-Path $PSScriptRoot "intdb.ps1"
if (-not (Test-Path $intdb)) {
    throw "intdb.ps1 not found near wrapper: $intdb"
}

if ($PSCmdlet.ParameterSetName -eq "Doctor") {
    & $intdb doctor --profile punktb-test-bootstrap
    exit $LASTEXITCODE
}

& $intdb file --profile punktb-test-bootstrap --path $Path --write --approve-target punktb-test-bootstrap
exit $LASTEXITCODE
