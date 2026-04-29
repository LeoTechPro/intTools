#!/usr/bin/env python3
"""Repo-local Codex hook for intData runtime context and guardrails."""

from __future__ import annotations

import getpass
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


OWNER_REPOS = {"crm", "id", "leonid", "nexus", "brain", "tools", "2brain", "intcrm-prototype"}
REFERENCE_REPOS = {"cabinet", "multica", "autoresearchclaw", "ngt-memory", "pb"}
PROJECT_MISSIONS = {
    "int": "master/manifest repo-set for intData projects, top-level layout, rules, public web source, and submodule pointers",
    "assess": "IntAssess consumer-product frontend shell for diagnostics, results, conclusions, public/staff UI, and backend contracts from data",
    "data": "canonical backend-core for the Intelligent Data family: Supabase/Postgres schema, RLS, RPC/PostgREST, Edge Functions, and backend-owned contracts",
    "probe": "standalone monitoring and Telegram-delivery contour for host/platform probes, alerts, recovery scripts, and probe contracts",
    "brain": "IntBrain standalone product monorepo for productivity-domain workflows, PARA, notes, tasks, resources, knowledge workflows, server, web, MCP, runtime, CLI, daemon, and desktop clients",
    "crm": "IntCRM consumer-product shell for CRM workspace UX, routes, runtime brand-config, user-facing docs, and backend contracts from data",
    "id": "standalone control-plane for SSO, secrets, entitlements, RBAC administration, access workflows, and IAM/admin operations",
    "leonid": "standalone public site for owner personal/public content, presentation assets, and related repo-level docs",
    "nexus": "standalone integration/runtime contour for connectors, workers, sync flows, operator UI, product bot runtime, contracts, and nexus-specific devops",
    "tools": "public open-source catalog of first-party intData tools, adapters, plugins, skills, gates, repo ops, and reusable automation utilities",
    "2brain": "markdown-first Obsidian vault for second-brain content, agent/workspace knowledge, wiki, PARA metadata, local skills, templates, and generated artifacts",
    "intcrm-prototype": "AI Studio generated prototype app for IntCRM experiments and local product validation",
}

SECRET_ENV_RE = re.compile(r"(^|[\s'\"=:/\\])[^'\"\s]*\.env(?:\.[^'\"\s]+)?\b", re.I)
SECRET_ENV_EXAMPLE_RE = re.compile(r"\.env\.example\b|\.example\b", re.I)
DESTRUCTIVE_GIT_RE = re.compile(r"(^|[;&|]\s*)git\s+(reset\s+--hard|clean\s+-[^\s]*[fdx]|rebase|filter-branch)\b", re.I)
PUSH_RE = re.compile(r"(^|[;&|]\s*)git\s+push\b", re.I)
MUTATING_GIT_RE = re.compile(
    r"(^|[;&|]\s*)git\s+(add|commit|push|reset|clean|checkout|switch|merge|rebase|cherry-pick|am|apply|stash|restore|rm|mv)\b",
    re.I,
)
WRITE_RE = re.compile(
    r"(^|[;&|]\s*)(rm|rmdir|del|erase|move|mv|copy|cp|install|touch|mkdir|ln|truncate|chmod|chown|"
    r"sed\s+-i|perl\s+-pi|dotnet\s+(restore|add|remove|new|tool\s+install|tool\s+update)|"
    r"npm\s+(install|ci|update|dedupe|audit\s+fix)|pnpm\s+(install|add|update|remove)|"
    r"yarn\s+(install|add|remove|upgrade)|"
    r"python3?\b.*\b(write_text|open|mkdir|unlink|rmtree|copy|move)\b|"
    r"node\b.*\b(writeFile|mkdir|rm|unlink|copyFile|rename)\b|"
    r"powershell\b.*\b(Set-Content|Add-Content|Out-File|New-Item|Remove-Item|Move-Item|Copy-Item)\b|"
    r"pwsh\b.*\b(Set-Content|Add-Content|Out-File|New-Item|Remove-Item|Move-Item|Copy-Item)\b)",
    re.I | re.S,
)
REDIRECT_RE = re.compile(r"(^|[\s;&|])(?:cat|printf|echo|tee|type)\b.*?(>>?|1>|2>)", re.I | re.S)
DEPLOY_RE = re.compile(
    r"(deploy|publish|systemctl|service\s+\w+\s+(restart|reload|start|stop)|docker\s+compose\s+(up|down|restart)|"
    r"kubectl|supabase\s+(db\s+push|migration)|psql\b.*\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b)",
    re.I | re.S,
)
PROD_RE = re.compile(r"(vds\.punkt-b\.pro|api\.punkt-b\.pro|/int/punkt-b|/int/punkt_b|\bprod\b|production)", re.I)


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


def norm_path(value: str) -> str:
    if not value:
        return ""
    return str(Path(value).resolve()).replace("\\", "/").rstrip("/")


def display_path(value: str) -> str:
    if re.match(r"^[A-Za-z]:/", value):
        return value.replace("/", "\\")
    return value


def hostnames() -> tuple[str, str]:
    host = socket.getfqdn() or socket.gethostname()
    short = socket.gethostname()
    return host, short


def repo_name_from_root(root_key: str) -> str:
    if root_key in {"d:/int", "/int"}:
        return "int"
    if root_key == "/int/punkt-b":
        return "data"
    return root_key.rsplit("/", 1)[-1]


def is_windows_root(root_key: str) -> bool:
    return root_key.startswith("d:/int")


def is_dev_vds(host: str, short: str) -> bool:
    return host in {"vds.intdata.pro", "debian"} or short in {"vds.intdata.pro", "debian"}


def is_prod_vds(host: str, short: str) -> bool:
    return host == "vds.punkt-b.pro" or short == "vds.punkt-b.pro"


def payload_context(cwd: str) -> dict[str, str]:
    host, short = hostnames()
    root = run_git(cwd or ".", ["rev-parse", "--show-toplevel"])
    if not root:
        try:
            root = str(Path(__file__).resolve().parents[2])
        except Exception:
            root = ""
    root_norm = norm_path(root)
    root_key = root_norm.lower()
    repo = repo_name_from_root(root_key)
    user = os.environ.get("USER") or getpass.getuser()

    contour = "unmanaged"
    if repo == "int":
        if root_key == "d:/int":
            contour = "local-master"
        elif root_key == "/int" and is_dev_vds(host, short):
            contour = "dev-vds-master"
    elif repo == "assess":
        contour = "local-source-push-manual" if is_windows_root(root_key) else "dev-vds-readonly"
    elif repo == "data":
        if root_key == "d:/int/data":
            contour = "local-source-backend"
        elif root_key == "/int/data" and is_dev_vds(host, short):
            contour = "dev-vds-backend"
        elif root_key == "/int/punkt-b" and is_prod_vds(host, short):
            contour = "prod-vds-backend"
    elif repo == "probe":
        contour = "local-source" if is_windows_root(root_key) else "dev-vds-source"
    elif repo in OWNER_REPOS:
        contour = "local-source" if is_windows_root(root_key) else "dev-vds-source"
    elif repo in REFERENCE_REPOS:
        contour = "reference-readonly"
    elif repo == "agent":
        contour = "unavailable-or-reference"

    return {
        "cwd": norm_path(cwd),
        "repo": repo,
        "repo_root": root_norm,
        "repo_root_key": root_key,
        "host": host,
        "short_host": short,
        "user": user,
        "contour": contour,
    }


def emit_context(event: str, text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}, ensure_ascii=False))


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}, ensure_ascii=False))


def approved(command: str, marker: str) -> bool:
    return f"{marker}=1" in command or os.environ.get(marker) == "1"


def tmp_write(command: str) -> bool:
    lowered = command.replace("\\", "/").lower()
    return any(marker in lowered for marker in ("/tmp/", "/var/tmp/", "/temp/", "/appdata/local/temp/", "/int/.tmp/"))


def context_prefix(root: str, contour: str, mission: str, scope: str = "Repo-local") -> str:
    return f"{scope} runtime context: repo_root={root}, contour={contour}, mission={mission}. "


def context_text(ctx: dict[str, str]) -> str:
    repo = ctx["repo"]
    root = display_path(ctx["repo_root"])
    contour = ctx["contour"]
    mission = PROJECT_MISSIONS.get(repo, "unclassified intData repository")

    if contour == "local-master":
        return (
            context_prefix(root, contour, mission, "Repo-set")
            + "This is the parent repo-set, not a product monorepo. "
            "Before edits, identify the owning submodule/repo. If the tree is clean and upstream is valid, git fetch + git pull --ff-only is recommended. "
            "If dirty/diverged/conflicted, show status and plan first. Parent gitlink updates are allowed only after a published submodule commit or explicit owner approval. "
            "Do not mix unrelated dirty state with gitlink updates. Push, destructive git, and delete outside D:/int require explicit owner approval."
        )
    if contour == "dev-vds-master":
        return (
            context_prefix(root, contour, mission, "Repo-set")
            + "This is the dev-vds parent repo-set. "
            "Work only in the owning submodule/repo. Update parent gitlinks only after checking the submodule commit and clean parent state. "
            "Pull --ff-only is allowed on clean trees. Push, deploy, and destructive git require explicit owner approval."
        )
    if contour == "local-source-push-manual":
        return (
            context_prefix(root, contour, mission)
            + "This is the owner local source checkout. "
            "If the tree is clean and upstream is valid, git fetch + git pull --ff-only is recommended. File edits are allowed within the task. "
            "Tracked mutations require repo policy/lockctl. Finished changes should be committed locally. "
            "Push/publish to origin is blocked unless the owner explicitly asks for it in the current conversation."
        )
    if contour == "dev-vds-readonly":
        return (
            context_prefix(root, contour, mission)
            + "This is a dev-vds read-only mirror. "
            "Read, diagnostics, and safe refresh via git fetch + git pull --ff-only on a clean tree are allowed. "
            "Edits, dependency install, commit, push, and backend/prod mutations require separate owner approval."
        )
    if contour == "local-source-backend":
        return (
            context_prefix(root, contour, mission)
            + "This is the local backend-core checkout. "
            "Edits are allowed only within the task and repo policy. Canonical dev backend execution checkout is usually agents@vds.intdata.pro:/int/data; canonical dev API host: api.intdata.pro. "
            "If the tree is clean, git fetch + git pull --ff-only is recommended. If dirty/diverged/conflicted, show status and plan first. "
            "Finished changes should be committed. Push, prod-targeting mutations, and secret staging require explicit owner approval."
        )
    if contour == "dev-vds-backend":
        return (
            context_prefix(root, contour, mission)[:-2]
            + ", api_host=api.intdata.pro. This is the dev backend provider checkout on vds.intdata.pro. "
            "Dev backend work is allowed according to the documented /int/data workflow. "
            "Check git status before work; pull --ff-only only on a clean tree. Finished changes should be committed. "
            "Push, prod-targeting mutations, and secret staging require explicit owner approval."
        )
    if contour == "prod-vds-backend":
        return (
            context_prefix(root, contour, mission)[:-2]
            + ", api_host=api.punkt-b.pro. This is the production backend provider on vds.punkt-b.pro. "
            "Default mode is read-first. Read, diagnostics, and safe git refresh on a clean tree are allowed. "
            "Production mutations, deploy/apply/service restart, commit/push, and secret staging require explicit owner approval marker INTDATA_PROD_MUTATION_APPROVED=1."
        )
    if repo == "probe" and contour == "dev-vds-source":
        return (
            context_prefix(root, contour, mission)
            + "This is the VDS source checkout for Probe. "
            "Source edits are allowed within the task and repo policy. Check git status before work; pull --ff-only only on a clean tree. "
            "Finished changes should be committed. Push and secret staging require explicit owner approval."
        )
    if contour == "reference-readonly":
        return (
            context_prefix(root, contour, mission)
            + "This is an external/reference checkout. "
            "Read, diagnostics, and safe refresh via git fetch + git pull --ff-only on a clean tree are allowed. "
            "File edits, dependency install, commit, push, and destructive git require separate owner approval."
        )
    if contour == "unavailable-or-reference":
        return (
            context_prefix(root, contour, mission)
            + "Worktree/git is not initialized or not confirmed. "
            "Do not edit, commit, or push; show state and ask for owner direction first."
        )
    if contour in {"local-source", "dev-vds-source"}:
        place = "owner local source checkout" if contour == "local-source" else "dev-vds source checkout"
        text = (
            context_prefix(root, contour, mission)
            + f"This is the {place}. "
            "If the tree is clean and upstream is valid, git fetch + git pull --ff-only is recommended. "
            "If dirty/diverged/conflicted, show status and plan first. File edits are allowed within the task. "
            "Tracked mutations require repo policy/lockctl. Finished changes should be committed locally. "
            "If checks pass and repo policy does not forbid it, push to origin is allowed as finish-flow."
        )
        if repo == "brain" and contour == "dev-vds-source":
            text += " Canonical user on vds.intdata.pro: agents."
        return text
    return ""


def guard_reason(command: str, ctx: dict[str, str]) -> str | None:
    repo = ctx["repo"]
    contour = ctx["contour"]
    if re.search(r"(^|[;&|]\s*)git\s+add\b", command, re.I) and SECRET_ENV_RE.search(command) and not SECRET_ENV_EXAMPLE_RE.search(command):
        return "staging runtime env/secret files is blocked; only *.env.example or *.example are allowed"
    if DESTRUCTIVE_GIT_RE.search(command) and not approved(command, "DESTRUCTIVE_GIT_APPROVED"):
        return "destructive git requires explicit owner approval marker DESTRUCTIVE_GIT_APPROVED=1"
    if contour == "reference-readonly":
        if MUTATING_GIT_RE.search(command):
            return "git mutations are blocked in reference-readonly checkout"
        if WRITE_RE.search(command):
            return "file/dependency mutations are blocked in reference-readonly checkout"
        if REDIRECT_RE.search(command) and not tmp_write(command):
            return "redirect writes into reference-readonly checkout are blocked"
    if contour == "dev-vds-readonly":
        if MUTATING_GIT_RE.search(command):
            return "git mutations are blocked in dev-vds read-only checkout"
        if WRITE_RE.search(command):
            return "file/dependency mutations are blocked in dev-vds read-only checkout"
        if REDIRECT_RE.search(command) and not tmp_write(command):
            return "redirect writes into dev-vds read-only checkout are blocked"
    if repo == "assess" and PUSH_RE.search(command) and not approved(command, "INTASSESS_PUSH_APPROVED"):
        return "git push from IntAssess requires direct owner approval marker INTASSESS_PUSH_APPROVED=1"
    if contour == "prod-vds-backend":
        if (DEPLOY_RE.search(command) or WRITE_RE.search(command) or PUSH_RE.search(command)) and not approved(command, "INTDATA_PROD_MUTATION_APPROVED"):
            return "production /int/punkt-b mutations require explicit owner approval marker INTDATA_PROD_MUTATION_APPROVED=1"
    if repo == "data" and contour in {"local-source-backend", "dev-vds-backend"}:
        if PROD_RE.search(command) and (DEPLOY_RE.search(command) or WRITE_RE.search(command)) and not approved(command, "INTDATA_PROD_MUTATION_APPROVED"):
            return "prod-targeting mutation from data checkout requires explicit owner approval marker INTDATA_PROD_MUTATION_APPROVED=1"
    if repo == "brain" and contour == "dev-vds-source" and ctx["user"] != "agents":
        return "Repo /int/brain on vds.intdata.pro must run under user 'agents'"
    if DEPLOY_RE.search(command) and not approved(command, "RUNTIME_MUTATION_APPROVED"):
        return "deploy/prod/service/apply actions require explicit owner approval marker RUNTIME_MUTATION_APPROVED=1"
    return None


def main() -> int:
    payload = load_payload()
    event = str(payload.get("hook_event_name") or "")
    cwd = str(payload.get("cwd") or os.getcwd())
    ctx = payload_context(cwd)
    if ctx["contour"] == "unmanaged":
        return 0

    if event in {"SessionStart", "UserPromptSubmit"}:
        text = context_text(ctx)
        if text:
            emit_context(event, text)
        return 0

    if event == "PreToolUse" and payload.get("tool_name") == "Bash":
        command = str((payload.get("tool_input") or {}).get("command") or "")
        reason = guard_reason(command, ctx)
        if reason:
            deny(f"{reason}; detected host={ctx['short_host']}, repo={ctx['repo_root']}, cwd={ctx['cwd']}, contour={ctx['contour']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
