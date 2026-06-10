[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = (Resolve-Path $PSScriptRoot).Path
$repoRoot = (Resolve-Path (Join-Path $toolsDir "../..")).Path
$openSpecDir = Join-Path $toolsDir "openspec"
$coordctlInstaller = Join-Path $repoRoot "coordctl/install_coordctl.ps1"

Push-Location $openSpecDir
try {
    npm ci
} finally {
    Pop-Location
}

& $coordctlInstaller

Write-Output "Готово. Используйте локальную команду:"
Write-Output "  $repoRoot/codex/bin/openspec --version"
