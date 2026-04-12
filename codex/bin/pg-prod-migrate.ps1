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
    [switch]$Prod,

    [Parameter(Mandatory = $true)]
    [string]$ConfirmTarget
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $Write -or -not $Prod) {
    throw "pg-prod-migrate requires -Write and -Prod flags."
}
if ($ConfirmTarget -ne "punkt_b_prod") {
    throw "Set -ConfirmTarget punkt_b_prod to continue."
}

Write-Host "==========================================" -ForegroundColor Red
Write-Host "YOU ARE CONNECTING TO PROD" -ForegroundColor Red
Write-Host "ROLE = db_migrator_prod" -ForegroundColor Red
Write-Host "DB   = punkt_b_prod" -ForegroundColor Red
Write-Host "MODE = WRITE (MIGRATION)" -ForegroundColor Red
Write-Host "==========================================" -ForegroundColor Red

$intdb = Join-Path $PSScriptRoot "intdb.ps1"
if (-not (Test-Path $intdb)) {
    throw "intdb.ps1 not found near wrapper: $intdb"
}

if ($PSCmdlet.ParameterSetName -eq "File") {
    & $intdb file --profile punktb-prod-migrator --path $Path --write --approve-target punktb-prod-migrator --force-prod-write
    exit $LASTEXITCODE
}

$args = @("migrate", "data", "--target", "punktb-prod-migrator", "--mode", $Mode, "--repo", $Repo, "--approve-target", "punktb-prod-migrator", "--force-prod-write")
if ($SeedBusiness) { $args += "--seed-business" }
& $intdb @args
exit $LASTEXITCODE
