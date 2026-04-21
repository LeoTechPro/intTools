[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoPath,

    [Parameter(Mandatory = $true)]
    [string]$ExpectedBranch,

    [Parameter(Mandatory = $true)]
    [string]$ExpectedUpstream,

    [Parameter(Mandatory = $true)]
    [string]$SuccessLabel,

    [string]$RepoName,
    [string]$PushRemote = "origin",
    [string]$PushBranch = "",
    [switch]$RequireClean,
    [switch]$NoPush,
    [switch]$NoDeploy,

    [ValidateSet("none", "ssh-fast-forward")]
    [string]$DeployMode = "none",

    [string]$DeployHost = "",
    [string]$DeployRepoPath = "",
    [string]$DeployFetchRef = "",
    [string]$DeployPullRef = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "python runtime is required for publish_repo adapter"
}

$enginePath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\delivery\bin\publish_repo.py"))
if (-not (Test-Path -LiteralPath $enginePath)) {
    throw "publish_repo engine not found: $enginePath"
}

$cliArgs = @(
    $enginePath,
    "--repo-path", $RepoPath,
    "--expected-branch", $ExpectedBranch,
    "--expected-upstream", $ExpectedUpstream,
    "--success-label", $SuccessLabel
)

if (-not [string]::IsNullOrWhiteSpace($RepoName)) { $cliArgs += @("--repo-name", $RepoName) }
if (-not [string]::IsNullOrWhiteSpace($PushRemote)) { $cliArgs += @("--push-remote", $PushRemote) }
if (-not [string]::IsNullOrWhiteSpace($PushBranch)) { $cliArgs += @("--push-branch", $PushBranch) }
if ($RequireClean) { $cliArgs += "--require-clean" }
if ($NoPush) { $cliArgs += "--no-push" }
if ($NoDeploy) { $cliArgs += "--no-deploy" }
if (-not [string]::IsNullOrWhiteSpace($DeployMode)) { $cliArgs += @("--deploy-mode", $DeployMode) }
if (-not [string]::IsNullOrWhiteSpace($DeployHost)) { $cliArgs += @("--deploy-host", $DeployHost) }
if (-not [string]::IsNullOrWhiteSpace($DeployRepoPath)) { $cliArgs += @("--deploy-repo-path", $DeployRepoPath) }
if (-not [string]::IsNullOrWhiteSpace($DeployFetchRef)) { $cliArgs += @("--deploy-fetch-ref", $DeployFetchRef) }
if (-not [string]::IsNullOrWhiteSpace($DeployPullRef)) { $cliArgs += @("--deploy-pull-ref", $DeployPullRef) }

if ($python.Name -eq "py.exe" -or $python.Name -eq "py") {
    & $python.Path -3 @cliArgs
}
else {
    & $python.Path @cliArgs
}

exit $LASTEXITCODE
