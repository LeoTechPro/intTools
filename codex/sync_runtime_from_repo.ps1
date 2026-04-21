[CmdletBinding()]
param(
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$codexRoot = (Resolve-Path $PSScriptRoot).Path
$assetsRoot = if ($env:ASSETS_ROOT) { $env:ASSETS_ROOT } else { Join-Path $codexRoot "assets/codex-home" }
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
$projectsRoot = if ($env:PROJECTS_ROOT) { $env:PROJECTS_ROOT } else { Join-Path $codexRoot "projects" }

if ($DryRun) {
    Write-Output "dry-run: Codex home sync is retired; use native Codex plugin/skill/config mechanisms."
    Write-Output "legacy source: $assetsRoot"
    Write-Output "legacy projects source: $projectsRoot"
    Write-Output "legacy destination: $codexHome"
    exit 0
}

Write-Error "Codex home sync is retired; use native Codex plugin/skill/config mechanisms."
exit 1
