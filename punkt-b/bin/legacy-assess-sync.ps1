[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$SourceDsn,

  [Parameter(Mandatory = $true)]
  [string]$TargetDsn,

  [ValidateSet("specialists", "clients", "results", "all")]
  [string]$Entity = "all",

  [string]$From,

  [string]$StateFile,

  [string]$ReportJson,

  [int]$OverlapMinutes = 5,

  [switch]$Apply,

  [switch]$DryRun,

  [string]$SourceSqlSpecialistsFile,
  [string]$SourceSqlClientsFile,
  [string]$SourceSqlResultsFile
)

$ErrorActionPreference = "Stop"

if ($Apply -and $DryRun) {
  throw "Use only one of -Apply or -DryRun."
}
if (-not $Apply -and -not $DryRun) {
  $DryRun = $true
}

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptPath
$pythonScript = Join-Path $repoRoot "legacy_assess_sync.py"
$runtimeRoot = "D:\int\tools\.runtime\punctb\legacy-assess-sync"

if ([string]::IsNullOrWhiteSpace($StateFile)) {
  $StateFile = Join-Path $runtimeRoot "state.json"
}
if ([string]::IsNullOrWhiteSpace($ReportJson)) {
  $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $ReportJson = Join-Path $runtimeRoot ("reports\legacy-assess-sync-" + $timestamp + ".json")
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StateFile) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ReportJson) | Out-Null

$argv = @(
  $pythonScript,
  "--source-dsn", $SourceDsn,
  "--target-dsn", $TargetDsn,
  "--entity", $Entity,
  "--state-file", $StateFile,
  "--report-json", $ReportJson,
  "--overlap-minutes", "$OverlapMinutes"
)

if ($Apply) {
  $argv += "--apply"
} else {
  $argv += "--dry-run"
}
if ($From) {
  $argv += @("--from", $From)
}
if ($SourceSqlSpecialistsFile) {
  $argv += @("--source-sql-specialists-file", $SourceSqlSpecialistsFile)
}
if ($SourceSqlClientsFile) {
  $argv += @("--source-sql-clients-file", $SourceSqlClientsFile)
}
if ($SourceSqlResultsFile) {
  $argv += @("--source-sql-results-file", $SourceSqlResultsFile)
}

if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3 @argv
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  & python @argv
} else {
  throw "Python launcher not found. Install Python 3 or use 'py -3'."
}
