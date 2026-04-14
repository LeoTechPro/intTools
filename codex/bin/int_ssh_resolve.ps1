Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-IntSshMode {
    $raw = [string]($env:INT_SSH_MODE)
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return "auto"
    }

    $mode = $raw.Trim().ToLowerInvariant()
    if ($mode -in @("auto", "tailnet", "public")) {
        return $mode
    }

    return "auto"
}

function Get-IntSshProbeTimeoutSec {
    $raw = [string]($env:INT_SSH_PROBE_TIMEOUT_SEC)
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return 4
    }

    $parsed = 0
    if (-not [int]::TryParse($raw.Trim(), [ref]$parsed)) {
        return 4
    }

    if ($parsed -lt 1) {
        return 1
    }
    if ($parsed -gt 30) {
        return 30
    }
    return $parsed
}

function Get-IntSshResolverEnginePath {
    $enginePath = Join-Path $PSScriptRoot "int_ssh_resolve.py"
    $resolved = [System.IO.Path]::GetFullPath($enginePath)
    if (-not (Test-Path -LiteralPath $resolved)) {
        throw "ssh resolver engine not found: $resolved"
    }
    return $resolved
}

function Get-IntSshPythonPath {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command py -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        throw "python runtime is required for int_ssh_resolve"
    }
    return $python
}

function Resolve-IntSshTarget {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RequestedHost,

        [string]$Mode = "",
        [int]$ProbeTimeoutSec = 0
    )

    $python = Get-IntSshPythonPath
    $engine = Get-IntSshResolverEnginePath
    $cliArgs = @(
        $engine,
        "--requested-host", $RequestedHost,
        "--capability", "int_ssh_resolve",
        "--binding-origin", "codex/bin/int_ssh_resolve.ps1",
        "--json"
    )

    if (-not [string]::IsNullOrWhiteSpace($Mode)) {
        $cliArgs += @("--mode", $Mode)
    }
    if ($ProbeTimeoutSec -gt 0) {
        $cliArgs += @("--probe-timeout-sec", [string]$ProbeTimeoutSec)
    }

    if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
        $raw = & $python.Path -3 @cliArgs
    }
    else {
        $raw = & $python.Path @cliArgs
    }

    if ($LASTEXITCODE -ne 0) {
        throw "int_ssh_resolve engine failed for '$RequestedHost'"
    }

    $payload = ($raw | Out-String).Trim() | ConvertFrom-Json -AsHashtable
    return @{
        RequestedHost = $payload.requested_host
        LogicalHost = $payload.logical_host
        ResolvedMode = $payload.resolved_mode
        Transport = $payload.transport
        Destination = $payload.destination
        SshArgs = @($payload.ssh_args)
        ProbeSucceeded = $payload.probe_succeeded
        FallbackUsed = [bool]$payload.fallback_used
        TailnetHost = $payload.tailnet_host
        PublicHost = $payload.public_host
    }
}
