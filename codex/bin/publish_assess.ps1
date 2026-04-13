[CmdletBinding()]
param(
    [switch]$NoPush,
    [switch]$NoDeploy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$enginePath = Join-Path $PSScriptRoot "publish_repo.ps1"

& $enginePath `
    -RepoPath "D:\int\assess" `
    -RepoName "assess" `
    -SuccessLabel "publish_assess" `
    -ExpectedBranch "dev" `
    -ExpectedUpstream "origin/dev" `
    -PushRemote "origin" `
    -PushBranch "dev" `
    -RequireClean `
    -NoPush:$NoPush `
    -NoDeploy:$NoDeploy `
    -DeployMode "ssh-fast-forward" `
    -DeployHost "vds-intdata-intdata" `
    -DeployRepoPath "/int/assess" `
    -DeployFetchRef "dev" `
    -DeployPullRef "dev"

exit $LASTEXITCODE
