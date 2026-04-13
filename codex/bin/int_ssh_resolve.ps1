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

function Get-IntSshConfigPath {
    $override = [string]($env:INT_SSH_CONFIG_PATH)
    if (-not [string]::IsNullOrWhiteSpace($override)) {
        return $override.Trim()
    }

    return (Join-Path $PSScriptRoot "..\config\int_ssh_config")
}

function Resolve-IntSshLogicalHost {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RequestedHost
    )

    $raw = $RequestedHost.Trim()
    $map = @{
        "vds-intdata-intdata" = "dev-intdata"
        "vds-intdata-codex" = "dev-codex"
        "vds-intdata-openclaw" = "dev-openclaw"
        "prod" = "prod-leon"
        "vds.punkt-b.pro" = "prod-leon"
        "dev-intdata" = "dev-intdata"
        "dev-codex" = "dev-codex"
        "dev-openclaw" = "dev-openclaw"
        "prod-leon" = "prod-leon"
    }

    if ($map.ContainsKey($raw)) {
        return $map[$raw]
    }

    return $null
}

function Get-IntSshTargetSpec {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LogicalHost
    )

    $suffix = [string]($env:INT_SSH_TAILNET_SUFFIX)
    if ([string]::IsNullOrWhiteSpace($suffix)) {
        $suffix = "tailf0f164.ts.net"
    } else {
        $suffix = $suffix.Trim()
    }

    switch ($LogicalHost) {
        "dev-intdata" {
            $publicHost = if ([string]::IsNullOrWhiteSpace([string]$env:INT_SSH_DEV_PUBLIC_HOST)) { "vds.intdata.pro" } else { [string]$env:INT_SSH_DEV_PUBLIC_HOST }
            $tailNode = if ([string]::IsNullOrWhiteSpace([string]$env:INT_SSH_DEV_TAILNET_NODE)) { "vds-intdata-pro" } else { [string]$env:INT_SSH_DEV_TAILNET_NODE }
            $tailHost = if ([string]::IsNullOrWhiteSpace([string]$env:INT_SSH_DEV_TAILNET_HOST)) { "$tailNode.$suffix" } else { [string]$env:INT_SSH_DEV_TAILNET_HOST }
            return @{
                LogicalHost = $LogicalHost
                User = "intdata"
                IdentityFile = "~/.ssh/id_ed25519_vds_intdata_intdata"
                PublicHost = $publicHost.Trim()
                TailnetHost = $tailHost.Trim()
                PublicAlias = "int-dev-intdata-public"
                TailnetAlias = "int-dev-intdata-tailnet"
            }
        }
        "dev-codex" {
            $publicHost = if ([string]::IsNullOrWhiteSpace([string]$env:INT_SSH_DEV_PUBLIC_HOST)) { "vds.intdata.pro" } else { [string]$env:INT_SSH_DEV_PUBLIC_HOST }
            $tailNode = if ([string]::IsNullOrWhiteSpace([string]$env:INT_SSH_DEV_TAILNET_NODE)) { "vds-intdata-pro" } else { [string]$env:INT_SSH_DEV_TAILNET_NODE }
            $tailHost = if ([string]::IsNullOrWhiteSpace([string]$env:INT_SSH_DEV_TAILNET_HOST)) { "$tailNode.$suffix" } else { [string]$env:INT_SSH_DEV_TAILNET_HOST }
            return @{
                LogicalHost = $LogicalHost
                User = "codex"
                IdentityFile = "~/.ssh/id_ed25519_vds_intdata_codex"
                PublicHost = $publicHost.Trim()
                TailnetHost = $tailHost.Trim()
                PublicAlias = "int-dev-codex-public"
                TailnetAlias = "int-dev-codex-tailnet"
            }
        }
        "dev-openclaw" {
            $publicHost = if ([string]::IsNullOrWhiteSpace([string]$env:INT_SSH_DEV_PUBLIC_HOST)) { "vds.intdata.pro" } else { [string]$env:INT_SSH_DEV_PUBLIC_HOST }
            $tailNode = if ([string]::IsNullOrWhiteSpace([string]$env:INT_SSH_DEV_TAILNET_NODE)) { "vds-intdata-pro" } else { [string]$env:INT_SSH_DEV_TAILNET_NODE }
            $tailHost = if ([string]::IsNullOrWhiteSpace([string]$env:INT_SSH_DEV_TAILNET_HOST)) { "$tailNode.$suffix" } else { [string]$env:INT_SSH_DEV_TAILNET_HOST }
            return @{
                LogicalHost = $LogicalHost
                User = "openclaw"
                IdentityFile = "~/.ssh/id_ed25519_vds_intdata_openclaw"
                PublicHost = $publicHost.Trim()
                TailnetHost = $tailHost.Trim()
                PublicAlias = "int-dev-openclaw-public"
                TailnetAlias = "int-dev-openclaw-tailnet"
            }
        }
        "prod-leon" {
            $publicHost = if ([string]::IsNullOrWhiteSpace([string]$env:INT_SSH_PROD_PUBLIC_HOST)) { "vds.punkt-b.pro" } else { [string]$env:INT_SSH_PROD_PUBLIC_HOST }
            $tailNode = if ([string]::IsNullOrWhiteSpace([string]$env:INT_SSH_PROD_TAILNET_NODE)) { "vds-punkt-b-pro" } else { [string]$env:INT_SSH_PROD_TAILNET_NODE }
            $tailHost = if ([string]::IsNullOrWhiteSpace([string]$env:INT_SSH_PROD_TAILNET_HOST)) { "$tailNode.$suffix" } else { [string]$env:INT_SSH_PROD_TAILNET_HOST }
            return @{
                LogicalHost = $LogicalHost
                User = "leon"
                IdentityFile = "~/.ssh/id_ed25519"
                PublicHost = $publicHost.Trim()
                TailnetHost = $tailHost.Trim()
                PublicAlias = "int-prod-leon-public"
                TailnetAlias = "int-prod-leon-tailnet"
            }
        }
        default {
            return $null
        }
    }
}

function New-IntSshEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Spec,

        [Parameter(Mandatory = $true)]
        [ValidateSet("public", "tailnet")]
        [string]$Transport,

        [Parameter(Mandatory = $true)]
        [string]$ConfigPath
    )

    $useAlias = Test-Path -LiteralPath $ConfigPath

    if ($Transport -eq "public") {
        return @{
            Transport = $Transport
            Alias = [string]$Spec.PublicAlias
            User = [string]$Spec.User
            Host = [string]$Spec.PublicHost
            IdentityFile = [string]$Spec.IdentityFile
            UseAlias = $useAlias
            ConfigPath = $ConfigPath
        }
    }

    return @{
        Transport = $Transport
        Alias = [string]$Spec.TailnetAlias
        User = [string]$Spec.User
        Host = [string]$Spec.TailnetHost
        IdentityFile = [string]$Spec.IdentityFile
        UseAlias = $useAlias
        ConfigPath = $ConfigPath
    }
}

function ConvertTo-IntSshArgs {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Endpoint,

        [Parameter(Mandatory = $true)]
        [int]$ProbeTimeoutSec
    )

    $args = @(
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=$ProbeTimeoutSec"
    )

    if ($Endpoint.UseAlias) {
        $args += @("-F", [string]$Endpoint.ConfigPath, [string]$Endpoint.Alias)
        return $args
    }

    $args += @(
        "-o", "StrictHostKeyChecking=accept-new",
        "-i", [string]$Endpoint.IdentityFile,
        ("{0}@{1}" -f [string]$Endpoint.User, [string]$Endpoint.Host)
    )
    return $args
}

function Test-IntSshEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Endpoint,

        [Parameter(Mandatory = $true)]
        [int]$ProbeTimeoutSec
    )

    $probeArgs = ConvertTo-IntSshArgs -Endpoint $Endpoint -ProbeTimeoutSec $ProbeTimeoutSec
    $null = (& ssh @probeArgs "true" 2>$null)
    return ($LASTEXITCODE -eq 0)
}

function Resolve-IntSshTarget {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RequestedHost,

        [string]$Mode = "",
        [int]$ProbeTimeoutSec = 0
    )

    $resolvedMode = if ([string]::IsNullOrWhiteSpace($Mode)) { Get-IntSshMode } else { $Mode.Trim().ToLowerInvariant() }
    if ($resolvedMode -notin @("auto", "tailnet", "public")) {
        $resolvedMode = "auto"
    }

    if ($ProbeTimeoutSec -le 0) {
        $ProbeTimeoutSec = Get-IntSshProbeTimeoutSec
    }

    $logicalHost = Resolve-IntSshLogicalHost -RequestedHost $RequestedHost
    if ($null -eq $logicalHost) {
        return @{
            RequestedHost = $RequestedHost
            LogicalHost = $null
            ResolvedMode = "legacy"
            Transport = "legacy"
            Destination = $RequestedHost
            SshArgs = @($RequestedHost)
            ProbeSucceeded = $null
            FallbackUsed = $false
            TailnetHost = $null
            PublicHost = $null
        }
    }

    $configPath = Get-IntSshConfigPath
    $spec = Get-IntSshTargetSpec -LogicalHost $logicalHost
    if ($null -eq $spec) {
        throw "No SSH target spec found for logical host '$logicalHost'."
    }

    $publicEndpoint = New-IntSshEndpoint -Spec $spec -Transport "public" -ConfigPath $configPath
    $tailnetEndpoint = New-IntSshEndpoint -Spec $spec -Transport "tailnet" -ConfigPath $configPath

    $selected = $publicEndpoint
    $probeSucceeded = $null
    $fallbackUsed = $false

    switch ($resolvedMode) {
        "public" {
            $selected = $publicEndpoint
        }
        "tailnet" {
            $selected = $tailnetEndpoint
        }
        default {
            $probeSucceeded = Test-IntSshEndpoint -Endpoint $tailnetEndpoint -ProbeTimeoutSec $ProbeTimeoutSec
            if ($probeSucceeded) {
                $selected = $tailnetEndpoint
            } else {
                $selected = $publicEndpoint
                $fallbackUsed = $true
            }
        }
    }

    $sshArgs = ConvertTo-IntSshArgs -Endpoint $selected -ProbeTimeoutSec $ProbeTimeoutSec
    $destination = if ($selected.UseAlias) { [string]$selected.Alias } else { "{0}@{1}" -f [string]$selected.User, [string]$selected.Host }

    return @{
        RequestedHost = $RequestedHost
        LogicalHost = $logicalHost
        ResolvedMode = $resolvedMode
        Transport = [string]$selected.Transport
        Destination = $destination
        SshArgs = $sshArgs
        ProbeSucceeded = $probeSucceeded
        FallbackUsed = $fallbackUsed
        TailnetHost = [string]$spec.TailnetHost
        PublicHost = [string]$spec.PublicHost
    }
}
