[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Logical,

    [ValidateSet("auto", "tailnet", "public")]
    [string]$Mode = "auto"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "python runtime is required for int_ssh_host"
}

$enginePath = Join-Path $PSScriptRoot "int_ssh_resolve.py"
$cliArgs = @(
    $enginePath,
    "--requested-host", $Logical,
    "--mode", $Mode,
    "--capability", "int_ssh_host",
    "--binding-origin", "codex/bin/int_ssh_host.ps1",
    "--destination-only"
)

if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
    & $python.Path -3 @cliArgs
} else {
    & $python.Path @cliArgs
}
exit $LASTEXITCODE
