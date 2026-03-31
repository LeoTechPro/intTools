param(
    [switch]$AllowUserFallback,
    [switch]$Json,
    [string]$IntRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($IntRoot)) {
    $IntRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-WingetInstall {
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][ValidateSet("machine", "user")][string]$Scope
    )
    $null = & winget install --id $Id -e --scope $Scope --accept-package-agreements --accept-source-agreements --silent
    return [int]$LASTEXITCODE
}

function Get-StatusByCode {
    param([int]$Code)
    switch ($Code) {
        0 { "ok"; break }
        -1978335189 { "ok"; break } # no newer package
        -1978335207 { "admin_required"; break }
        -1978335216 { "unsupported_scope"; break }
        default { "failed" }
    }
}

function Install-PortableCMake {
    param([string]$Version = "4.3.1")
    $base = Join-Path $env:LOCALAPPDATA "Programs\PortableTools\cmake"
    New-Item -ItemType Directory -Force -Path $base | Out-Null
    $zipPath = Join-Path $env:TEMP "cmake-$Version.zip"
    $url = "https://github.com/Kitware/CMake/releases/download/v$Version/cmake-$Version-windows-x86_64.zip"
    Invoke-WebRequest -Uri $url -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $base -Force
    $root = Get-ChildItem $base -Directory | Where-Object { $_.Name -like "cmake-$Version*" } | Select-Object -First 1
    if (-not $root) {
        throw "Portable CMake extraction failed."
    }
    return (Join-Path $root.FullName "bin")
}

function Resolve-PortableCMakeBin {
    param([string]$Version = "4.3.1")
    $base = Join-Path $env:LOCALAPPDATA "Programs\PortableTools\cmake"
    if (-not (Test-Path $base)) {
        return $null
    }
    $preferredExe = Join-Path $base "cmake-$Version-windows-x86_64\bin\cmake.exe"
    if (Test-Path $preferredExe) {
        return (Split-Path -Parent $preferredExe)
    }
    $existing = Get-ChildItem $base -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "cmake-$Version*" } | Sort-Object Name -Descending | Select-Object -First 1
    if (-not $existing) {
        return $null
    }
    $candidateExe = Join-Path $existing.FullName "bin\cmake.exe"
    if (Test-Path $candidateExe) {
        return (Split-Path -Parent $candidateExe)
    }
    return $null
}

function Normalize-UserPath {
    param(
        [string[]]$HeadEntries,
        [string[]]$DropEntries
    )

    $userRaw = [Environment]::GetEnvironmentVariable("Path", "User")
    $machineRaw = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $all = @()
    if ($HeadEntries) { $all += $HeadEntries }
    if ($userRaw) { $all += ($userRaw -split ";") }

    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $dropRaw = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $dropExpanded = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in @($DropEntries)) {
        if ([string]::IsNullOrWhiteSpace($entry)) { continue }
        $trimmed = $entry.Trim()
        [void]$dropRaw.Add($trimmed)
        $expanded = [Environment]::ExpandEnvironmentVariables($trimmed)
        if (-not [string]::IsNullOrWhiteSpace($expanded)) {
            [void]$dropExpanded.Add($expanded)
        }
    }
    $final = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in $all) {
        if ([string]::IsNullOrWhiteSpace($entry)) { continue }
        $candidate = $entry.Trim()
        $expandedCandidate = [Environment]::ExpandEnvironmentVariables($candidate)
        $hasEnvToken = $candidate -match "%[^%]+%"
        $compareKey = $candidate

        if ($hasEnvToken) {
            if ($expandedCandidate -eq $candidate) {
                # Keep unresolved %VAR% tokens to avoid dropping valid entries for future sessions.
                $compareKey = $candidate
            }
            elseif (Test-Path $expandedCandidate) {
                $compareKey = $expandedCandidate
            }
            else {
                continue
            }
        }
        else {
            if (-not (Test-Path $candidate)) { continue }
            $compareKey = $candidate
        }

        if (
            $dropRaw.Contains($candidate) -or
            $dropExpanded.Contains($candidate) -or
            $dropRaw.Contains($compareKey) -or
            $dropExpanded.Contains($compareKey)
        ) {
            continue
        }

        if ($seen.Add($compareKey)) {
            [void]$final.Add($candidate)
        }
    }

    $newUserPath = ($final -join ";")
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
    $env:Path = "$newUserPath;$machineRaw"
    return $newUserPath
}

$results = [System.Collections.Generic.List[object]]::new()
$isAdmin = Test-IsAdmin

if (-not $isAdmin -and -not $AllowUserFallback) {
    $msg = "Elevation required. Re-run in elevated PowerShell or use -AllowUserFallback."
    if ($Json) {
        [pscustomobject]@{
            ok = $false
            code = 10
            message = $msg
        } | ConvertTo-Json -Depth 4
    }
    else {
        Write-Host $msg
    }
    exit 10
}

$scope = if ($isAdmin) { "machine" } else { "user" }
$utc = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$backupDir = Join-Path $IntRoot ".tmp\toolchain-bootstrap\$utc"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$pathSnapshot = [pscustomobject]@{
    created_utc = $utc
    user_path = [Environment]::GetEnvironmentVariable("Path", "User")
    machine_path = [Environment]::GetEnvironmentVariable("Path", "Machine")
    process_path = $env:Path
}
$pathSnapshot | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $backupDir "path-backup.json") -Encoding UTF8
$effectivePathParts = @(
    [Environment]::GetEnvironmentVariable("Path", "User"),
    [Environment]::GetEnvironmentVariable("Path", "Machine")
) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
$env:Path = ($effectivePathParts -join ";")

$wingetPackages = @(
    "BurntSushi.ripgrep.MSVC",
    "sharkdp.fd",
    "MikeFarah.yq",
    "astral-sh.uv",
    "pnpm.pnpm",
    "Kitware.CMake",
    "7zip.7zip",
    "Hashicorp.Terraform"
)

foreach ($pkg in $wingetPackages) {
    $code = Invoke-WingetInstall -Id $pkg -Scope $scope
    $status = Get-StatusByCode -Code $code
    $note = ""
    if ($status -eq "admin_required") {
        $note = "Need elevated shell for machine scope."
    }
    elseif ($status -eq "unsupported_scope") {
        $note = "Package has no user-scope installer."
    }
    $results.Add([pscustomobject]@{
            tool = $pkg
            manager = "winget"
            scope = $scope
            code = $code
            status = $status
            note = $note
        })
}

$makeCode = 1
if ($isAdmin -and (Get-Command choco -ErrorAction SilentlyContinue)) {
    & choco install make -y --no-progress
    $makeCode = $LASTEXITCODE
}
$makeStatus = Get-StatusByCode -Code $makeCode
if ($makeStatus -ne "ok") {
    $makeCode = Invoke-WingetInstall -Id "ezwinports.make" -Scope $scope
    $makeStatus = Get-StatusByCode -Code $makeCode
}
$results.Add([pscustomobject]@{
        tool = "make"
        manager = "choco+winget-fallback"
        scope = $scope
        code = $makeCode
        status = $makeStatus
        note = ""
    })

$cmakeBinHint = Resolve-PortableCMakeBin
$cmakeCmd = Get-Command cmake -ErrorAction SilentlyContinue
if (-not $cmakeCmd -and $cmakeBinHint) {
    $env:Path = "$cmakeBinHint;$env:Path"
    $cmakeCmd = Get-Command cmake -ErrorAction SilentlyContinue
}
if (-not $cmakeCmd -and $scope -eq "user") {
    try {
        $cmakeBinHint = Install-PortableCMake
        $results.Add([pscustomobject]@{
                tool = "portable-cmake"
                manager = "manual"
                scope = "user"
                code = 0
                status = "ok"
                note = "Installed portable CMake."
            })
    }
    catch {
        $results.Add([pscustomobject]@{
                tool = "portable-cmake"
                manager = "manual"
                scope = "user"
                code = 1
                status = "failed"
                note = $_.Exception.Message
            })
    }
}
elseif ($cmakeBinHint) {
    $results.Add([pscustomobject]@{
            tool = "portable-cmake"
            manager = "manual"
            scope = "user"
            code = 0
            status = "ok"
            note = "Reused existing portable CMake."
        })
}

$sevenCmd = Get-Command 7z -ErrorAction SilentlyContinue
if (-not $sevenCmd -and $scope -eq "user") {
    $nanoCode = Invoke-WingetInstall -Id "M2Team.NanaZip" -Scope "user"
    $results.Add([pscustomobject]@{
            tool = "M2Team.NanaZip"
            manager = "winget"
            scope = "user"
            code = $nanoCode
            status = (Get-StatusByCode -Code $nanoCode)
            note = "7z alias provider for user scope."
        })
}

$headEntries = @(
    (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links"),
    (Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps")
)
if ($cmakeBinHint -and (Test-Path $cmakeBinHint)) {
    $headEntries = @($cmakeBinHint) + $headEntries
}
$dropEntries = @(
    (Join-Path $env:LOCALAPPDATA "OpenAI\Codex\bin")
)
$newUserPath = Normalize-UserPath -HeadEntries $headEntries -DropEntries $dropEntries

$resultsPath = Join-Path $backupDir "install-results.json"
$results | ConvertTo-Json -Depth 5 | Set-Content -Path $resultsPath -Encoding UTF8

$hasFailure = @($results | Where-Object { $_.status -eq "failed" }).Count -gt 0
$hasAdminRequired = @($results | Where-Object { $_.status -eq "admin_required" }).Count -gt 0

$payload = [pscustomobject]@{
    ok = (-not $hasFailure)
    code = if ($hasFailure) { 20 } elseif ($hasAdminRequired -and -not $isAdmin) { 10 } else { 0 }
    is_admin = $isAdmin
    scope = $scope
    backup_dir = $backupDir
    results_file = $resultsPath
    new_user_path = $newUserPath
    results = $results
}

if ($Json) {
    $payload | ConvertTo-Json -Depth 6
}
else {
    $results | Format-Table tool, manager, scope, status, code, note -AutoSize
    Write-Host "backup_dir: $backupDir"
    Write-Host "results_file: $resultsPath"
}

exit $payload.code
