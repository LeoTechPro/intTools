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

if (-not (Test-Path (Join-Path $assetsRoot "AGENTS.md"))) {
    throw "missing managed assets root: $assetsRoot"
}

New-Item -ItemType Directory -Force -Path $codexHome | Out-Null

function Copy-ManagedFile {
    param(
        [string]$Source,
        [string]$Destination
    )

    if ($DryRun) {
        Write-Output "dry-run copy $Source -> $Destination"
        return
    }

    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

function Sync-ManagedDirectory {
    param(
        [string]$Source,
        [string]$Destination
    )

    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $args = @(
        $Source,
        $Destination,
        "/MIR",
        "/R:1",
        "/W:1",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/NP",
        "/XD", "__pycache__",
        "/XF", "*.pyc"
    )
    if ($DryRun) {
        $args += "/L"
    }
    & robocopy @args | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "robocopy failed for $Source -> $Destination with exit code $LASTEXITCODE"
    }
}

Copy-ManagedFile (Join-Path $assetsRoot "AGENTS.md") (Join-Path $codexHome "AGENTS.md")
Copy-ManagedFile (Join-Path $assetsRoot ".personality_migration") (Join-Path $codexHome ".personality_migration")
Copy-ManagedFile (Join-Path $assetsRoot "version.json") (Join-Path $codexHome "version.json")

Sync-ManagedDirectory (Join-Path $assetsRoot "rules") (Join-Path $codexHome "rules")
Sync-ManagedDirectory (Join-Path $assetsRoot "prompts") (Join-Path $codexHome "prompts")
Sync-ManagedDirectory (Join-Path $assetsRoot "skills") (Join-Path $codexHome "skills")

if (Test-Path $projectsRoot) {
    Sync-ManagedDirectory $projectsRoot (Join-Path $codexHome "projects")
}

Write-Output "synced runtime-facing config assets from $assetsRoot into $codexHome"
