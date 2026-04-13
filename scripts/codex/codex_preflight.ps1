param(
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function Invoke-ToolCheck {
    param(
        [Parameter(Mandatory = $true)][string]$Tool,
        [Parameter(Mandatory = $true)][scriptblock]$VersionCommand
    )

    $cmd = Get-Command $Tool -ErrorAction SilentlyContinue
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
        $output = (& $VersionCommand 2>&1 | Out-String).Trim()
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
    $firefoxCommand = Get-Command firefox.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $firefoxCommand) {
        $firefoxCommand = Get-Command firefox -ErrorAction SilentlyContinue | Select-Object -First 1
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
    @{ tool = "rg"; cmd = { rg --version } },
    @{ tool = "fd"; cmd = { fd --version } },
    @{ tool = "yq"; cmd = { yq --version } },
    @{ tool = "uv"; cmd = { uv --version } },
    @{ tool = "pnpm"; cmd = { pnpm --version } },
    @{ tool = "cmake"; cmd = { cmake --version } },
    @{ tool = "terraform"; cmd = { terraform --version } },
    @{ tool = "make"; cmd = { make --version } },
    @{ tool = "7z"; cmd = { 7z i | Select-Object -First 2 } },
    @{ tool = "git"; cmd = { git --version } },
    @{ tool = "python"; cmd = { python --version } },
    @{ tool = "node"; cmd = { node --version } },
    @{ tool = "npx"; cmd = { npx --version } },
    @{ tool = "gh"; cmd = { gh --version } },
    @{ tool = "go"; cmd = { go version } }
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
