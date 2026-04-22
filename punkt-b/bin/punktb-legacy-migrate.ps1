[CmdletBinding()]
param(
  [ValidateSet("dev", "prod")]
  [string]$Target = "dev",

  [switch]$Apply,

  [switch]$DryRun,

  [string]$Workdir,

  [string]$ReportJson,

  [int]$Limit,

  [switch]$ForceProdWrite
)

$ErrorActionPreference = "Stop"

if ($Apply -and $DryRun) {
  throw "Use only one of -Apply or -DryRun."
}
if (-not $Apply -and -not $DryRun) {
  $DryRun = $true
}
if ($Target -eq "prod" -and -not $Apply) {
  throw "Target=prod is reserved for release apply; use -Apply and -ForceProdWrite in the release window."
}
if ($Target -eq "prod" -and -not $ForceProdWrite) {
  throw "Target=prod requires -ForceProdWrite."
}

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptPath)
$intdb = Join-Path $repoRoot "intdb\lib\intdb.py"

$targetProfile = if ($Target -eq "prod") { "punktb-prod-migrator" } else { "intdata-dev-migrator" }
$argv = @(
  $intdb,
  "project-migrate",
  "punktb-legacy-assess",
  "--source", "punktb-legacy-ro",
  "--target", $targetProfile
)

if ($Apply) {
  $argv += @("--apply", "--approve-target", $targetProfile)
} else {
  $argv += "--dry-run"
}
if ($ForceProdWrite) {
  $argv += "--force-prod-write"
}
if ($Workdir) {
  $argv += @("--workdir", $Workdir)
}
if ($ReportJson) {
  $argv += @("--report-json", $ReportJson)
}
if ($Limit) {
  $argv += @("--limit", $Limit)
}

if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3 @argv
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  & python @argv
} else {
  throw "Python launcher not found. Install Python 3 or use 'py -3'."
}
