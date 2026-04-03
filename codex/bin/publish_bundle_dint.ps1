[CmdletBinding()]
param(
    [ValidateSet("data", "assess", "crm", "id", "nexus")]
    [string]$Repo,

    [switch]$All,
    [switch]$NoPush,
    [switch]$NoDeploy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$wrapperMap = [ordered]@{
    data = (Join-Path $PSScriptRoot "publish_data.ps1")
    assess = (Join-Path $PSScriptRoot "publish_assess.ps1")
    crm = (Join-Path $PSScriptRoot "publish_crm.ps1")
    id = (Join-Path $PSScriptRoot "publish_id.ps1")
    nexus = (Join-Path $PSScriptRoot "publish_nexus.ps1")
}

if (-not $All -and [string]::IsNullOrWhiteSpace($Repo)) {
    Write-Host "publish_bundle_dint FAILED" -ForegroundColor Red
    Write-Host " - This is a manual bulk utility. Use -Repo <data|assess|crm|id|nexus> or -All."
    exit 1
}

$targets = if ($All) { $wrapperMap.Keys } else { @($Repo) }
$failures = [System.Collections.Generic.List[string]]::new()

foreach ($target in $targets) {
    $wrapperPath = $wrapperMap[$target]
    & $wrapperPath -NoPush:$NoPush -NoDeploy:$NoDeploy
    if ($LASTEXITCODE -ne 0) {
        $failures.Add($target)
    }
}

if ($failures.Count -gt 0) {
    Write-Host "publish_bundle_dint FAILED" -ForegroundColor Red
    foreach ($failure in $failures) {
        Write-Host " - $failure wrapper failed"
    }
    exit 1
}

Write-Host "publish_bundle_dint OK" -ForegroundColor Green
foreach ($target in $targets) {
    Write-Host " - $target wrapper completed"
}
exit 0
