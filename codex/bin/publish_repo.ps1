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

function Invoke-GitChecked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Repo,

        [Parameter(Mandatory = $true)]
        [string[]]$Args,

        [switch]$Capture
    )

    if ($Capture) {
        $output = (& git -C $Repo @Args 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) {
            $suffix = if ([string]::IsNullOrWhiteSpace($output)) { "" } else { ": $output" }
            throw "git $($Args -join ' ') failed$suffix"
        }

        return $output
    }

    & git -C $Repo @Args
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Args -join ' ') failed"
    }
}

function Get-GitDirPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoPath
    )

    $gitDir = Invoke-GitChecked -Repo $RepoPath -Args @("rev-parse", "--git-dir") -Capture
    if ([System.IO.Path]::IsPathRooted($gitDir)) {
        return $gitDir
    }

    return (Join-Path $RepoPath $gitDir)
}

function Invoke-SshChecked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SshHost,

        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    & ssh $SshHost $Command
    if ($LASTEXITCODE -ne 0) {
        throw "ssh $SshHost failed"
    }
}

$resolvedRepoName = if ([string]::IsNullOrWhiteSpace($RepoName)) {
    Split-Path $RepoPath -Leaf
}
else {
    $RepoName
}

$actions = [System.Collections.Generic.List[string]]::new()
$pushCompleted = $false
$deployCompleted = $false

try {
    if (-not (Test-Path $RepoPath)) {
        throw "repository path not found: $RepoPath"
    }

    if (-not (Test-Path (Join-Path $RepoPath ".git"))) {
        throw "not a git repository: $RepoPath"
    }

    Invoke-GitChecked -Repo $RepoPath -Args @("fetch", "--prune", $PushRemote)

    $branch = Invoke-GitChecked -Repo $RepoPath -Args @("branch", "--show-current") -Capture
    if ($branch -ne $ExpectedBranch) {
        throw "current branch is '$branch', expected '$ExpectedBranch'"
    }

    $upstream = Invoke-GitChecked -Repo $RepoPath -Args @("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}") -Capture
    if ($upstream -ne $ExpectedUpstream) {
        throw "upstream is '$upstream', expected '$ExpectedUpstream'"
    }

    $gitDir = Get-GitDirPath -RepoPath $RepoPath
    foreach ($marker in @("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD", "rebase-apply", "rebase-merge")) {
        if (Test-Path (Join-Path $gitDir $marker)) {
            throw "merge/rebase operation in progress ($marker)"
        }
    }

    if ($RequireClean) {
        $status = Invoke-GitChecked -Repo $RepoPath -Args @("status", "--porcelain", "--untracked-files=all") -Capture
        if (-not [string]::IsNullOrWhiteSpace($status)) {
            throw "working tree is not clean"
        }
    }

    $countsRaw = Invoke-GitChecked -Repo $RepoPath -Args @("rev-list", "--left-right", "--count", "$ExpectedUpstream...$ExpectedBranch") -Capture
    $countParts = $countsRaw -split "\s+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    if ($countParts.Count -lt 2) {
        throw "unexpected ahead/behind output: '$countsRaw'"
    }

    $behind = [int]$countParts[0]
    $ahead = [int]$countParts[1]

    if ($behind -gt 0) {
        throw "branch is behind $ExpectedUpstream by $behind commit(s)"
    }

    if ($ahead -gt 0) {
        if ($NoPush) {
            $actions.Add("${resolvedRepoName}: ahead=$ahead behind=$behind (NoPush)")
        }
        else {
            Invoke-GitChecked -Repo $RepoPath -Args @("push", $PushRemote, "${ExpectedBranch}:$PushBranch")
            $actions.Add("${resolvedRepoName}: pushed $PushRemote/$PushBranch (ahead=$ahead)")
            $pushCompleted = $true
        }
    }
    else {
        $actions.Add("${resolvedRepoName}: already up to date (ahead=0 behind=0)")
    }

    if (-not $NoDeploy -and $DeployMode -ne "none") {
        if ($DeployMode -eq "ssh-fast-forward") {
            foreach ($required in @(
                @{ Name = "DeployHost"; Value = $DeployHost },
                @{ Name = "DeployRepoPath"; Value = $DeployRepoPath },
                @{ Name = "DeployFetchRef"; Value = $DeployFetchRef },
                @{ Name = "DeployPullRef"; Value = $DeployPullRef }
            )) {
                if ([string]::IsNullOrWhiteSpace($required.Value)) {
                    throw "$($required.Name) is required for DeployMode=$DeployMode"
                }
            }

            if ($NoPush -and $ahead -gt 0) {
                throw "deploy requires remote branch to contain local HEAD; rerun without -NoPush or add -NoDeploy"
            }

            $sshCommand = "cd $DeployRepoPath && git fetch --prune origin $DeployFetchRef && git pull --ff-only origin $DeployPullRef"
            Invoke-SshChecked -SshHost $DeployHost -Command $sshCommand
            $actions.Add("${resolvedRepoName}: deployed via ssh-fast-forward to ${DeployHost}:${DeployRepoPath}")
            $deployCompleted = $true
        }
    }

    Write-Host "$SuccessLabel OK" -ForegroundColor Green
    foreach ($action in $actions) {
        Write-Host " - $action"
    }
    exit 0
}
catch {
    Write-Host "$SuccessLabel FAILED" -ForegroundColor Red
    Write-Host " - ${resolvedRepoName}: $($_.Exception.Message)"
    foreach ($action in $actions) {
        Write-Host " - completed: $action"
    }
    if ($pushCompleted -and -not $deployCompleted -and -not $NoDeploy -and $DeployMode -ne "none") {
        Write-Host " - partial_state: push in $PushRemote/$PushBranch completed; deploy to ${DeployHost}:${DeployRepoPath} did not finish"
    }
    exit 1
}
