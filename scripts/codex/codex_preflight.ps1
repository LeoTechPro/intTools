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
    @{ tool = "gh"; cmd = { gh --version } },
    @{ tool = "go"; cmd = { go version } }
)

$rows = foreach ($item in $checks) {
    Invoke-ToolCheck -Tool $item.tool -VersionCommand $item.cmd
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
