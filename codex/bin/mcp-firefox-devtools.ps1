[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Capability,

    [Parameter(Mandatory = $true)]
    [string]$ProfileKey,

    [Parameter(Mandatory = $true)]
    [string]$StartUrl,

    [string]$BindingOrigin = "codex/bin/firefox_mcp_launcher.py",
    [string]$Viewport = "1440x900",
    [switch]$Visible,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "python runtime is required for mcp-firefox-devtools"
}

$enginePath = Join-Path $PSScriptRoot "firefox_mcp_launcher.py"
$cliArgs = @(
    $enginePath,
    "--capability", $Capability,
    "--binding-origin", $BindingOrigin,
    "--profile-key", $ProfileKey,
    "--start-url", $StartUrl,
    "--viewport", $Viewport
)
if ($Visible) { $cliArgs += "--visible" }
if ($DryRun) { $cliArgs += "--dry-run" }

if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
    & $python.Path -3 @cliArgs
} else {
    & $python.Path @cliArgs
}
exit $LASTEXITCODE
