#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


ISSUE_RE = re.compile(r"\b(?:Refs|Fixes|Closes|Resolves)\s+#(?P<issue>\d+)\b", re.IGNORECASE)
WATCHED_BRANCHES = {"dev", "main"}


def _run_lines(cmd: list[str]) -> list[str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=15)
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    return [line.rstrip("\n") for line in (proc.stdout or "").splitlines()]


def _repo_root() -> str:
    lines = _run_lines(["git", "rev-parse", "--show-toplevel"])
    return lines[0].strip() if lines else ""


def _spool_path(repo_root: str) -> str:
    override = os.getenv("PUNCTB_PROBE_GIT_SPOOL_FILE", "").strip()
    if override:
        return override
    return str(Path(repo_root) / ".git" / "probe-events.jsonl")


def _append_payload(path: str, payload: dict) -> int:
    os.makedirs(str(Path(path).parent), exist_ok=True)
    line = json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(line)
    return 0


def _parse_issue_id(message_body: str) -> str:
    match = ISSUE_RE.search(message_body or "")
    if not match:
        return ""
    return str(match.group("issue") or "").strip()


def _current_branch(repo_root: str) -> str:
    lines = _run_lines(["git", "-C", repo_root, "rev-parse", "--abbrev-ref", "HEAD"])
    return lines[0].strip() if lines else ""


def _commit_payload(repo_root: str) -> dict:
    branch = _current_branch(repo_root)
    if branch not in WATCHED_BRANCHES:
        return {}

    lines = _run_lines(
        [
            "git",
            "-C",
            repo_root,
            "show",
            "-s",
            "--format=%H%n%h%n%s%n%an%n%ae%n%ct%n%B",
            "HEAD",
        ]
    )
    if len(lines) < 6:
        return {}

    commit_sha = lines[0].strip()
    commit_short = lines[1].strip()
    subject = lines[2].strip()
    author_name = lines[3].strip()
    author_email = lines[4].strip()
    commit_ts = lines[5].strip()
    message_body = "\n".join(lines[6:]).strip()
    issue_id = _parse_issue_id(message_body)

    numstat_lines = _run_lines(["git", "-C", repo_root, "show", "--numstat", "--format=", "HEAD"])
    changed_files = 0
    insertions = 0
    deletions = 0
    for raw in numstat_lines:
        parts = raw.split("\t")
        if len(parts) < 3:
            continue
        changed_files += 1
        if parts[0].isdigit():
            insertions += int(parts[0])
        if parts[1].isdigit():
            deletions += int(parts[1])

    now = int(time.time())
    return {
        "kind": "local_commit",
        "event_ts": str(now),
        "repo_path": repo_root,
        "branch": branch,
        "commit_sha": commit_sha,
        "commit_short": commit_short,
        "subject": subject,
        "author_name": author_name,
        "author_email": author_email,
        "issue_id": issue_id,
        "changed_files": changed_files,
        "insertions": insertions,
        "deletions": deletions,
        "commit_ts": commit_ts,
    }


def _ref_advance_payload(repo_root: str, argv: list[str]) -> dict:
    ref_name = ""
    old_sha = ""
    new_sha = ""
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--ref" and idx + 1 < len(argv):
            ref_name = argv[idx + 1].strip()
            idx += 2
            continue
        if arg == "--old" and idx + 1 < len(argv):
            old_sha = argv[idx + 1].strip()
            idx += 2
            continue
        if arg == "--new" and idx + 1 < len(argv):
            new_sha = argv[idx + 1].strip()
            idx += 2
            continue
        idx += 1

    if not ref_name.startswith("refs/heads/"):
        return {}
    branch = ref_name.split("/", 2)[-1].strip()
    if branch not in WATCHED_BRANCHES:
        return {}
    if not new_sha or re.fullmatch(r"0{40}", new_sha or ""):
        return {}

    return {
        "kind": "ref_advance",
        "event_ts": str(int(time.time())),
        "repo_path": repo_root,
        "branch": branch,
        "ref_name": ref_name,
        "old_sha": old_sha,
        "new_sha": new_sha,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: probe_git_event_emit.py <commit|ref-advance> [...]", file=sys.stderr)
        return 2

    repo_root = _repo_root()
    if not repo_root:
        return 0

    mode = argv[1].strip().lower()
    if mode == "commit":
        payload = _commit_payload(repo_root)
    elif mode == "ref-advance":
        payload = _ref_advance_payload(repo_root, argv[2:])
    else:
        print(f"unsupported mode: {mode}", file=sys.stderr)
        return 2

    if not payload:
        return 0
    return _append_payload(_spool_path(repo_root), payload)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
