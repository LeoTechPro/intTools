param(
    [ValidateSet("start", "finish")]
    [string]$Stage = "start",

    [string]$RootPath = "",

    [string[]]$Repos = @(),

    [switch]$Push,

    [switch]$DryRun,

    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-RootPath {
    param([string]$ExplicitRoot)

    if (-not [string]::IsNullOrWhiteSpace($ExplicitRoot)) {
        return [System.IO.Path]::GetFullPath($ExplicitRoot)
    }

    foreach ($candidate in @("/int", "D:/int")) {
        if (Test-Path -LiteralPath $candidate) {
            return [System.IO.Path]::GetFullPath($candidate)
        }
    }

    return [System.IO.Path]::GetFullPath((Get-Location).Path)
}

function Get-RepoCandidates {
    param(
        [string]$ResolvedRoot,
        [string[]]$ExplicitRepos
    )

    if ($ExplicitRepos.Count -gt 0) {
        return @($ExplicitRepos | ForEach-Object { [System.IO.Path]::GetFullPath($_) })
    }

    $topLevel = Get-ChildItem -Path $ResolvedRoot -Directory -ErrorAction SilentlyContinue
    return @(
        $topLevel |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName ".git") } |
        ForEach-Object { [System.IO.Path]::GetFullPath($_.FullName) }
    )
}

function Invoke-GitCapture {
    param(
        [string]$RepoPath,
        [string[]]$GitArgs
    )

    $output = (& git -C $RepoPath @GitArgs 2>&1 | Out-String).Trim()
    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output = $output
    }
}

function Parse-AheadBehind {
    param([string]$RawCounts)

    $parts = $RawCounts -split "\s+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    if ($parts.Count -lt 2) {
        throw "unexpected ahead/behind output: '$RawCounts'"
    }

    return [pscustomobject]@{
        Behind = [int]$parts[0]
        Ahead = [int]$parts[1]
    }
}

function New-Result {
    param(
        [string]$RepoPath,
        [string]$StageName
    )

    return [ordered]@{
        repo = $RepoPath
        stage = $StageName
        branch = ""
        upstream = ""
        clean = $false
        ahead = 0
        behind = 0
        status = "pending"
        actions = @()
        error = ""
    }
}

$resolvedRoot = Resolve-RootPath -ExplicitRoot $RootPath
$repoCandidates = @(Get-RepoCandidates -ResolvedRoot $resolvedRoot -ExplicitRepos $Repos)

if ($repoCandidates.Count -eq 0) {
    Write-Error "No git repositories found for gate under '$resolvedRoot'."
    exit 2
}

$results = @()

foreach ($repo in $repoCandidates) {
    $result = New-Result -RepoPath $repo -StageName $Stage
    $actions = New-Object System.Collections.Generic.List[string]

    try {
        if (-not (Test-Path -LiteralPath $repo)) {
            throw "repository path does not exist"
        }

        if (-not (Test-Path -LiteralPath (Join-Path $repo ".git"))) {
            throw "not a git repository"
        }

        $branchProbe = Invoke-GitCapture -RepoPath $repo -GitArgs @("branch", "--show-current")
        if ($branchProbe.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($branchProbe.Output)) {
            throw "cannot resolve current branch"
        }
        $branch = $branchProbe.Output.Trim()
        $result.branch = $branch

        $upstreamProbe = Invoke-GitCapture -RepoPath $repo -GitArgs @("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        if ($upstreamProbe.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($upstreamProbe.Output)) {
            throw "upstream is not configured"
        }
        $upstream = $upstreamProbe.Output.Trim()
        $result.upstream = $upstream

        $statusProbe = Invoke-GitCapture -RepoPath $repo -GitArgs @("status", "--porcelain", "--untracked-files=all")
        if ($statusProbe.ExitCode -ne 0) {
            throw "git status failed: $($statusProbe.Output)"
        }
        $isClean = [string]::IsNullOrWhiteSpace($statusProbe.Output)
        $result.clean = $isClean

        $countProbe = Invoke-GitCapture -RepoPath $repo -GitArgs @("rev-list", "--left-right", "--count", "$upstream...$branch")
        if ($countProbe.ExitCode -ne 0) {
            throw "cannot evaluate ahead/behind: $($countProbe.Output)"
        }
        $counts = Parse-AheadBehind -RawCounts $countProbe.Output
        $result.behind = $counts.Behind
        $result.ahead = $counts.Ahead

        if ($Stage -eq "start") {
            if (-not $isClean) {
                throw "working tree is not clean (start gate requires clean tree before pull)"
            }
            if ($counts.Ahead -gt 0) {
                throw "unpushed commits detected (ahead=$($counts.Ahead)); push previous work before new session"
            }

            if ($DryRun) {
                $actions.Add("dry-run: would run git pull --ff-only")
            }
            else {
                $pullProbe = Invoke-GitCapture -RepoPath $repo -GitArgs @("pull", "--ff-only")
                if ($pullProbe.ExitCode -ne 0) {
                    throw "git pull --ff-only failed: $($pullProbe.Output)"
                }
                $actions.Add("git pull --ff-only")

                $postCountProbe = Invoke-GitCapture -RepoPath $repo -GitArgs @("rev-list", "--left-right", "--count", "$upstream...$branch")
                if ($postCountProbe.ExitCode -eq 0) {
                    $postCounts = Parse-AheadBehind -RawCounts $postCountProbe.Output
                    $result.behind = $postCounts.Behind
                    $result.ahead = $postCounts.Ahead
                }
                if ($result.behind -gt 0 -or $result.ahead -gt 0) {
                    throw "repository is not synchronized after pull (behind=$($result.behind), ahead=$($result.ahead))"
                }
            }
        }
        else {
            if (-not $isClean) {
                throw "working tree is not clean (finish gate requires commit/stage discipline before push)"
            }
            if ($counts.Behind -gt 0) {
                throw "branch is behind upstream (behind=$($counts.Behind)); run start gate/rebase before finish"
            }

            if ($counts.Ahead -gt 0) {
                if (-not $Push) {
                    throw "unpushed commits detected (ahead=$($counts.Ahead)); rerun finish gate with -Push"
                }

                if ($DryRun) {
                    $actions.Add("dry-run: would run git push")
                }
                else {
                    $pushProbe = Invoke-GitCapture -RepoPath $repo -GitArgs @("push")
                    if ($pushProbe.ExitCode -ne 0) {
                        throw "git push failed: $($pushProbe.Output)"
                    }
                    $actions.Add("git push")

                    $postCountProbe = Invoke-GitCapture -RepoPath $repo -GitArgs @("rev-list", "--left-right", "--count", "$upstream...$branch")
                    if ($postCountProbe.ExitCode -eq 0) {
                        $postCounts = Parse-AheadBehind -RawCounts $postCountProbe.Output
                        $result.behind = $postCounts.Behind
                        $result.ahead = $postCounts.Ahead
                    }
                    if ($result.ahead -gt 0 -or $result.behind -gt 0) {
                        throw "repository is not synchronized after push (behind=$($result.behind), ahead=$($result.ahead))"
                    }
                }
            }
            else {
                $actions.Add("no local commits to push")
            }
        }

        $result.status = "ok"
        $result.actions = @($actions.ToArray())
    }
    catch {
        $result.status = "blocked"
        $result.error = $_.Exception.Message
        $result.actions = @($actions.ToArray())
    }

    $results += [pscustomobject]$result
}

$blocked = @($results | Where-Object { $_.status -ne "ok" })

if ($Json) {
    $results | ConvertTo-Json -Depth 6
}
else {
    $results | Format-Table repo, stage, status, branch, upstream, clean, behind, ahead -AutoSize
    foreach ($item in $results) {
        if ($item.actions.Count -gt 0) {
            Write-Host "[$($item.repo)] actions: $($item.actions -join '; ')"
        }
        if (-not [string]::IsNullOrWhiteSpace($item.error)) {
            Write-Host "[$($item.repo)] error: $($item.error)" -ForegroundColor Red
        }
    }
}

if ($blocked.Count -gt 0) {
    exit 20
}

exit 0
