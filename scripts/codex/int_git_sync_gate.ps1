param(
    [ValidateSet("start", "finish")]
    [string]$Stage = "start",

    [string]$RootPath = "",

    [string[]]$Repos = @(),

    [switch]$Push,

    [switch]$DryRun,

    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "python runtime is required for int_git_sync_gate"
}

$enginePath = Join-Path $PSScriptRoot "int_git_sync_gate.py"
$resolvedEngine = [System.IO.Path]::GetFullPath($enginePath)
if (-not (Test-Path -LiteralPath $resolvedEngine)) {
    throw "int_git_sync_gate.py not found: $resolvedEngine"
}

$cliArgs = @(
    "--stage", $Stage
)

if (-not [string]::IsNullOrWhiteSpace($RootPath)) {
    $cliArgs += @("--root-path", $RootPath)
}

if ($Repos.Count -gt 0) {
    $cliArgs += "--repos"
    $cliArgs += $Repos
}

if ($Push) {
    $cliArgs += "--push"
}
if ($DryRun) {
    $cliArgs += "--dry-run"
}
if ($Json) {
    $cliArgs += "--json"
}

if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
    & $python.Path -3 $resolvedEngine @cliArgs
}
else {
    & $python.Path $resolvedEngine @cliArgs
}

exit $LASTEXITCODE
