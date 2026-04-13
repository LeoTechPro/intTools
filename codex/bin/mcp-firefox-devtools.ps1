[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]*$')]
    [string]$ProfileKey,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https?://')]
    [string]$StartUrl,

    [ValidatePattern('^[0-9]{3,5}x[0-9]{3,5}$')]
    [string]$Viewport = "1440x900",

    [switch]$Visible,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runtimeRoot = "D:\int\.runtime\firefox-mcp"
$profilesRoot = Join-Path $runtimeRoot "profiles"
$logsRoot = Join-Path $runtimeRoot "logs"
$runRoot = Join-Path $runtimeRoot "run"
$profilePath = Join-Path $profilesRoot $ProfileKey
$logDir = Join-Path $logsRoot $ProfileKey
$runMetaPath = Join-Path $runRoot "$ProfileKey.json"
$stderrLogPath = Join-Path $logDir "stderr.log"
$packageSpec = "firefox-devtools-mcp@0.9.1"

function Ensure-Directory {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Get-RequiredCommandPath {
    param([Parameter(Mandatory = $true)][string]$Name)

    $command = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $command) {
        throw "Required tool '$Name' was not found in PATH."
    }

    return $command.Source
}

function Resolve-FirefoxBinary {
    $command = Get-Command firefox.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) {
        return $command.Source
    }

    $command = Get-Command firefox -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) {
        return $command.Source
    }

    $candidates = @(
        (Join-Path $env:ProgramFiles "Mozilla Firefox\firefox.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Mozilla Firefox\firefox.exe")
    ) | Where-Object { $_ }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "Firefox executable was not found. Install Firefox 100+ or add firefox.exe to PATH."
}

function Test-PidAlive {
    param([Parameter(Mandatory = $true)][int]$Pid)

    try {
        Get-Process -Id $Pid -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Remove-StaleRunMeta {
    if (-not (Test-Path -LiteralPath $runMetaPath)) {
        return
    }

    $raw = Get-Content -Raw -LiteralPath $runMetaPath | ConvertFrom-Json
    $existingPid = 0
    try {
        $existingPid = [int]$raw.pid
    }
    catch {
        $existingPid = 0
    }

    if ($existingPid -gt 0 -and (Test-PidAlive -Pid $existingPid)) {
        throw "Firefox MCP profile '$ProfileKey' is already active under PID $existingPid."
    }

    Remove-Item -LiteralPath $runMetaPath -Force -ErrorAction SilentlyContinue
}

function Quote-CmdToken {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value -notmatch '[\s"&|<>^]') {
        return $Value
    }

    return '"' + $Value.Replace('"', '""') + '"'
}

Ensure-Directory -Path $profilesRoot
Ensure-Directory -Path $logsRoot
Ensure-Directory -Path $runRoot
Ensure-Directory -Path $profilePath
Ensure-Directory -Path $logDir

$nodePath = Get-RequiredCommandPath -Name "node"
$npxPath = Get-RequiredCommandPath -Name "npx"
$firefoxPath = Resolve-FirefoxBinary
$firefoxDir = Split-Path -Parent $firefoxPath

if (($env:PATH -split ';') -notcontains $firefoxDir) {
    $env:PATH = "$firefoxDir;$env:PATH"
}

Remove-StaleRunMeta

$npxArgs = @(
    "-y",
    $packageSpec,
    "--firefox-path",
    $firefoxPath,
    "--profile-path",
    $profilePath,
    "--start-url",
    $StartUrl,
    "--viewport",
    $Viewport
)

if (-not $Visible) {
    $npxArgs += "--headless"
}

$commandParts = @("npx") + ($npxArgs | ForEach-Object { Quote-CmdToken -Value $_ })
$cmdLine = (($commandParts -join " ") + " 2>> " + (Quote-CmdToken -Value $stderrLogPath)).Trim()

$meta = [ordered]@{
    profile_key = $ProfileKey
    pid = $PID
    start_url = $StartUrl
    viewport = $Viewport
    visible = [bool]$Visible
    profile_path = $profilePath
    log_path = $stderrLogPath
    launched_utc = (Get-Date).ToUniversalTime().ToString("o")
    command = "cmd.exe /d /s /c"
    command_line = $cmdLine
    package = $packageSpec
    tool_paths = [ordered]@{
        node = $nodePath
        npx = $npxPath
        firefox = $firefoxPath
    }
}

if ($DryRun) {
    $meta | ConvertTo-Json -Depth 6
    exit 0
}

Add-Content -LiteralPath $stderrLogPath -Value ("[{0}] launch profile={1} start_url={2} viewport={3} visible={4}" -f (Get-Date).ToUniversalTime().ToString("o"), $ProfileKey, $StartUrl, $Viewport, [bool]$Visible)
$meta | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $runMetaPath -Encoding utf8

$exitCode = 0
try {
    & cmd.exe /d /s /c $cmdLine
    $exitCode = $LASTEXITCODE
}
finally {
    Remove-Item -LiteralPath $runMetaPath -Force -ErrorAction SilentlyContinue
}

exit $exitCode
