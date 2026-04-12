[CmdletBinding(DefaultParameterSetName="Doctor")]
param(
    [Parameter(ParameterSetName="Sql", Mandatory = $true)]
    [string]$Sql,

    [Parameter(ParameterSetName="File", Mandatory = $true)]
    [string]$Path,

    [Parameter(Mandatory = $true)]
    [string]$Breakglass,

    [Parameter(ParameterSetName="Doctor")]
    [switch]$Doctor
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($Breakglass -ne "I_UNDERSTAND_BREAKGLASS") {
    throw "Set -Breakglass I_UNDERSTAND_BREAKGLASS to continue."
}

$profile = "intdata-dev-admin"
$role = "db_admin_dev"
$db = "intdata"
$envName = "dev"

Write-Host "==========================================" -ForegroundColor Red
Write-Host "YOU ARE CONNECTING TO $($envName.ToUpper())" -ForegroundColor Red
Write-Host "ROLE = $role" -ForegroundColor Red
Write-Host "DB   = $db" -ForegroundColor Red
Write-Host "MODE = BREAKGLASS ADMIN" -ForegroundColor Red
Write-Host "==========================================" -ForegroundColor Red

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
        & $intdb sql --profile $profile --sql $Sql --write --approve-target $profile 
        exit $LASTEXITCODE
    }
    "File" {
        & $intdb file --profile $profile --path $Path --write --approve-target $profile 
        exit $LASTEXITCODE
    }
}
