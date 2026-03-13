#!/usr/bin/env python3
"""Release lockctl-backed paths for a specific issue id."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys

ISSUE_ID_RE = re.compile(r"^[1-9][0-9]*$")
LOCKCTL_BIN = os.environ.get("LOCKCTL_BIN", "lockctl")


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
        raise RuntimeError("lockctl command is empty")
    if "/" in candidate:
        path = Path(candidate).expanduser()
        if path.exists():
            return str(path)
        raise RuntimeError(f"missing lockctl: {path}")
    resolved = shutil.which(candidate)
    if resolved:
        return resolved
    raise RuntimeError(f"missing lockctl in PATH: {candidate}")


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


def _collect_files(repo_root: Path, files: list[str], files_csv: str | None, files_stdin: bool) -> list[str]:
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


def _json_out(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=True))


def _lockctl_status(repo_root: Path, issue_id: str) -> dict[str, object]:
    try:
        lockctl_bin = _resolve_lockctl_bin()
    except RuntimeError as exc:
        return {"ok": False, "error": "LOCKCTL_MISSING", "message": str(exc)}
    cmd = [
        lockctl_bin,
        "status",
        "--repo-root",
        str(repo_root),
        "--issue",
        issue_id,
        "--format",
        "json",
    ]
    cp = _run(cmd, cwd=repo_root)
    try:
        payload = json.loads(cp.stdout) if cp.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "error": "LOCKCTL_INVALID_JSON",
            "message": cp.stdout.strip() or cp.stderr.strip() or "lockctl status failed",
        }
    if cp.returncode != 0 and payload.get("ok") is not False:
        payload = {
            "ok": False,
            "error": "LOCKCTL_FAILED",
            "message": cp.stderr.strip() or cp.stdout.strip() or "lockctl status failed",
        }
    return payload


def _lockctl_release_issue(repo_root: Path, issue_id: str) -> dict[str, object]:
    try:
        lockctl_bin = _resolve_lockctl_bin()
    except RuntimeError as exc:
        return {"ok": False, "error": "LOCKCTL_MISSING", "message": str(exc)}
    cmd = [
        lockctl_bin,
        "release-issue",
        "--repo-root",
        str(repo_root),
        "--issue",
        issue_id,
        "--format",
        "json",
    ]
    cp = _run(cmd, cwd=repo_root)
    try:
        payload = json.loads(cp.stdout) if cp.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "error": "LOCKCTL_INVALID_JSON",
            "message": cp.stdout.strip() or cp.stderr.strip() or "lockctl release-issue failed",
        }
    if cp.returncode != 0 and payload.get("ok") is not False:
        payload = {
            "ok": False,
            "error": "LOCKCTL_FAILED",
            "message": cp.stderr.strip() or cp.stdout.strip() or "lockctl release-issue failed",
        }
    return payload


def _lockctl_release_path(repo_root: Path, path_rel: str, owner_id: str) -> dict[str, object]:
    try:
        lockctl_bin = _resolve_lockctl_bin()
    except RuntimeError as exc:
        return {"ok": False, "error": "LOCKCTL_MISSING", "message": str(exc)}
    cmd = [
        lockctl_bin,
        "release-path",
        "--repo-root",
        str(repo_root),
        "--path",
        path_rel,
        "--owner",
        owner_id,
        "--format",
        "json",
    ]
    cp = _run(cmd, cwd=repo_root)
    try:
        payload = json.loads(cp.stdout) if cp.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "error": "LOCKCTL_INVALID_JSON",
            "message": cp.stdout.strip() or cp.stderr.strip() or "lockctl release-path failed",
        }
    if cp.returncode != 0 and payload.get("ok") is not False:
        payload = {
            "ok": False,
            "error": "LOCKCTL_FAILED",
            "message": cp.stderr.strip() or cp.stdout.strip() or "lockctl release-path failed",
        }
    return payload


def main() -> int:
    repo_root = _resolve_repo_root()
    parser = argparse.ArgumentParser(description="Release lockctl paths by explicit issue id.")
    parser.add_argument("--file", type=Path, default=None, help="Deprecated compatibility flag; ignored")
    parser.add_argument("--issue-id", required=True, help="Numeric issue id")
    parser.add_argument("--drop-issue", action="store_true", help="Remove all active locks for the issue id")
    parser.add_argument("--files", nargs="*", default=[], help="File paths")
    parser.add_argument("--files-csv", help="Comma-separated file list")
    parser.add_argument("--files-stdin", action="store_true", help="Read newline-separated files from stdin")
    parser.add_argument("--dry-run", action="store_true", help="Print summary only, do not release locks")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    issue_id = args.issue_id.strip()
    if not ISSUE_ID_RE.match(issue_id):
        payload = {"ok": False, "error": "INVALID_ISSUE_ID", "message": f"`{issue_id}` is not numeric issue id"}
        if args.json:
            _json_out(payload)
        else:
            print(f"[INVALID_ISSUE_ID] `{issue_id}` is not numeric issue id", file=sys.stderr)
        return 2

    files: list[str] = []
    if not args.drop_issue:
        try:
            files = _collect_files(
                repo_root=repo_root,
                files=args.files or [],
                files_csv=args.files_csv,
                files_stdin=args.files_stdin,
            )
        except ValueError as exc:
            payload = {"ok": False, "error": "INVALID_PATH", "message": str(exc)}
            if args.json:
                _json_out(payload)
            else:
                print(f"[INVALID_PATH] {exc}", file=sys.stderr)
            return 2
        if not files:
            payload = {"ok": False, "error": "NO_FILES", "message": "no files provided"}
            if args.json:
                _json_out(payload)
            else:
                print("[NO_FILES] no files provided", file=sys.stderr)
            return 2

    status_payload = _lockctl_status(repo_root=repo_root, issue_id=issue_id)
    if not status_payload.get("ok"):
        if args.json:
            _json_out(status_payload)
        else:
            print(f"[{status_payload.get('error', 'LOCKCTL_FAILED')}] {status_payload.get('message', '')}", file=sys.stderr)
        return 2

    active_rows = status_payload.get("active", [])
    active_locks = active_rows if isinstance(active_rows, list) else []
    target_paths = set(files)
    selected = [
        row for row in active_locks
        if isinstance(row, dict) and (args.drop_issue or str(row.get("path_rel", "")) in target_paths)
    ]

    if args.dry_run:
        payload = {
            "ok": True,
            "changed": False,
            "issue_id": issue_id,
            "dry_run": True,
            "removed_entries": 0,
            "removed_paths": [str(item.get("path_rel", "")) for item in selected if isinstance(item, dict)],
            "matched_issue_entries": len(selected),
        }
        if args.json:
            _json_out(payload)
        else:
            print(json.dumps(payload, ensure_ascii=True))
        return 0

    if args.drop_issue:
        payload = _lockctl_release_issue(repo_root=repo_root, issue_id=issue_id)
        if args.json:
            _json_out(payload)
        else:
            target = sys.stdout if payload.get("ok") else sys.stderr
            print(json.dumps(payload, ensure_ascii=True), file=target)
        return 0 if payload.get("ok") else 2

    removed_paths: list[str] = []
    removed_entries = 0
    errors: list[dict[str, object]] = []
    for row in selected:
        owner_id = str(row.get("owner_id", "")).strip()
        path_rel = str(row.get("path_rel", "")).strip()
        if not owner_id or not path_rel:
            continue
        release_payload = _lockctl_release_path(repo_root=repo_root, path_rel=path_rel, owner_id=owner_id)
        if not release_payload.get("ok"):
            errors.append({"path_rel": path_rel, "owner_id": owner_id, "payload": release_payload})
            continue
        if release_payload.get("changed"):
            removed_entries += 1
            removed_paths.append(path_rel)

    payload = {
        "ok": not errors,
        "changed": removed_entries > 0,
        "issue_id": issue_id,
        "matched_issue_entries": len(selected),
        "removed_entries": removed_entries,
        "removed_paths": removed_paths,
        "errors": errors,
    }
    if args.json:
        _json_out(payload)
    else:
        if errors:
            print(json.dumps(payload, ensure_ascii=True), file=sys.stderr)
        else:
            print(json.dumps(payload, ensure_ascii=True))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
