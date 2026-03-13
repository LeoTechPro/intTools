#!/usr/bin/env python3
"""Prepare docs/release.md from closed release-note issues."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

RELEASE_LABEL = "release"
RELEASE_NOTE_LABEL = "release-note"
RELEASE_ISSUES_HEADERS = ("## Release includes", "## Included issues")
RELEASE_NOTE_HEADERS = ("## Release note",)


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


def _section(text: str, headers: tuple[str, ...]) -> str:
    lines = text.splitlines()
    capture = False
    out: list[str] = []
    normalized = {item.strip().lower() for item in headers}
    for line in lines:
        stripped = line.strip()
        if stripped.lower() in normalized:
            capture = True
            continue
        if capture and stripped.startswith("## "):
            break
        if capture:
            out.append(line)
    return "\n".join(out).strip()


def _extract_issue_ids(section: str) -> list[str]:
    found: list[str] = []
    for match in re.finditer(r"#?(?P<id>[1-9][0-9]*)", section):
        issue_id = match.group("id")
        if issue_id not in found:
            found.append(issue_id)
    return found


def _normalize_note(note: str) -> str:
    note = note.strip()
    if not note:
        return ""
    if not note.endswith("\n"):
        note += "\n"
    return note


def _owner_repo(repo_root: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    cp = _run(["gh", "repo", "view", "--json", "nameWithOwner"], cwd=repo_root)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or "cannot determine GitHub repo")
    payload = json.loads(cp.stdout)
    return str(payload["nameWithOwner"])


def _issue_view(repo_root: Path, issue_id: str, repo: str) -> dict:
    cp = _run(
        ["gh", "issue", "view", issue_id, "-R", repo, "--json", "state,title,body,labels"],
        cwd=repo_root,
    )
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or f"cannot load issue #{issue_id}")
    return json.loads(cp.stdout)


def _issue_comments(repo_root: Path, issue_id: str, repo: str) -> list[dict]:
    cp = _run(
        ["gh", "api", f"repos/{repo}/issues/{issue_id}/comments?per_page=100"],
        cwd=repo_root,
    )
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or f"cannot load comments for #{issue_id}")
    payload = json.loads(cp.stdout)
    if not isinstance(payload, list):
        return []
    return payload


def _labels(payload: dict) -> set[str]:
    return {item.get("name", "") for item in payload.get("labels", []) if item.get("name")}


def _release_note_text(repo_root: Path, issue_id: str, repo: str, payload: dict) -> str:
    body_note = _section(str(payload.get("body", "")), RELEASE_NOTE_HEADERS)
    if body_note:
        return _normalize_note(body_note)

    comments = _issue_comments(repo_root=repo_root, issue_id=issue_id, repo=repo)
    for comment in reversed(comments):
        body = str(comment.get("body", ""))
        section = _section(body, RELEASE_NOTE_HEADERS)
        if section:
            return _normalize_note(section)
    raise RuntimeError(f"issue #{issue_id} has no `## Release note` in body or comments")


def _build_block(repo_root: Path, release_issue_id: str, repo: str, date_text: str) -> str:
    release_issue = _issue_view(repo_root=repo_root, issue_id=release_issue_id, repo=repo)
    if str(release_issue.get("state", "")) != "OPEN":
        raise RuntimeError(f"release issue #{release_issue_id} must be OPEN")
    if RELEASE_LABEL not in _labels(release_issue):
        raise RuntimeError(f"release issue #{release_issue_id} must have label `{RELEASE_LABEL}`")

    includes_section = _section(str(release_issue.get("body", "")), RELEASE_ISSUES_HEADERS)
    included_issue_ids = _extract_issue_ids(includes_section)
    if not included_issue_ids:
        raise RuntimeError(
            f"release issue #{release_issue_id} must list included issues under `## Release includes`"
        )

    parts = [f"<!-- release:{release_issue_id}:start -->", f"## {date_text}"]
    for issue_id in included_issue_ids:
        issue_payload = _issue_view(repo_root=repo_root, issue_id=issue_id, repo=repo)
        if str(issue_payload.get("state", "")) != "CLOSED":
            raise RuntimeError(f"included issue #{issue_id} must be CLOSED")
        if RELEASE_NOTE_LABEL not in _labels(issue_payload):
            raise RuntimeError(f"included issue #{issue_id} must have label `{RELEASE_NOTE_LABEL}`")

        title = str(issue_payload.get("title", "")).strip()
        note_text = _release_note_text(
            repo_root=repo_root,
            issue_id=issue_id,
            repo=repo,
            payload=issue_payload,
        )
        parts.append(f"### {title}")
        parts.append(note_text.rstrip())

    parts.append(f"<!-- release:{release_issue_id}:end -->")
    return "\n".join(parts).strip() + "\n"


def _replace_release_block(content: str, release_issue_id: str, block: str) -> str:
    marker_start = f"<!-- release:{release_issue_id}:start -->"
    marker_end = f"<!-- release:{release_issue_id}:end -->"
    start = content.find(marker_start)
    end = content.find(marker_end)
    if start != -1 and end != -1 and end >= start:
        end += len(marker_end)
        replacement = block.rstrip()
        if start > 0 and content[start - 1] == "\n":
            replacement = "\n" + replacement
        return content[:start] + replacement + content[end:]

    lines = content.splitlines()
    insert_at = len(lines)
    for index, line in enumerate(lines):
        if line.startswith("## "):
            insert_at = index
            break
    new_lines = lines[:insert_at] + [block.rstrip(), ""] + lines[insert_at:]
    return "\n".join(new_lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare docs/release.md from release issue metadata")
    parser.add_argument("--issue", required=True, help="Release issue id")
    parser.add_argument("--repo", help="Optional OWNER/REPO override")
    parser.add_argument("--date", help="Optional YYYY-MM-DD override")
    args = parser.parse_args()

    repo_root = _repo_root()
    repo = _owner_repo(repo_root=repo_root, explicit=args.repo)
    date_text = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    release_md = repo_root / "docs" / "release.md"
    if not release_md.exists():
        raise RuntimeError(f"missing release file: {release_md}")

    block = _build_block(repo_root=repo_root, release_issue_id=args.issue, repo=repo, date_text=date_text)
    current = release_md.read_text(encoding="utf-8")
    updated = _replace_release_block(content=current, release_issue_id=args.issue, block=block)
    if updated == current:
        print(f"RELEASE_PREPARE_NO_CHANGES issue=#{args.issue}")
        return 0

    release_md.write_text(updated, encoding="utf-8")
    print(f"RELEASE_PREPARED issue=#{args.issue} repo={repo} date={date_text}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
