param(
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function Resolve-ToolCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Tool
    )

    $cmd = Get-Command $Tool -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) {
        return $cmd
    }

    $wingetLink = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\$Tool.exe"
    if (Test-Path -LiteralPath $wingetLink) {
        return [pscustomobject]@{
            Source = $wingetLink
            Path = $wingetLink
            Name = $Tool
        }
    }

    return $null
}

function Invoke-ToolCheck {
    param(
        [Parameter(Mandatory = $true)][string]$Tool,
        [Parameter(Mandatory = $true)][scriptblock]$VersionCommand
    )

    $cmd = Resolve-ToolCommand -Tool $Tool
    if (-not $cmd) {
        return [pscustomobject]@{
            tool = $Tool
            status = "missing"
            source = ""
            version = ""
            action = "install_or_fix_path"
        }
    }

    $output = ""
    $status = "ok"
    try {
        $output = (& $VersionCommand $cmd.Source 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) {
            $status = "fix_suggested"
        }
    }
    catch {
        $output = $_.Exception.Message
        if ($output -match "Access is denied|Отказано в доступе") {
            $status = "blocked"
        }
        else {
            $status = "fix_suggested"
        }
    }

    $action = switch ($status) {
        "ok" { "none" }
        "missing" { "install_or_fix_path" }
        "blocked" {
            if ($Tool -eq "rg") { "fallback_select_string_get_childitem" } else { "check_policy_or_permissions" }
        }
        default { "check_tool_output" }
    }

    return [pscustomobject]@{
        tool = $Tool
        status = $status
        source = $cmd.Source
        version = $output
        action = $action
    }
}

function Invoke-FirefoxCheck {
    $firefoxCommand = Resolve-ToolCommand -Tool "firefox.exe"
    if (-not $firefoxCommand) {
        $firefoxCommand = Resolve-ToolCommand -Tool "firefox"
    }

    $candidatePaths = @(
        (Join-Path $env:ProgramFiles "Mozilla Firefox\firefox.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Mozilla Firefox\firefox.exe")
    ) | Where-Object { $_ }

    $resolvedPath = ""
    if ($firefoxCommand) {
        $resolvedPath = $firefoxCommand.Source
    }
    else {
        foreach ($candidate in $candidatePaths) {
            if (Test-Path -LiteralPath $candidate) {
                $resolvedPath = $candidate
                break
            }
        }
    }

    if (-not $resolvedPath) {
        return [pscustomobject]@{
            tool = "firefox"
            status = "missing"
            source = ""
            version = ""
            action = "install_or_fix_path"
        }
    }

    $output = ""
    $status = "ok"
    try {
        $output = (& $resolvedPath --version 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) {
            $status = "fix_suggested"
        }
    }
    catch {
        $output = $_.Exception.Message
        $status = "fix_suggested"
    }

    return [pscustomobject]@{
        tool = "firefox"
        status = $status
        source = $resolvedPath
        version = $output
        action = if ($status -eq "ok") { "none" } else { "check_tool_output" }
    }
}

$checks = @(
    @{ tool = "rg"; cmd = { param($Executable) & $Executable --version } },
    @{ tool = "fd"; cmd = { param($Executable) & $Executable --version } },
    @{ tool = "yq"; cmd = { param($Executable) & $Executable --version } },
    @{ tool = "uv"; cmd = { param($Executable) & $Executable --version } },
    @{ tool = "pnpm"; cmd = { param($Executable) & $Executable --version } },
    @{ tool = "cmake"; cmd = { param($Executable) & $Executable --version } },
    @{ tool = "terraform"; cmd = { param($Executable) & $Executable --version } },
    @{ tool = "make"; cmd = { param($Executable) & $Executable --version } },
    @{ tool = "7z"; cmd = { param($Executable) & $Executable i | Select-Object -First 2 } },
    @{ tool = "git"; cmd = { param($Executable) & $Executable --version } },
    @{ tool = "python"; cmd = { param($Executable) & $Executable --version } },
    @{ tool = "node"; cmd = { param($Executable) & $Executable --version } },
    @{ tool = "npx"; cmd = { param($Executable) & $Executable --version } },
    @{ tool = "gh"; cmd = { param($Executable) & $Executable --version } },
    @{ tool = "go"; cmd = { param($Executable) & $Executable version } }
)

$rows = foreach ($item in $checks) {
    Invoke-ToolCheck -Tool $item.tool -VersionCommand $item.cmd
}

$rows += Invoke-FirefoxCheck

$firefoxReady = @($rows | Where-Object { $_.tool -in @("node", "npx", "firefox") -and $_.status -eq "ok" }).Count -eq 3
$rows += [pscustomobject]@{
    tool = "firefox_mcp_ready"
    status = if ($firefoxReady) { "ok" } else { "blocked" }
    source = "/int/tools/codex/bin/mcp-firefox-devtools.ps1"
    version = "node+npx+firefox"
    action = if ($firefoxReady) { "none" } else { "install_or_fix_path" }
}

if ($Json) {
    $rows | ConvertTo-Json -Depth 5
}
else {
    $rows | Format-Table tool, status, source, action -AutoSize
}

if (@($rows | Where-Object { $_.status -in @("missing", "blocked", "fix_suggested") }).Count -gt 0) {
    exit 20
}

exit 0
