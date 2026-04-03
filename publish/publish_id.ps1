[CmdletBinding()]
param(
    [switch]$NoPush,
    [switch]$NoDeploy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$enginePath = Join-Path $PSScriptRoot "publish_repo.ps1"

& $enginePath `
    -RepoPath "D:\int\id" `
    -RepoName "id" `
    -SuccessLabel "publish_id" `
    -ExpectedBranch "dev" `
    -ExpectedUpstream "origin/dev" `
    -PushRemote "origin" `
    -PushBranch "dev" `
    -RequireClean `
    -NoPush:$NoPush `
    -NoDeploy:$NoDeploy

exit $LASTEXITCODE
