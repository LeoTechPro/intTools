#!/usr/bin/env python3
"""Codex hooks dispatcher for intData host/repo contour guardrails."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONTOURS = [
    {
        "name": "intdata-dev",
        "host": "vds.intdata.pro",
        "host_aliases": ["vds.intdata.pro", "debian"],
        "repo": "/int/data",
        "branch": "main",
        "role": "dev",
        "mutation_policy": "allowed_with_issue_lock_spec_and_git_hooks",
        "publication": "commit on /int/data main, publish to origin/main, prod refreshes from origin",
    },
    {
        "name": "punktb-prod",
        "host": "vds.punkt-b.pro",
        "host_aliases": ["vds.punkt-b.pro"],
        "repo": "/int/punkt-b",
        "branch": "main",
        "role": "prod",
        "mutation_policy": "read_only_refresh_from_origin",
        "publication": "no direct agent commits or pushes; refresh only from origin/main",
    },
]

MUTATING_GIT_RE = re.compile(
    r"(^|[;&|]\s*)git\s+(add|commit|push|reset|clean|checkout|switch|merge|rebase|cherry-pick|am|apply)\b",
    re.IGNORECASE,
)
COMMIT_RE = re.compile(r"(^|[;&|]\s*)git\s+commit\b", re.IGNORECASE)
PUSH_RE = re.compile(r"(^|[;&|]\s*)git\s+push\b", re.IGNORECASE)
PULL_RE = re.compile(r"(^|[;&|]\s*)git\s+pull\b", re.IGNORECASE)


def read_payload() -> dict[str, Any]:
    try:
        return json.load(sys.stdin)
    except Exception as exc:
        return {"hook_event_name": "unknown", "_parse_error": str(exc)}


def realpath(path: str | None) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).resolve())
    except Exception:
        return path


def run_git(cwd: str, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def discover_context(cwd: str) -> dict[str, Any]:
    host = socket.getfqdn() or socket.gethostname()
    short_host = socket.gethostname()
    cwd_real = realpath(cwd)
    repo_root = run_git(cwd_real or "/", ["rev-parse", "--show-toplevel"]) if cwd_real else ""
    repo_root = realpath(repo_root) if repo_root else ""
    branch = run_git(repo_root or cwd_real or "/", ["branch", "--show-current"]) if (repo_root or cwd_real) else ""
    head = run_git(repo_root or cwd_real or "/", ["rev-parse", "--short", "HEAD"]) if (repo_root or cwd_real) else ""

    matched = None
    for contour in CONTOURS:
        if repo_root == contour["repo"]:
            matched = contour
            break

    return {
        "host": host,
        "short_host": short_host,
        "cwd": cwd_real,
        "repo_root": repo_root,
        "branch": branch,
        "head": head,
        "contour": matched,
    }


def contour_text(ctx: dict[str, Any]) -> str:
    c = ctx.get("contour")
    if not c:
        return (
            "Codex hook context: no managed intData contour matched for this cwd. "
            f"host={ctx.get('host')}; repo={ctx.get('repo_root') or ctx.get('cwd')}."
        )
    return (
        "Codex hook context: managed intData contour detected. "
        f"contour={c['name']}; role={c['role']}; host={ctx.get('host')}; "
        f"repo={ctx.get('repo_root')}; branch={ctx.get('branch')}; head={ctx.get('head')}; "
        f"mutation_policy={c['mutation_policy']}; publication={c['publication']}. "
        "Do not spend tokens re-discovering dev/prod by hostname/pwd unless this injected context conflicts with direct evidence."
    )


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            },
            ensure_ascii=False,
        )
    )


def allow_with_context(event: str, ctx: dict[str, Any]) -> None:
    if event in {"SessionStart", "UserPromptSubmit"} and ctx.get("contour"):
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": event,
                        "additionalContext": contour_text(ctx),
                    }
                },
                ensure_ascii=False,
            )
        )


def check_pre_tool(payload: dict[str, Any], ctx: dict[str, Any]) -> bool:
    if payload.get("tool_name") != "Bash":
        return True
    command = str((payload.get("tool_input") or {}).get("command") or "")
    contour = ctx.get("contour")
    if not contour:
        return True

    expected_host = contour["host"]
    expected_hosts = set(contour.get("host_aliases") or [expected_host])
    expected_repo = contour["repo"]
    expected_branch = contour["branch"]

    if ctx.get("host") not in expected_hosts and ctx.get("short_host") not in expected_hosts:
        if MUTATING_GIT_RE.search(command):
            deny(
                f"Managed contour mismatch: repo {expected_repo} must run on {expected_host}, "
                f"current host is {ctx.get('host')}. Mutating git command blocked."
            )
            return False

    if ctx.get("repo_root") != expected_repo:
        if MUTATING_GIT_RE.search(command):
            deny(
                f"Managed contour mismatch: expected repo {expected_repo}, current repo is {ctx.get('repo_root')}. "
                "Mutating git command blocked."
            )
            return False

    if ctx.get("branch") and ctx.get("branch") != expected_branch and MUTATING_GIT_RE.search(command):
        deny(
            f"Managed contour branch mismatch: {expected_repo} must use {expected_branch}, "
            f"current branch is {ctx.get('branch')}. Mutating git command blocked."
        )
        return False

    if contour["role"] == "prod":
        if COMMIT_RE.search(command) or PUSH_RE.search(command) or MUTATING_GIT_RE.search(command) and not PULL_RE.search(command):
            deny(
                "Production contour is read-only for agents: direct git mutations are blocked in "
                f"{expected_repo}. Make changes on agents@vds.intdata.pro:/int/data, publish origin/main, "
                "then refresh prod from origin."
            )
            return False

    if contour["role"] == "dev" and PUSH_RE.search(command):
        if "origin" not in command or "main" not in command:
            deny("Dev /int/data publication must target origin/main explicitly.")
            return False

    return True


def write_log(payload: dict[str, Any], ctx: dict[str, Any]) -> None:
    try:
        path = Path("/int/tools/.runtime/codex-hooks/events.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": payload.get("hook_event_name"),
            "session_id": payload.get("session_id"),
            "turn_id": payload.get("turn_id"),
            "host": ctx.get("host"),
            "cwd": ctx.get("cwd"),
            "repo_root": ctx.get("repo_root"),
            "branch": ctx.get("branch"),
            "contour": (ctx.get("contour") or {}).get("name"),
            "tool_name": payload.get("tool_name"),
            "command": (payload.get("tool_input") or {}).get("command"),
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main() -> int:
    payload = read_payload()
    event = str(payload.get("hook_event_name") or "")
    cwd = str(payload.get("cwd") or os.getcwd())
    ctx = discover_context(cwd)
    write_log(payload, ctx)

    if event == "PreToolUse" and not check_pre_tool(payload, ctx):
        return 0

    allow_with_context(event, ctx)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
