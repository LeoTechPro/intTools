#!/usr/bin/env python3
"""Repo-local Codex hook for intTools source/read-only contours."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


WINDOWS_REPO = "d:/int/tools"
LINUX_REPO = "/int/tools"
LINUX_READONLY_HOSTS = {"vds.intdata.pro", "vds.punkt-b.pro", "debian"}

SAFE_GIT_RE = re.compile(r"(^|[;&|]\s*)git\s+(status|diff|log|show|rev-parse|branch\s+--show-current|fetch|pull)\b", re.I)
MUTATING_GIT_RE = re.compile(r"(^|[;&|]\s*)git\s+(add|commit|push|reset|clean|checkout|switch|merge|rebase|cherry-pick|am|apply|stash|restore|rm|mv)\b", re.I)
WRITE_RE = re.compile(
    r"(^|[;&|]\s*)(rm|rmdir|del|erase|move|mv|copy|cp|install|touch|mkdir|ln|truncate|chmod|chown|"
    r"sed\s+-i|perl\s+-pi|npm\s+(install|ci|update|dedupe|audit\s+fix)|pnpm\s+(install|add|update|remove)|"
    r"yarn\s+(install|add|remove|upgrade)|python3?\b.*\b(write_text|open|mkdir|unlink|rmtree|copy|move)\b|"
    r"node\b.*\b(writeFile|mkdir|rm|unlink|copyFile|rename)\b|"
    r"powershell\b.*\b(Set-Content|Add-Content|Out-File|New-Item|Remove-Item|Move-Item|Copy-Item)\b|"
    r"pwsh\b.*\b(Set-Content|Add-Content|Out-File|New-Item|Remove-Item|Move-Item|Copy-Item)\b)",
    re.I | re.S,
)
REDIRECT_RE = re.compile(r"(^|[\s;&|])(?:cat|printf|echo|tee|type)\b.*?(>>?|1>|2>)", re.I | re.S)
OPENSPEC_WRITE_RE = re.compile(r"(openspec[/\\].*|[./\\]openspec[/\\])", re.I)
SECRET_ENV_RE = re.compile(r"(^|[\s'\"=:/\\])[^'\"\s]*\.env(?:\.[^'\"\s]+)?\b", re.I)
SECRET_ENV_EXAMPLE_RE = re.compile(r"\.env\.example\b|\.example\b", re.I)


def load_payload() -> dict[str, Any]:
    try:
        raw = sys.stdin.read().lstrip("\ufeff")
        starts = [idx for idx in (raw.find("{"), raw.find("[")) if idx >= 0]
        if starts:
            raw = raw[min(starts) :]
        return json.loads(raw)
    except Exception as exc:
        return {"hook_event_name": "unknown", "_parse_error": str(exc)}


def run_git(cwd: str, args: list[str]) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=2, check=False)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def norm_path(value: str) -> str:
    if not value:
        return ""
    return str(Path(value).resolve()).replace("\\", "/").rstrip("/").lower()


def context(cwd: str) -> dict[str, str]:
    host = socket.getfqdn() or socket.gethostname()
    short = socket.gethostname()
    root = run_git(cwd or ".", ["rev-parse", "--show-toplevel"])
    root_norm = norm_path(root)
    if root_norm == WINDOWS_REPO:
        contour = "windows-source"
    elif root_norm == LINUX_REPO and (host in LINUX_READONLY_HOSTS or short in LINUX_READONLY_HOSTS):
        contour = "linux-vds-readonly"
    elif root_norm == LINUX_REPO:
        contour = "linux-inttools"
    else:
        contour = "unmanaged"
    return {"host": host, "short_host": short, "repo_root": root_norm, "cwd": norm_path(cwd), "contour": contour}


def emit_context(event: str, text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}, ensure_ascii=False))


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}, ensure_ascii=False))


def tmp_write(command: str) -> bool:
    lowered = command.replace("\\", "/").lower()
    return any(marker in lowered for marker in ("/tmp/", "/var/tmp/", "/temp/", "/appdata/local/temp/"))


def approved(command: str, marker: str) -> bool:
    return f"{marker}=1" in command or os.environ.get(marker) == "1"


def readonly_reason(command: str) -> str | None:
    if MUTATING_GIT_RE.search(command):
        return "git mutations are blocked in VDS /int/tools read-only checkout"
    if SAFE_GIT_RE.search(command):
        return None
    if WRITE_RE.search(command):
        return "tracked/runtime mutations are blocked in VDS /int/tools read-only checkout"
    if REDIRECT_RE.search(command) and not tmp_write(command):
        return "redirect writes into /int/tools are blocked on VDS read-only checkout"
    return None


def source_reason(command: str) -> str | None:
    if re.search(r"(^|[;&|]\s*)git\s+push\b", command, re.I) and not approved(command, "INTTOOLS_PUSH_APPROVED"):
        return "git push from intTools requires owner approval marker INTTOOLS_PUSH_APPROVED=1"
    if OPENSPEC_WRITE_RE.search(command) and WRITE_RE.search(command) and not approved(command, "SPEC_MUTATION_APPROVED"):
        return "tracked intTools process/tooling mutations touching OpenSpec require SPEC_MUTATION_APPROVED=1"
    if re.search(r"(^|[;&|]\s*)git\s+add\b", command, re.I) and SECRET_ENV_RE.search(command) and not SECRET_ENV_EXAMPLE_RE.search(command):
        return "staging runtime env/secret files is blocked; only *.env.example or *.example are allowed"
    return None


def main() -> int:
    payload = load_payload()
    event = str(payload.get("hook_event_name") or "")
    cwd = str(payload.get("cwd") or os.getcwd())
    ctx = context(cwd)
    if ctx["contour"] == "unmanaged":
        return 0
    if event in {"SessionStart", "UserPromptSubmit"}:
        if ctx["contour"] == "linux-vds-readonly":
            emit_context(event, "Repo-local hook context: OS=Linux; repo=/int/tools; contour=VDS read-only mirror. Read and git fetch/pull refresh are allowed; tracked-file edits, dependency installs, commits and pushes are blocked. Source changes belong in D:\\int\\tools and flow through origin/main.")
        elif ctx["contour"] == "windows-source":
            emit_context(event, "Repo-local hook context: OS=Windows; repo=D:\\int\\tools; contour=source checkout. Source edits are allowed here. Push, OpenSpec mutations and secret staging require explicit approval markers and repo governance.")
        return 0
    if event == "PreToolUse" and payload.get("tool_name") == "Bash":
        command = str((payload.get("tool_input") or {}).get("command") or "")
        reason = readonly_reason(command) if ctx["contour"] == "linux-vds-readonly" else source_reason(command)
        if reason:
            deny(f"{reason}; detected host={ctx['short_host']}, repo={ctx['repo_root']}, cwd={ctx['cwd']}, contour={ctx['contour']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
