[CmdletBinding(DefaultParameterSetName="File")]
param(
    [Parameter(ParameterSetName="File", Mandatory = $true)]
    [string]$Path,

    [Parameter(ParameterSetName="Data")]
    [ValidateSet("incremental", "bootstrap")]
    [string]$Mode = "incremental",

    [Parameter(ParameterSetName="Data")]
    [string]$Repo = "D:\int\data",

    [Parameter(ParameterSetName="Data")]
    [switch]$SeedBusiness,

    [Parameter(Mandatory = $true)]
    [switch]$Write,

    [Parameter(Mandatory = $true)]
    [string]$ConfirmTarget
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $Write) {
    throw "pg-dev-migrate requires -Write flag."
}
if ($ConfirmTarget -ne "intdata") {
    throw "Set -ConfirmTarget intdata to continue."
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "YOU ARE CONNECTING TO DEV" -ForegroundColor Cyan
Write-Host "ROLE = db_migrator_dev" -ForegroundColor Cyan
Write-Host "DB   = intdata" -ForegroundColor Cyan
Write-Host "MODE = WRITE (MIGRATION)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$intdb = Join-Path $PSScriptRoot "intdb.ps1"
if (-not (Test-Path $intdb)) {
    throw "intdb.ps1 not found near wrapper: $intdb"
}

if ($PSCmdlet.ParameterSetName -eq "File") {
    & $intdb file --profile intdata-dev-migrator --path $Path --write --approve-target intdata-dev-migrator
    exit $LASTEXITCODE
}

$args = @("migrate", "data", "--target", "intdata-dev-migrator", "--mode", $Mode, "--repo", $Repo, "--approve-target", "intdata-dev-migrator")
if ($SeedBusiness) { $args += "--seed-business" }
& $intdb @args
exit $LASTEXITCODE
