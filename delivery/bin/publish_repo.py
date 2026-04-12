#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_checked(args: list[str], *, cwd: Path | None = None, capture: bool = False) -> str:
    completed = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=capture,
        check=False,
    )
    if completed.returncode != 0:
        detail = ""
        if capture:
            output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part).strip()
            if output:
                detail = f": {output}"
        raise RuntimeError(f"{' '.join(args)} failed{detail}")
    if capture:
        return completed.stdout.strip()
    return ""


def resolve_ssh_executable() -> str:
    if os.name == "nt":
        for candidate in ("ssh.cmd", "ssh.bat", "ssh.exe", "ssh"):
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
    return shutil.which("ssh") or "ssh"


def run_ssh_checked(host: str, command: str) -> None:
    completed = subprocess.run(
        [resolve_ssh_executable(), host, command],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part).strip()
        suffix = f": {output}" if output else ""
        raise RuntimeError(f"ssh {host} failed{suffix}")
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)


def git_capture(repo: Path, *git_args: str) -> str:
    return run_checked(["git", "-C", str(repo), *git_args], capture=True)


def git_run(repo: Path, *git_args: str) -> None:
    run_checked(["git", "-C", str(repo), *git_args])


def get_git_dir(repo: Path) -> Path:
    git_dir = git_capture(repo, "rev-parse", "--git-dir")
    git_path = Path(git_dir)
    return git_path if git_path.is_absolute() else repo / git_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform repository publish engine")
    parser.add_argument("--repo-path", required=True)
    parser.add_argument("--expected-branch", required=True)
    parser.add_argument("--expected-upstream", required=True)
    parser.add_argument("--success-label", required=True)
    parser.add_argument("--repo-name")
    parser.add_argument("--push-remote", default="origin")
    parser.add_argument("--push-branch", default="")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--no-deploy", action="store_true")
    parser.add_argument("--deploy-mode", choices=("none", "ssh-fast-forward"), default="none")
    parser.add_argument("--deploy-host", default="")
    parser.add_argument("--deploy-repo-path", default="")
    parser.add_argument("--deploy-fetch-ref", default="")
    parser.add_argument("--deploy-pull-ref", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    repo_path = Path(args.repo_path)
    repo_name = args.repo_name or repo_path.name
    actions: list[str] = []
    push_completed = False
    deploy_completed = False

    try:
        if not repo_path.exists():
            raise RuntimeError(f"repository path not found: {repo_path}")
        if not (repo_path / ".git").exists():
            raise RuntimeError(f"not a git repository: {repo_path}")

        git_run(repo_path, "fetch", "--prune", args.push_remote)

        branch = git_capture(repo_path, "branch", "--show-current")
        if branch != args.expected_branch:
            raise RuntimeError(f"current branch is '{branch}', expected '{args.expected_branch}'")

        upstream = git_capture(repo_path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        if upstream != args.expected_upstream:
            raise RuntimeError(f"upstream is '{upstream}', expected '{args.expected_upstream}'")

        git_dir = get_git_dir(repo_path)
        for marker in ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD", "rebase-apply", "rebase-merge"):
            if (git_dir / marker).exists():
                raise RuntimeError(f"merge/rebase operation in progress ({marker})")

        if args.require_clean:
            status = git_capture(repo_path, "status", "--porcelain", "--untracked-files=all")
            if status.strip():
                raise RuntimeError("working tree is not clean")

        counts_raw = git_capture(repo_path, "rev-list", "--left-right", "--count", f"{args.expected_upstream}...{args.expected_branch}")
        count_parts = [part for part in counts_raw.split() if part]
        if len(count_parts) < 2:
            raise RuntimeError(f"unexpected ahead/behind output: '{counts_raw}'")
        behind = int(count_parts[0])
        ahead = int(count_parts[1])

        if behind > 0:
            raise RuntimeError(f"branch is behind {args.expected_upstream} by {behind} commit(s)")

        push_branch = args.push_branch or args.expected_branch
        if ahead > 0:
            if args.no_push:
                actions.append(f"{repo_name}: ahead={ahead} behind={behind} (NoPush)")
            else:
                git_run(repo_path, "push", args.push_remote, f"{args.expected_branch}:{push_branch}")
                actions.append(f"{repo_name}: pushed {args.push_remote}/{push_branch} (ahead={ahead})")
                push_completed = True
        else:
            actions.append(f"{repo_name}: already up to date (ahead=0 behind=0)")

        if not args.no_deploy and args.deploy_mode != "none":
            if args.deploy_mode == "ssh-fast-forward":
                for name, value in (
                    ("deploy_host", args.deploy_host),
                    ("deploy_repo_path", args.deploy_repo_path),
                    ("deploy_fetch_ref", args.deploy_fetch_ref),
                    ("deploy_pull_ref", args.deploy_pull_ref),
                ):
                    if not value:
                        raise RuntimeError(f"{name} is required for deploy_mode={args.deploy_mode}")
                if args.no_push and ahead > 0:
                    raise RuntimeError("deploy requires remote branch to contain local HEAD; rerun without --no-push or add --no-deploy")

                ssh_command = (
                    f"cd {args.deploy_repo_path} && "
                    f"git fetch --prune origin {args.deploy_fetch_ref} && "
                    f"git pull --ff-only origin {args.deploy_pull_ref}"
                )
                run_ssh_checked(args.deploy_host, ssh_command)
                actions.append(f"{repo_name}: deployed via ssh-fast-forward to {args.deploy_host}:{args.deploy_repo_path}")
                deploy_completed = True

        print(f"{args.success_label} OK")
        for action in actions:
            print(f" - {action}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"{args.success_label} FAILED")
        print(f" - {repo_name}: {exc}")
        for action in actions:
            print(f" - completed: {action}")
        if push_completed and not deploy_completed and not args.no_deploy and args.deploy_mode != "none":
            print(f" - partial_state: push in {args.push_remote}/{args.push_branch or args.expected_branch} completed; deploy to {args.deploy_host}:{args.deploy_repo_path} did not finish")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
