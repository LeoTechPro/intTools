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

$enginePath = Join-Path (Split-Path $PSScriptRoot -Parent) "..\\scripts\\codex\\int_git_sync_gate.ps1"
$resolvedEngine = [System.IO.Path]::GetFullPath($enginePath)

if (-not (Test-Path -LiteralPath $resolvedEngine)) {
    throw "int git sync gate engine not found: $resolvedEngine"
}

& $resolvedEngine `
    -Stage $Stage `
    -RootPath $RootPath `
    -Repos $Repos `
    -Push:$Push `
    -DryRun:$DryRun `
    -Json:$Json
exit $LASTEXITCODE
