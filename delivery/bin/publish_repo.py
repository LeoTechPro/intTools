#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def normalize_cli_args(argv: list[str]) -> list[str]:
    """Allow PowerShell-style single-dash options (e.g. -NoPush) for backward compatibility."""
    switch_map = {
        "requireclean": "--require-clean",
        "nopush": "--no-push",
        "nodeploy": "--no-deploy",
    }
    value_map = {
        "repopath": "--repo-path",
        "expectedbranch": "--expected-branch",
        "expectedupstream": "--expected-upstream",
        "successlabel": "--success-label",
        "reponame": "--repo-name",
        "pushremote": "--push-remote",
        "pushbranch": "--push-branch",
        "deploymode": "--deploy-mode",
        "deployhost": "--deploy-host",
        "deployrepopath": "--deploy-repo-path",
        "deployfetchref": "--deploy-fetch-ref",
        "deploypullref": "--deploy-pull-ref",
    }

    def normalize_key(raw: str) -> str:
        return raw.strip().lower().replace("-", "").replace("_", "")

    normalized: list[str] = []
    i = 0
    while i < len(argv):
        token = argv[i]
        if not token.startswith("-") or token.startswith("--"):
            normalized.append(token)
            i += 1
            continue

        body = token[1:]
        if ":" in body:
            key_raw, inline_value = body.split(":", 1)
        else:
            key_raw, inline_value = body, None
        key = normalize_key(key_raw)

        if key in switch_map:
            if inline_value is None:
                normalized.append(switch_map[key])
            else:
                decision = inline_value.strip().lower()
                if decision in ("1", "true", "$true", "yes", "on"):
                    normalized.append(switch_map[key])
            i += 1
            continue

        if key in value_map:
            normalized.append(value_map[key])
            if inline_value is not None:
                normalized.append(inline_value)
                i += 1
                continue
            if i + 1 >= len(argv):
                normalized.append(token)
                i += 1
                continue
            normalized.append(argv[i + 1])
            i += 2
            continue

        normalized.append(token)
        i += 1

    return normalized


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


def get_int_ssh_mode() -> str:
    mode = os.getenv("INT_SSH_MODE", "auto").strip().lower()
    if mode in ("auto", "tailnet", "public"):
        return mode
    return "auto"


def get_int_ssh_probe_timeout_sec() -> int:
    raw = os.getenv("INT_SSH_PROBE_TIMEOUT_SEC", "4").strip()
    try:
        value = int(raw)
    except ValueError:
        return 4
    return max(1, min(30, value))


def resolve_int_ssh_target(requested_host: str) -> dict[str, object]:
    logical_map = {
        "vds-intdata-intdata": "dev-intdata",
        "vds-intdata-codex": "dev-codex",
        "vds-intdata-openclaw": "dev-openclaw",
        "prod": "prod-leon",
        "vds.punkt-b.pro": "prod-leon",
        "dev-intdata": "dev-intdata",
        "dev-codex": "dev-codex",
        "dev-openclaw": "dev-openclaw",
        "prod-leon": "prod-leon",
    }
    logical = logical_map.get(requested_host.strip())
    if logical is None:
        return {
            "destination": requested_host,
            "transport": "legacy",
            "fallback_used": False,
        }

    suffix = os.getenv("INT_SSH_TAILNET_SUFFIX", "tailf0f164.ts.net").strip() or "tailf0f164.ts.net"
    specs = {
        "dev-intdata": {
            "user": "intdata",
            "public_host": (os.getenv("INT_SSH_DEV_PUBLIC_HOST", "vds.intdata.pro") or "vds.intdata.pro").strip(),
            "tail_node": (os.getenv("INT_SSH_DEV_TAILNET_NODE", "vds-intdata-pro") or "vds-intdata-pro").strip(),
            "tail_override": (os.getenv("INT_SSH_DEV_TAILNET_HOST", "") or "").strip(),
        },
        "dev-codex": {
            "user": "codex",
            "public_host": (os.getenv("INT_SSH_DEV_PUBLIC_HOST", "vds.intdata.pro") or "vds.intdata.pro").strip(),
            "tail_node": (os.getenv("INT_SSH_DEV_TAILNET_NODE", "vds-intdata-pro") or "vds-intdata-pro").strip(),
            "tail_override": (os.getenv("INT_SSH_DEV_TAILNET_HOST", "") or "").strip(),
        },
        "dev-openclaw": {
            "user": "openclaw",
            "public_host": (os.getenv("INT_SSH_DEV_PUBLIC_HOST", "vds.intdata.pro") or "vds.intdata.pro").strip(),
            "tail_node": (os.getenv("INT_SSH_DEV_TAILNET_NODE", "vds-intdata-pro") or "vds-intdata-pro").strip(),
            "tail_override": (os.getenv("INT_SSH_DEV_TAILNET_HOST", "") or "").strip(),
        },
        "prod-leon": {
            "user": "leon",
            "public_host": (os.getenv("INT_SSH_PROD_PUBLIC_HOST", "vds.punkt-b.pro") or "vds.punkt-b.pro").strip(),
            "tail_node": (os.getenv("INT_SSH_PROD_TAILNET_NODE", "vds-punkt-b-pro") or "vds-punkt-b-pro").strip(),
            "tail_override": (os.getenv("INT_SSH_PROD_TAILNET_HOST", "") or "").strip(),
        },
    }
    spec = specs[logical]
    user = str(spec["user"])
    public_host = str(spec["public_host"])
    tail_host = str(spec["tail_override"]) or f"{spec['tail_node']}.{suffix}"
    public_dest = f"{user}@{public_host}"
    tail_dest = f"{user}@{tail_host}"

    mode = get_int_ssh_mode()
    if mode == "public":
        return {"destination": public_dest, "transport": "public", "fallback_used": False}
    if mode == "tailnet":
        return {"destination": tail_dest, "transport": "tailnet", "fallback_used": False}

    if run_ssh_probe(tail_dest, get_int_ssh_probe_timeout_sec()):
        return {"destination": tail_dest, "transport": "tailnet", "fallback_used": False}
    return {"destination": public_dest, "transport": "public", "fallback_used": True}


def run_ssh_probe(host: str, timeout_sec: int) -> bool:
    completed = subprocess.run(
        [resolve_ssh_executable(), "-o", "BatchMode=yes", "-o", f"ConnectTimeout={timeout_sec}", host, "true"],
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def run_ssh_checked(host: str, command: str, *, timeout_sec: int | None = None) -> None:
    args = [resolve_ssh_executable()]
    if timeout_sec is not None:
        args.extend(["-o", f"ConnectTimeout={timeout_sec}"])
    args.extend([host, command])
    completed = subprocess.run(
        args,
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
    args = build_parser().parse_args(normalize_cli_args(sys.argv[1:]))

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

                ssh_target = resolve_int_ssh_target(args.deploy_host)
                ssh_command = (
                    f"cd {args.deploy_repo_path} && "
                    f"git fetch --prune origin {args.deploy_fetch_ref} && "
                    f"git pull --ff-only origin {args.deploy_pull_ref}"
                )
                destination = str(ssh_target["destination"])
                run_ssh_checked(destination, ssh_command, timeout_sec=get_int_ssh_probe_timeout_sec())
                transport = str(ssh_target["transport"])
                fallback_suffix = ", fallback=public" if bool(ssh_target["fallback_used"]) else ""
                actions.append(
                    f"{repo_name}: deployed via ssh-fast-forward transport={transport}{fallback_suffix} to {destination}:{args.deploy_repo_path}"
                )
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
