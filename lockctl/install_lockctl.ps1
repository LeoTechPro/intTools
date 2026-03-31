$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsRoot = Resolve-Path (Join-Path $scriptDir "..")
$binDir = if ($env:LOCKCTL_INSTALL_BIN -and $env:LOCKCTL_INSTALL_BIN.Trim()) { $env:LOCKCTL_INSTALL_BIN } else { Join-Path $env:USERPROFILE "bin" }

New-Item -ItemType Directory -Force -Path $binDir | Out-Null
Copy-Item -Path (Join-Path $scriptDir "lockctl.cmd") -Destination (Join-Path $binDir "lockctl.cmd") -Force
Copy-Item -Path (Join-Path $toolsRoot "codex\\bin\\mcp-lockctl.cmd") -Destination (Join-Path $binDir "lockctl-mcp.cmd") -Force

Write-Output "lockctl install: copied launchers into $binDir"
