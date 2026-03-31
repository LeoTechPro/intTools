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

if ($env:LOCKCTL_INSTALL_BIN -and $env:LOCKCTL_INSTALL_BIN.Trim()) {
  $binDir = $env:LOCKCTL_INSTALL_BIN.Trim()
} elseif ($userPathEntries -contains $defaultUserBin) {
  $binDir = $defaultUserBin
} elseif ($userPathEntries -contains $defaultNpmBin) {
  $binDir = $defaultNpmBin
} else {
  $binDir = $defaultUserBin
}

New-Item -ItemType Directory -Force -Path $binDir | Out-Null

$lockctlSource = (Join-Path $scriptDir "lockctl.cmd").Replace("/", "\")
$lockctlMcpSource = (Join-Path $toolsRoot "codex\\bin\\mcp-lockctl.cmd").Replace("/", "\")
$lockctlTarget = Join-Path $binDir "lockctl.cmd"
$lockctlMcpTarget = Join-Path $binDir "lockctl-mcp.cmd"

$lockctlWrapper = @"
@echo off
setlocal
call "$lockctlSource" %*
exit /b %ERRORLEVEL%
"@

$lockctlMcpWrapper = @"
@echo off
setlocal
call "$lockctlMcpSource" %*
exit /b %ERRORLEVEL%
"@

[System.IO.File]::WriteAllText($lockctlTarget, $lockctlWrapper, (New-Object System.Text.UTF8Encoding($false)))
[System.IO.File]::WriteAllText($lockctlMcpTarget, $lockctlMcpWrapper, (New-Object System.Text.UTF8Encoding($false)))

if (-not ($userPathEntries -contains $binDir)) {
  $newPath = if ($userPathRaw -and $userPathRaw.Trim()) { "$userPathRaw;$binDir" } else { $binDir }
  [System.Environment]::SetEnvironmentVariable("Path", $newPath, "User")
  Write-Output "lockctl install: added $binDir to user PATH (new shells only)"
}

Write-Output "lockctl install: copied launchers into $binDir"
