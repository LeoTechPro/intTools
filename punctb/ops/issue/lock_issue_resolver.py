#!/usr/bin/env python3
"""Resolve GitHub issue binding from machine-wide lockctl and audit commit metadata."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys

ISSUE_ID_RE = re.compile(r"^[1-9][0-9]*$")
REFS_RE = re.compile(r"(?im)^\s*Refs\s+#(?P<id>[1-9][0-9]*)\b")
FORBIDDEN_CLOSE_RE = re.compile(r"(?i)\b(?:Fixes|Closes|Resolves)\s*#[0-9]+\b")
LOCKCTL_BIN = os.environ.get("LOCKCTL_BIN", "lockctl")


@dataclasses.dataclass
class ResolverFailure:
    code: str
    message: str


class ResolverError(Exception):
    def __init__(self, failures: list[ResolverFailure]):
        self.failures = failures
        super().__init__("; ".join(f"[{item.code}] {item.message}" for item in failures))


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


def _resolve_lockctl_bin() -> str:
    candidate = LOCKCTL_BIN.strip()
    if not candidate:
        raise ResolverError([ResolverFailure("LOCKCTL_MISSING", "lockctl command is empty")])
    if "/" in candidate:
        path = Path(candidate).expanduser()
        if path.exists():
            return str(path)
        raise ResolverError([ResolverFailure("LOCKCTL_MISSING", f"missing lockctl: {path}")])
    resolved = shutil.which(candidate)
    if resolved:
        return resolved
    raise ResolverError([ResolverFailure("LOCKCTL_MISSING", f"missing lockctl in PATH: {candidate}")])


def _resolve_repo_root() -> Path:
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


def _normalize_path(path_value: str, repo_root: Path) -> str:
    cleaned = path_value.strip().replace("\\", "/")
    p = PurePosixPath(cleaned)
    if p.is_absolute():
        abs_target = Path(str(p)).resolve()
        try:
            return abs_target.relative_to(repo_root.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError(f"path escapes repository root: {path_value}") from exc

    normalized = os.path.normpath(str(p)).replace("\\", "/")
    if normalized in {".", ""}:
        raise ValueError(f"empty path is not allowed: {path_value}")
    if normalized == ".." or normalized.startswith("../"):
        raise ValueError(f"path escapes repository root: {path_value}")
    abs_target = (repo_root / normalized).resolve()
    try:
        abs_target.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes repository root: {path_value}") from exc
    return normalized


def _collect_files_from_staged(repo_root: Path) -> list[str]:
    cp = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRD", "-z"], cwd=repo_root)
    if cp.returncode != 0:
        raise ResolverError([ResolverFailure("GIT_FAILED", cp.stderr.strip() or "cannot read staged files")])
    files = [item for item in cp.stdout.split("\0") if item]
    return [_normalize_path(item, repo_root) for item in files]


def _collect_files_from_args(repo_root: Path, files: list[str], files_csv: str | None, files_stdin: bool) -> list[str]:
    collected: list[str] = []
    collected.extend(files)
    if files_csv:
        for chunk in files_csv.split(","):
            token = chunk.strip()
            if token:
                collected.append(token)
    if files_stdin:
        for raw in sys.stdin.read().splitlines():
            token = raw.strip()
            if token:
                collected.append(token)
    normalized = [_normalize_path(item, repo_root) for item in collected]
    seen: set[str] = set()
    unique: list[str] = []
    for item in normalized:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _lockctl_status(repo_root: Path, path: str | None = None, issue_id: str | None = None) -> dict[str, object]:
    cmd = [_resolve_lockctl_bin(), "status", "--repo-root", str(repo_root), "--format", "json"]
    if path is not None:
        cmd.extend(["--path", path])
    if issue_id is not None:
        cmd.extend(["--issue", issue_id])
    cp = _run(cmd, cwd=repo_root)
    try:
        payload = json.loads(cp.stdout) if cp.stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise ResolverError(
            [ResolverFailure("LOCKCTL_INVALID_JSON", f"invalid JSON from lockctl status: {cp.stdout.strip()}")]
        ) from exc
    if cp.returncode != 0 or not payload.get("ok"):
        error = str(payload.get("error", "LOCKCTL_FAILED"))
        message = str(payload.get("message", cp.stderr.strip() or "lockctl status failed"))
        raise ResolverError([ResolverFailure(error, message)])
    return payload


def _format_lock_sources(entries: list[dict[str, object]]) -> str:
    details: list[str] = []
    for entry in entries:
        issue_id = str(entry.get("issue_id") or "n/a")
        owner_id = str(entry.get("owner_id") or "n/a")
        lock_id = str(entry.get("lock_id") or "n/a")
        details.append(f"issue={issue_id} owner={owner_id} lock_id={lock_id}")
    return ", ".join(sorted(set(details)))


def _active_entries_for_path(repo_root: Path, file_path: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    payload = _lockctl_status(repo_root=repo_root, path=file_path)
    active = payload.get("active", [])
    expired = payload.get("expired", [])
    return (
        active if isinstance(active, list) else [],
        expired if isinstance(expired, list) else [],
    )


def _resolve_issue_for_files(files: list[str], repo_root: Path) -> str:
    if not files:
        raise ResolverError([ResolverFailure("NO_STAGED_FILES", "no files to resolve")])

    failures: list[ResolverFailure] = []
    resolved_ids: set[str] = set()

    for file_path in files:
        active_entries, expired_entries = _active_entries_for_path(repo_root=repo_root, file_path=file_path)
        if not active_entries:
            if expired_entries:
                failures.append(
                    ResolverFailure(
                        "LOCK_EXPIRED",
                        f"{file_path}: no active lock; found only expired locks: {_format_lock_sources(expired_entries)}",
                    )
                )
            else:
                failures.append(ResolverFailure("NO_LOCK", f"{file_path}: no active lock entry found"))
            continue

        active_ids = sorted({str(entry.get("issue_id")) for entry in active_entries if entry.get("issue_id")})
        if not active_ids:
            failures.append(
                ResolverFailure(
                    "NO_LOCK",
                    f"{file_path}: active lock exists but has no numeric issue id; sources: {_format_lock_sources(active_entries)}",
                )
            )
            continue

        if len(active_ids) > 1:
            failures.append(
                ResolverFailure(
                    "AMBIGUOUS_LOCK",
                    f"{file_path}: multiple active issue ids: {', '.join(active_ids)}; "
                    f"sources: {_format_lock_sources(active_entries)}",
                )
            )
            continue

        resolved_ids.add(active_ids[0])

    if failures:
        raise ResolverError(failures)
    if not resolved_ids:
        raise ResolverError([ResolverFailure("NO_LOCK", "cannot resolve issue id for provided files")])
    if len(resolved_ids) > 1:
        raise ResolverError(
            [
                ResolverFailure(
                    "MULTI_ISSUE",
                    "single commit cannot contain files from multiple issues: " + ", ".join(sorted(resolved_ids)),
                )
            ]
        )
    return next(iter(resolved_ids))


def _assert_issue_for_files(issue_id: str, files: list[str], repo_root: Path) -> dict[str, object]:
    if not ISSUE_ID_RE.match(issue_id):
        raise ResolverError([ResolverFailure("INVALID_ISSUE_ID", f"`{issue_id}` is not numeric issue id")])
    if not files:
        raise ResolverError([ResolverFailure("NO_STAGED_FILES", "no files to resolve")])

    matched: list[str] = []
    missing: list[dict[str, object]] = []
    conflicts: list[dict[str, object]] = []

    for file_path in files:
        active_entries, expired_entries = _active_entries_for_path(repo_root=repo_root, file_path=file_path)
        if not active_entries:
            if expired_entries:
                missing.append(
                    {
                        "path": file_path,
                        "state": "expired",
                        "sources": _format_lock_sources(expired_entries),
                    }
                )
            else:
                missing.append({"path": file_path, "state": "missing", "sources": ""})
            continue

        active_ids = sorted({str(entry.get("issue_id")) for entry in active_entries if entry.get("issue_id")})
        if active_ids == [issue_id]:
            matched.append(file_path)
            continue

        conflicts.append(
            {
                "path": file_path,
                "issue_ids": active_ids,
                "sources": _format_lock_sources(active_entries),
            }
        )

    return {"issue_id": issue_id, "files": files, "matched": matched, "missing": missing, "conflicts": conflicts}


def _resolve_repo_arg(repo: str | None) -> str | None:
    return repo or None


def _check_issue(issue_id: str, repo_root: Path, repo: str | None, require_open: bool) -> None:
    cmd = ["gh", "issue", "view", issue_id, "--json", "number,state,title"]
    repo_value = _resolve_repo_arg(repo)
    if repo_value:
        cmd.extend(["-R", repo_value])
    cp = _run(cmd, cwd=repo_root)
    if cp.returncode != 0:
        msg = cp.stderr.strip() or cp.stdout.strip() or "gh issue view failed"
        raise ResolverError([ResolverFailure("ISSUE_NOT_FOUND", f"#{issue_id}: {msg}")])
    payload = json.loads(cp.stdout)
    state = str(payload.get("state", "")).upper()
    if require_open and state != "OPEN":
        raise ResolverError([ResolverFailure("ISSUE_NOT_OPEN", f"#{issue_id}: issue state is {state}, expected OPEN")])


def _extract_refs_ids(message: str) -> list[str]:
    return sorted(set(match.group("id") for match in REFS_RE.finditer(message)))


def _strip_comment_lines(message: str) -> str:
    lines = message.splitlines()
    visible: list[str] = []
    for line in lines:
        if line.lstrip().startswith("#"):
            continue
        visible.append(line)
    return "\n".join(visible)


def _ensure_message(message_file: Path, issue_id: str) -> bool:
    raw = message_file.read_text(encoding="utf-8")
    visible = _strip_comment_lines(raw)

    if FORBIDDEN_CLOSE_RE.search(visible):
        raise ResolverError(
            [
                ResolverFailure(
                    "FORBIDDEN_CLOSE_KEYWORD",
                    "commit message must not contain Fixes/Closes/Resolves #<id>; use `Refs #<id>`",
                )
            ]
        )

    refs_ids = _extract_refs_ids(visible)
    if len(refs_ids) > 1:
        raise ResolverError([ResolverFailure("MULTI_ISSUE", f"commit message references multiple issues: {', '.join(refs_ids)}")])
    if len(refs_ids) == 1 and refs_ids[0] != issue_id:
        raise ResolverError([ResolverFailure("MISMATCH_REFS", f"commit message has Refs #{refs_ids[0]} but resolved issue is #{issue_id}")])
    if refs_ids:
        return False

    new_text = raw
    if not new_text.endswith("\n"):
        new_text += "\n"
    if visible.strip():
        new_text += "\n"
    new_text += f"Refs #{issue_id}\n"
    message_file.write_text(new_text, encoding="utf-8")
    return True


def _get_commit_message(repo_root: Path, commit: str) -> str:
    cp = _run(["git", "show", "-s", "--format=%B", commit], cwd=repo_root)
    if cp.returncode != 0:
        raise ResolverError([ResolverFailure("GIT_FAILED", cp.stderr.strip() or f"cannot read commit {commit}")])
    return cp.stdout


def _verify_commit_message(
    repo_root: Path,
    commit: str,
    check_gh: bool,
    require_open: bool,
    repo: str | None,
    issue_cache: dict[str, bool] | None = None,
) -> str:
    message = _get_commit_message(repo_root=repo_root, commit=commit)
    if FORBIDDEN_CLOSE_RE.search(message):
        raise ResolverError(
            [ResolverFailure("FORBIDDEN_CLOSE_KEYWORD", f"{commit}: commit message contains forbidden Fixes/Closes/Resolves keyword")]
        )
    refs_ids = _extract_refs_ids(message)
    if not refs_ids:
        raise ResolverError([ResolverFailure("MISSING_REFS", f"{commit}: commit message does not contain `Refs #<id>`")])
    if len(refs_ids) > 1:
        raise ResolverError([ResolverFailure("MULTI_ISSUE", f"{commit}: commit message references multiple issues: {', '.join(refs_ids)}")])

    issue_id = refs_ids[0]
    if check_gh:
        if issue_cache is not None and issue_id in issue_cache:
            cached_open = issue_cache[issue_id]
            if require_open and not cached_open:
                raise ResolverError([ResolverFailure("ISSUE_NOT_OPEN", f"{commit}: issue #{issue_id} is not OPEN")])
        else:
            _check_issue(issue_id=issue_id, repo_root=repo_root, repo=repo, require_open=require_open)
            if issue_cache is not None:
                issue_cache[issue_id] = True
    return issue_id


def _list_commits_for_range(repo_root: Path, rev_range: str) -> list[str]:
    cp = _run(["git", "rev-list", "--reverse", rev_range], cwd=repo_root)
    if cp.returncode != 0:
        raise ResolverError([ResolverFailure("GIT_FAILED", cp.stderr.strip() or f"invalid range: {rev_range}")])
    return [line.strip() for line in cp.stdout.splitlines() if line.strip()]


def _json_result(data: dict[str, object]) -> None:
    print(json.dumps(data, ensure_ascii=True))


def cmd_resolve(args: argparse.Namespace, repo_root: Path) -> int:
    files = _collect_files_from_args(repo_root=repo_root, files=args.files or [], files_csv=args.files_csv, files_stdin=args.files_stdin)
    issue_id = _resolve_issue_for_files(files=files, repo_root=repo_root)
    if args.check_gh:
        _check_issue(issue_id=issue_id, repo_root=repo_root, repo=args.repo, require_open=args.require_open)
    if args.json:
        _json_result({"ok": True, "issue_id": issue_id, "files": files})
    else:
        print(issue_id)
    return 0


def cmd_resolve_staged(args: argparse.Namespace, repo_root: Path) -> int:
    files = _collect_files_from_staged(repo_root=repo_root)
    issue_id = _resolve_issue_for_files(files=files, repo_root=repo_root)
    if args.check_gh:
        _check_issue(issue_id=issue_id, repo_root=repo_root, repo=args.repo, require_open=args.require_open)
    if args.json:
        _json_result({"ok": True, "issue_id": issue_id, "files": files})
    else:
        print(issue_id)
    return 0


def cmd_assert_issue_files(args: argparse.Namespace, repo_root: Path) -> int:
    files = _collect_files_from_args(repo_root=repo_root, files=args.files or [], files_csv=args.files_csv, files_stdin=args.files_stdin)
    issue_id = args.issue_id.strip()
    summary = _assert_issue_for_files(issue_id=issue_id, files=files, repo_root=repo_root)
    if args.check_gh:
        _check_issue(issue_id=issue_id, repo_root=repo_root, repo=args.repo, require_open=args.require_open)

    failures: list[ResolverFailure] = []
    missing = summary.get("missing", [])
    conflicts = summary.get("conflicts", [])
    if isinstance(missing, list):
        for item in missing:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", ""))
            state = str(item.get("state", "missing"))
            sources = str(item.get("sources", ""))
            code = "LOCK_EXPIRED" if state == "expired" else "NO_LOCK"
            if sources:
                failures.append(ResolverFailure(code, f"{path}: {state} lock; sources: {sources}"))
            else:
                failures.append(ResolverFailure(code, f"{path}: no active lock for issue #{issue_id}"))
    if isinstance(conflicts, list):
        for item in conflicts:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", ""))
            issue_ids = item.get("issue_ids", [])
            sources = str(item.get("sources", ""))
            issue_ids_text = ", ".join(str(value) for value in issue_ids) if isinstance(issue_ids, list) else str(issue_ids)
            failures.append(ResolverFailure("LOCK_CONFLICT", f"{path}: active lock belongs to other issue(s): {issue_ids_text}; sources: {sources}"))

    if failures:
        if args.json:
            _json_result({"ok": False, "summary": summary, "errors": [dataclasses.asdict(item) for item in failures]})
        else:
            for item in failures:
                print(f"[{item.code}] {item.message}", file=sys.stderr)
        return 2

    if args.json:
        _json_result({"ok": True, "summary": summary})
    else:
        matched = summary.get("matched", [])
        print(f"ASSERT_OK issue={issue_id} matched={len(matched) if isinstance(matched, list) else 0}")
    return 0


def cmd_ensure_message(args: argparse.Namespace, repo_root: Path) -> int:
    issue_id = args.issue_id.strip()
    if not ISSUE_ID_RE.match(issue_id):
        raise ResolverError([ResolverFailure("INVALID_ISSUE_ID", f"`{issue_id}` is not numeric issue id")])
    changed = _ensure_message(message_file=Path(args.message_file), issue_id=issue_id)
    if args.json:
        _json_result({"ok": True, "issue_id": issue_id, "changed": changed})
    return 0


def cmd_verify_commit(args: argparse.Namespace, repo_root: Path) -> int:
    issue_id = _verify_commit_message(repo_root=repo_root, commit=args.commit, check_gh=args.check_gh, require_open=args.require_open, repo=args.repo)
    if args.json:
        _json_result({"ok": True, "commit": args.commit, "issue_id": issue_id})
    else:
        print(issue_id)
    return 0


def cmd_audit_range(args: argparse.Namespace, repo_root: Path) -> int:
    commits = _list_commits_for_range(repo_root=repo_root, rev_range=args.range)
    if not commits:
        if args.json:
            _json_result({"ok": True, "range": args.range, "checked": 0, "issues": []})
        else:
            print("No commits in range")
        return 0

    issue_cache: dict[str, bool] = {}
    failures: list[ResolverFailure] = []
    checked = 0
    issue_ids: set[str] = set()
    for commit in commits:
        checked += 1
        try:
            issue_id = _verify_commit_message(
                repo_root=repo_root,
                commit=commit,
                check_gh=args.check_gh,
                require_open=args.require_open,
                repo=args.repo,
                issue_cache=issue_cache,
            )
            issue_ids.add(issue_id)
        except ResolverError as err:
            failures.extend(err.failures)
    if failures:
        raise ResolverError(failures)
    if args.json:
        _json_result({"ok": True, "range": args.range, "checked": checked, "issues": sorted(issue_ids)})
    else:
        print(f"AUDIT_OK checked={checked} issues={','.join(sorted(issue_ids))}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve issue ids from lockctl-backed machine-wide leases")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common_resolve_flags(command: argparse.ArgumentParser) -> None:
        command.add_argument("--lock-file", default="", help="Deprecated compatibility flag; ignored")
        command.add_argument("--check-gh", action="store_true", help="Validate issue via gh issue view")
        command.add_argument("--require-open", action="store_true", help="Require issue state OPEN when --check-gh")
        command.add_argument("--repo", help="Optional OWNER/REPO for gh commands")
        command.add_argument("--json", action="store_true", help="Output JSON")

    resolve = sub.add_parser("resolve", help="Resolve issue id for explicit files")
    resolve.add_argument("--files", nargs="*", default=[], help="File paths")
    resolve.add_argument("--files-csv", help="Comma-separated file list")
    resolve.add_argument("--files-stdin", action="store_true", help="Read newline-separated files from stdin")
    add_common_resolve_flags(resolve)

    resolve_staged = sub.add_parser("resolve-staged", help="Resolve issue id for staged files")
    add_common_resolve_flags(resolve_staged)

    assert_issue = sub.add_parser("assert-issue-files", help="Assert that files are actively locked under explicit issue id")
    assert_issue.add_argument("--issue-id", required=True, help="Expected numeric issue id")
    assert_issue.add_argument("--files", nargs="*", default=[], help="File paths")
    assert_issue.add_argument("--files-csv", help="Comma-separated file list")
    assert_issue.add_argument("--files-stdin", action="store_true", help="Read newline-separated files from stdin")
    add_common_resolve_flags(assert_issue)

    ensure = sub.add_parser("ensure-message", help="Validate and inject `Refs #<id>` trailer")
    ensure.add_argument("--message-file", required=True, help="Path to commit message file")
    ensure.add_argument("--issue-id", required=True, help="Expected issue id")
    ensure.add_argument("--json", action="store_true", help="Output JSON")

    verify = sub.add_parser("verify-commit", help="Verify one commit message")
    verify.add_argument("--commit", required=True, help="Commit SHA")
    verify.add_argument("--check-gh", action="store_true", help="Validate issue via gh")
    verify.add_argument("--require-open", action="store_true", help="Require issue OPEN when --check-gh")
    verify.add_argument("--repo", help="Optional OWNER/REPO")
    verify.add_argument("--json", action="store_true", help="Output JSON")

    audit = sub.add_parser("audit-range", help="Audit all commits in revision range")
    audit.add_argument("--range", required=True, help="Revision range, e.g. origin/main..HEAD")
    audit.add_argument("--check-gh", action="store_true", help="Validate issue via gh")
    audit.add_argument("--require-open", action="store_true", help="Require issue OPEN when --check-gh")
    audit.add_argument("--repo", help="Optional OWNER/REPO")
    audit.add_argument("--json", action="store_true", help="Output JSON")

    return parser


def main() -> int:
    repo_root = _resolve_repo_root()
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "resolve":
            return cmd_resolve(args, repo_root)
        if args.command == "resolve-staged":
            return cmd_resolve_staged(args, repo_root)
        if args.command == "assert-issue-files":
            return cmd_assert_issue_files(args, repo_root)
        if args.command == "ensure-message":
            return cmd_ensure_message(args, repo_root)
        if args.command == "verify-commit":
            return cmd_verify_commit(args, repo_root)
        if args.command == "audit-range":
            return cmd_audit_range(args, repo_root)
        raise ResolverError([ResolverFailure("INTERNAL", f"unknown command: {args.command}")])
    except ResolverError as err:
        if getattr(args, "json", False):
            _json_result({"ok": False, "errors": [dataclasses.asdict(item) for item in err.failures]})
        else:
            for item in err.failures:
                print(f"[{item.code}] {item.message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
