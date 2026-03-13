#!/usr/bin/env python3
"""Branch-aware policy checks for dev/main git flow."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

RELEASE_FILE = "docs/release.md"
RELEASE_LABEL = "release"
LOCAL_ONLY_FILES = frozenset()


class AuditError(Exception):
    pass


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def _git_toplevel(start: Path) -> Path | None:
    probe = _run(["git", "rev-parse", "--show-toplevel"], cwd=start)
    if probe.returncode != 0:
        return None
    root = probe.stdout.strip()
    if not root:
        return None
    return Path(root).resolve()


def _repo_root() -> Path:
    env_root = os.environ.get("PUNCTB_REPO_ROOT", "").strip()
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        resolved = _git_toplevel(candidate)
        if resolved is not None:
            return resolved
        return candidate

    cwd_root = _git_toplevel(Path.cwd())
    if cwd_root is not None:
        return cwd_root

    default_root = Path(__file__).resolve().parents[2]
    fallback_root = _git_toplevel(default_root)
    if fallback_root is not None:
        return fallback_root
    return default_root


def _resolver_path(repo_root: Path) -> Path:
    ops_home = Path(os.environ.get("PUNCTB_OPS_HOME", Path(__file__).resolve().parents[2]))
    return ops_home / "ops" / "issue" / "lock_issue_resolver.py"


def _current_branch(repo_root: Path) -> str:
    cp = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    if cp.returncode != 0:
        raise AuditError(cp.stderr.strip() or "cannot determine current branch")
    return cp.stdout.strip()


def _load_issue(issue_id: str, repo_root: Path, repo: str | None, cache: dict[str, dict]) -> dict:
    if issue_id in cache:
        return cache[issue_id]

    cmd = ["gh", "issue", "view", issue_id, "--json", "state,labels,title"]
    if repo:
        cmd.extend(["-R", repo])
    cp = _run(cmd, cwd=repo_root)
    if cp.returncode != 0:
        raise AuditError(cp.stderr.strip() or f"cannot load issue #{issue_id}")
    try:
        payload = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise AuditError(f"invalid gh issue payload for #{issue_id}") from exc

    labels = sorted(item.get("name", "") for item in payload.get("labels", []) if item.get("name"))
    result = {
        "issue_id": issue_id,
        "state": str(payload.get("state", "")),
        "title": str(payload.get("title", "")),
        "labels": labels,
    }
    cache[issue_id] = result
    return result


def _parse_name_status(output: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    records = [item for item in output.split("\0") if item]
    index = 0
    while index < len(records):
        raw_record = records[index]
        if "\t" in raw_record:
            status, path = raw_record.split("\t", 1)
            index += 1
        else:
            if index + 1 >= len(records):
                break
            status = raw_record
            path = records[index + 1]
            index += 2

        status = status.strip()
        path = path.strip()
        if not status or not path:
            continue
        result.append((status[0], path))
    return result


def _staged_changes(repo_root: Path) -> list[tuple[str, str]]:
    cp = _run(["git", "diff", "--cached", "--name-status", "--no-renames", "-z"], cwd=repo_root)
    if cp.returncode != 0:
        raise AuditError(cp.stderr.strip() or "cannot read staged changes")
    return _parse_name_status(cp.stdout)


def _commit_changes(repo_root: Path, commit: str) -> list[tuple[str, str]]:
    cp = _run(
        ["git", "show", "--pretty=format:", "--name-status", "--no-renames", "-z", commit],
        cwd=repo_root,
    )
    if cp.returncode != 0:
        raise AuditError(cp.stderr.strip() or f"cannot read commit files for {commit}")
    return _parse_name_status(cp.stdout)


def _commit_list(repo_root: Path, rev_range: str) -> list[str]:
    cp = _run(["git", "rev-list", "--reverse", rev_range], cwd=repo_root)
    if cp.returncode != 0:
        raise AuditError(cp.stderr.strip() or f"invalid range: {rev_range}")
    return [item.strip() for item in cp.stdout.splitlines() if item.strip()]


def _verify_commit_issue_id(
    repo_root: Path,
    commit: str,
    require_open: bool,
    repo: str | None,
) -> str:
    resolver = _resolver_path(repo_root)
    if not resolver.exists():
        raise AuditError(f"missing resolver: {resolver}")

    cmd = [sys.executable, str(resolver), "verify-commit", "--commit", commit, "--check-gh"]
    if require_open:
        cmd.append("--require-open")
    if repo:
        cmd.extend(["--repo", repo])

    cp = _run(cmd, cwd=repo_root)
    if cp.returncode != 0:
        message = cp.stderr.strip() or cp.stdout.strip() or f"commit verification failed: {commit}"
        raise AuditError(message)
    return cp.stdout.strip().splitlines()[-1]


def _require_release_label(
    issue_id: str,
    repo_root: Path,
    repo: str | None,
    cache: dict[str, dict],
) -> None:
    payload = _load_issue(issue_id=issue_id, repo_root=repo_root, repo=repo, cache=cache)
    labels = payload["labels"]
    if RELEASE_LABEL not in labels:
        raise AuditError(f"[RELEASE_LABEL_REQUIRED] #{issue_id} must have label `{RELEASE_LABEL}` to change {RELEASE_FILE}")


def _check_release_file_policy(
    issue_id: str,
    changes: list[tuple[str, str]],
    repo_root: Path,
    repo: str | None,
    cache: dict[str, dict],
) -> None:
    for status, path in changes:
        if path == RELEASE_FILE and status != "D":
            _require_release_label(issue_id=issue_id, repo_root=repo_root, repo=repo, cache=cache)
            return


def _check_local_only_file_policy(changes: list[tuple[str, str]]) -> None:
    for status, path in changes:
        if path in LOCAL_ONLY_FILES and status != "D":
            raise AuditError(
                f"[LOCAL_ONLY_FILE_FORBIDDEN] {path} must remain local-only/ignored and must not be committed"
            )


def _assert_main_target(repo_root: Path, local_sha: str, remote_sha: str, dev_ref: str) -> None:
    if remote_sha and not re.fullmatch(r"0+", remote_sha):
        cp = _run(["git", "merge-base", "--is-ancestor", remote_sha, local_sha], cwd=repo_root)
        if cp.returncode != 0:
            raise AuditError(
                f"[MAIN_FAST_FORWARD_REQUIRED] target main update must be fast-forward: {remote_sha} !<= {local_sha}"
            )

    cp = _run(["git", "rev-parse", "--verify", dev_ref], cwd=repo_root)
    if cp.returncode != 0:
        raise AuditError(f"[DEV_REF_MISSING] cannot resolve dev ref `{dev_ref}`")

    cp = _run(["git", "merge-base", "--is-ancestor", local_sha, dev_ref], cwd=repo_root)
    if cp.returncode != 0:
        raise AuditError(
            f"[MAIN_NOT_IN_DEV] target main SHA {local_sha} is not reachable from `{dev_ref}`"
        )


def cmd_validate_staged(args: argparse.Namespace, repo_root: Path) -> int:
    branch = args.branch or _current_branch(repo_root)
    if branch != "dev":
        raise AuditError("[BRANCH_NOT_DEV] direct issue-bound commits are allowed only on `dev`")

    changes = _staged_changes(repo_root)
    if not changes:
        return 0

    _check_local_only_file_policy(changes=changes)
    cache: dict[str, dict] = {}
    _check_release_file_policy(
        issue_id=args.issue_id,
        changes=changes,
        repo_root=repo_root,
        repo=args.repo,
        cache=cache,
    )
    return 0


def cmd_audit_range(args: argparse.Namespace, repo_root: Path) -> int:
    commits = _commit_list(repo_root=repo_root, rev_range=args.range)
    if not commits:
        return 0

    cache: dict[str, dict] = {}
    require_open = args.target_branch == "dev"
    for commit in commits:
        issue_id = _verify_commit_issue_id(
            repo_root=repo_root,
            commit=commit,
            require_open=require_open,
            repo=args.repo,
        )
        changes = _commit_changes(repo_root=repo_root, commit=commit)
        _check_local_only_file_policy(changes=changes)
        _check_release_file_policy(
            issue_id=issue_id,
            changes=changes,
            repo_root=repo_root,
            repo=args.repo,
            cache=cache,
        )
    return 0


def cmd_assert_target(args: argparse.Namespace, repo_root: Path) -> int:
    if args.target_branch == "main":
        _assert_main_target(
            repo_root=repo_root,
            local_sha=args.local_sha,
            remote_sha=args.remote_sha,
            dev_ref=args.dev_ref,
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Branch-aware git flow policy checks")
    sub = parser.add_subparsers(dest="command", required=True)

    p_staged = sub.add_parser("validate-staged", help="Validate staged changes for dev commit flow")
    p_staged.add_argument("--issue-id", required=True, help="Numeric release/feature issue id")
    p_staged.add_argument("--branch", help="Explicit branch override")
    p_staged.add_argument("--repo", help="Optional OWNER/REPO for gh commands")

    p_range = sub.add_parser("audit-range", help="Audit a commit range for target branch policy")
    p_range.add_argument("--target-branch", required=True, choices=["dev", "main"])
    p_range.add_argument("--range", required=True, help="Git revision range")
    p_range.add_argument("--repo", help="Optional OWNER/REPO for gh commands")

    p_target = sub.add_parser("assert-target", help="Validate target-branch topology before push")
    p_target.add_argument("--target-branch", required=True, choices=["dev", "main"])
    p_target.add_argument("--local-sha", required=True)
    p_target.add_argument("--remote-sha", required=True)
    p_target.add_argument("--dev-ref", default="refs/remotes/origin/dev")

    return parser


def main() -> int:
    repo_root = _repo_root()
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "validate-staged":
            return cmd_validate_staged(args, repo_root)
        if args.command == "audit-range":
            return cmd_audit_range(args, repo_root)
        if args.command == "assert-target":
            return cmd_assert_target(args, repo_root)
        raise AuditError(f"unknown command: {args.command}")
    except AuditError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
