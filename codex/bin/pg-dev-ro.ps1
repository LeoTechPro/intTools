[CmdletBinding(DefaultParameterSetName="Doctor")]
param(
    [Parameter(ParameterSetName="Sql", Mandatory = $true)]
    [string]$Sql,

    [Parameter(ParameterSetName="File", Mandatory = $true)]
    [string]$Path,

    [Parameter(ParameterSetName="Doctor")]
    [switch]$Doctor
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$profile = "intdata-dev-ro"
$role = "db_readonly_dev"
$db = "intdata"
$envName = "dev"
$mode = "READONLY"

Write-Host "==========================================" -ForegroundColor Yellow
Write-Host "YOU ARE CONNECTING TO $($envName.ToUpper())" -ForegroundColor Yellow
Write-Host "ROLE = $role" -ForegroundColor Yellow
Write-Host "DB   = $db" -ForegroundColor Yellow
Write-Host "MODE = $mode" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Yellow

$intdb = Join-Path $PSScriptRoot "intdb.ps1"
if (-not (Test-Path $intdb)) {
    throw "intdb.ps1 not found near wrapper: $intdb"
}

switch ($PSCmdlet.ParameterSetName) {
    "Doctor" {
        & $intdb doctor --profile $profile
        exit $LASTEXITCODE
    }
    "Sql" {
        & $intdb sql --profile $profile --sql $Sql
        exit $LASTEXITCODE
    }
    "File" {
        & $intdb file --profile $profile --path $Path
        exit $LASTEXITCODE
    }
    default {
        throw "Unsupported mode: $($PSCmdlet.ParameterSetName)"
    }
}
