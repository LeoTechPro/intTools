$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsRoot = Resolve-Path (Join-Path $scriptDir "..")
$userPathRaw = [System.Environment]::GetEnvironmentVariable("Path", "User")
$userPathEntries = @()
if ($userPathRaw) {
  $userPathEntries = $userPathRaw.Split(";") | Where-Object { $_ -and $_.Trim() } | ForEach-Object { $_.Trim() }
}
$defaultUserBin = Join-Path $env:USERPROFILE "bin"
$defaultNpmBin = Join-Path $env:APPDATA "npm"

if ($env:COORDCTL_INSTALL_BIN -and $env:COORDCTL_INSTALL_BIN.Trim()) {
  $binDir = $env:COORDCTL_INSTALL_BIN.Trim()
} elseif ($userPathEntries -contains $defaultUserBin) {
  $binDir = $defaultUserBin
} elseif ($userPathEntries -contains $defaultNpmBin) {
  $binDir = $defaultNpmBin
} else {
  $binDir = $defaultUserBin
}

New-Item -ItemType Directory -Force -Path $binDir | Out-Null

$coordctlSource = (Join-Path $scriptDir "coordctl.cmd").Replace("/", "\")
$coordctlTarget = Join-Path $binDir "coordctl.cmd"

$coordctlWrapper = @"
@echo off
setlocal
call "$coordctlSource" %*
exit /b %ERRORLEVEL%
"@

[System.IO.File]::WriteAllText($coordctlTarget, $coordctlWrapper, (New-Object System.Text.UTF8Encoding($false)))

if (-not ($userPathEntries -contains $binDir)) {
  $newPath = if ($userPathRaw -and $userPathRaw.Trim()) { "$userPathRaw;$binDir" } else { $binDir }
  [System.Environment]::SetEnvironmentVariable("Path", $newPath, "User")
  Write-Output "coordctl install: added $binDir to user PATH (new shells only)"
}

Write-Output "coordctl install: copied coordctl launcher into $binDir"
Write-Output "coordctl MCP is exposed by: $toolsRoot\codex\bin\mcp-intdata-cli.cmd --profile coordctl (or intdata-control)"
