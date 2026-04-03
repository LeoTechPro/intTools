[CmdletBinding()]
param(
    [switch]$NoPush,
    [switch]$NoDeploy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$enginePath = Join-Path $PSScriptRoot "publish_repo.ps1"

& $enginePath `
    -RepoPath "D:\int\data" `
    -RepoName "data" `
    -SuccessLabel "publish_data" `
    -ExpectedBranch "main" `
    -ExpectedUpstream "origin/main" `
    -PushRemote "origin" `
    -PushBranch "main" `
    -RequireClean `
    -NoPush:$NoPush `
    -NoDeploy:$NoDeploy `
    -DeployMode "ssh-fast-forward" `
    -DeployHost "vds.intdata.pro" `
    -DeployRepoPath "/int/data" `
    -DeployFetchRef "main" `
    -DeployPullRef "main"

exit $LASTEXITCODE
