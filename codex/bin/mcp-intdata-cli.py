#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo


PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "0.1.0"
IO_MODE = "framed"

ROOT_DIR = Path(__file__).resolve().parents[2]
INT_ROOT = ROOT_DIR.parent
ISSUE_RE = re.compile(r"^INT-\d+$")

LOCKCTL_DIR = ROOT_DIR / "lockctl"
if str(LOCKCTL_DIR) not in sys.path:
    sys.path.insert(0, str(LOCKCTL_DIR))

CODEX_LIB_DIR = ROOT_DIR / "codex" / "lib"
if str(CODEX_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(CODEX_LIB_DIR))

from lockctl_core import LockCtlError, cmd_acquire, cmd_gc, cmd_release_issue, cmd_release_path, cmd_renew, cmd_status
from intbrain_memory import IntBrainMemory


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}


COMMON_RUN_PROPS = {
    "cwd": {"type": "string", "description": "Working directory under D:/int. Defaults to D:/int/tools."},
    "timeout_sec": {"type": "integer", "description": "Command timeout in seconds."},
}


def _args_prop(description: str = "Structured command arguments.") -> dict[str, Any]:
    return {"type": "array", "items": {"type": "string"}, "description": description}


def _action_prop(actions: list[str], description: str = "Allowlisted action.") -> dict[str, Any]:
    return {"type": "string", "enum": actions, "description": description}


def _mutation_props() -> dict[str, Any]:
    return {
        "confirm_mutation": {"type": "boolean"},
        "issue_context": {"type": "string", "description": "Current Multica issue identifier, e.g. INT-202."},
    }


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"name": name, "description": description, "inputSchema": _schema(properties, required)}


def _load_browser_profile_registry() -> dict[str, dict[str, Any]]:
    path = ROOT_DIR / "codex" / "config" / "browser-profiles.v1.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    profiles = raw.get("profiles") if isinstance(raw, dict) else None
    if not isinstance(profiles, dict):
        raise RuntimeError(f"invalid browser profile registry: {path}")
    return profiles


BROWSER_PROFILE_REGISTRY = _load_browser_profile_registry()
BROWSER_PROFILE_NAMES = sorted(BROWSER_PROFILE_REGISTRY)


OPEN_SPEC_TOOLS = [
    _tool("openspec_list", "List OpenSpec changes or specs.", {**COMMON_RUN_PROPS, "specs": {"type": "boolean"}}),
    _tool(
        "openspec_show",
        "Show an OpenSpec change or spec.",
        {**COMMON_RUN_PROPS, "item": {"type": "string"}, "json": {"type": "boolean"}},
        ["item"],
    ),
    _tool(
        "openspec_validate",
        "Validate an OpenSpec change/spec or full catalog.",
        {**COMMON_RUN_PROPS, "item": {"type": "string"}, "strict": {"type": "boolean"}},
    ),
    _tool("openspec_status", "Show OpenSpec artifact completion status.", {**COMMON_RUN_PROPS, "item": {"type": "string"}}),
    _tool(
        "openspec_instructions",
        "Output enriched OpenSpec instructions for an artifact.",
        {**COMMON_RUN_PROPS, "artifact": {"type": "string"}, "args": _args_prop("Additional OpenSpec instruction arguments.")},
        ["artifact"],
    ),
    _tool(
        "openspec_archive",
        "Archive a completed OpenSpec change. Mutating; requires confirmation and issue context.",
        {**COMMON_RUN_PROPS, **_mutation_props(), "change_name": {"type": "string"}, "args": _args_prop()},
        ["confirm_mutation", "issue_context", "change_name"],
    ),
    _tool(
        "openspec_change_mutate",
        "Run a mutating `openspec change` subcommand. Requires confirmation and issue context.",
        {**COMMON_RUN_PROPS, **_mutation_props(), "subcommand": {"type": "string"}, "args": _args_prop()},
        ["confirm_mutation", "issue_context", "subcommand"],
    ),
    _tool(
        "openspec_spec_mutate",
        "Run a mutating `openspec spec` subcommand. Requires confirmation and issue context.",
        {**COMMON_RUN_PROPS, **_mutation_props(), "subcommand": {"type": "string"}, "args": _args_prop()},
        ["confirm_mutation", "issue_context", "subcommand"],
    ),
    _tool(
        "openspec_new",
        "Run `openspec new`. Mutating; requires confirmation and issue context.",
        {**COMMON_RUN_PROPS, **_mutation_props(), "args": _args_prop()},
        ["confirm_mutation", "issue_context"],
    ),
    _tool(
        "openspec_exec_mutate",
        "Run a mutating structured OpenSpec CLI command. Requires confirmation and issue context.",
        {**COMMON_RUN_PROPS, **_mutation_props(), "args": _args_prop("Arguments after the openspec executable.")},
        ["confirm_mutation", "issue_context", "args"],
    ),
]

GOVERNANCE_TOOLS = [
    _tool("routing_validate", "Validate high-risk agent tool routing registry.", {**COMMON_RUN_PROPS, "strict": {"type": "boolean"}, "json": {"type": "boolean"}}),
    _tool(
        "routing_resolve",
        "Resolve a logical high-risk tooling intent.",
        {**COMMON_RUN_PROPS, "intent": {"type": "string"}, "platform": {"type": "string"}, "json": {"type": "boolean"}},
        ["intent"],
    ),
    _tool(
        "gate_status",
        "Show gate receipts/bindings/approvals status.",
        {**COMMON_RUN_PROPS, "repo_root": {"type": "string"}, "issue": {"type": "string"}, "receipt_id": {"type": "string"}, "commit": {"type": "string"}, "gate": {"type": "string"}, "owner": {"type": "string"}, "format": {"type": "string", "enum": ["json", "text"]}},
    ),
    _tool(
        "gate_receipt",
        "Show a gate receipt by id or commit binding.",
        {**COMMON_RUN_PROPS, "repo_root": {"type": "string"}, "receipt_id": {"type": "string"}, "commit": {"type": "string"}, "format": {"type": "string", "enum": ["json", "text"]}},
    ),
    _tool(
        "commit_binding",
        "Bind a gate receipt to a commit. Mutating; requires confirmation.",
        {**COMMON_RUN_PROPS, **_mutation_props(), "repo_root": {"type": "string"}, "issue": {"type": "string"}, "receipt_id": {"type": "string"}, "commit_sha": {"type": "string"}, "repo": {"type": "string"}, "post_issue": {"type": "boolean"}, "format": {"type": "string", "enum": ["json", "text"]}},
        ["confirm_mutation", "issue_context", "commit_sha"],
    ),
]

RUNTIME_TOOLS = [
    _tool("host_preflight", "Run Codex preflight.", {**COMMON_RUN_PROPS, "json": {"type": "boolean"}}),
    _tool("host_verify", "Run Codex host verification.", {**COMMON_RUN_PROPS, "args": _args_prop()}),
    _tool("host_bootstrap", "Run Codex host bootstrap. Mutating; requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "args": _args_prop()}, ["confirm_mutation", "issue_context"]),
    _tool("recovery_bundle", "Create a Codex recovery bundle. Mutating; requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "args": _args_prop()}, ["confirm_mutation", "issue_context"]),
    _tool("ssh_resolve", "Resolve IntData SSH host transport.", {**COMMON_RUN_PROPS, "host": {"type": "string"}, "mode": {"type": "string"}, "json": {"type": "boolean"}}, ["host"]),
    _tool("ssh_host", "Print SSH host config/diagnostics, not an interactive shell.", {**COMMON_RUN_PROPS, "host": {"type": "string"}, "args": _args_prop()}, ["host"]),
    _tool(
        "browser_profile_launch",
        "Launch an allowed Firefox MCP profile. Mutating; requires confirmation.",
        {**COMMON_RUN_PROPS, **_mutation_props(), "profile": {"type": "string", "enum": BROWSER_PROFILE_NAMES}, "args": _args_prop("Optional launcher arguments.")},
        ["confirm_mutation", "issue_context", "profile"],
    ),
]

INTDB_TOOLS = [
    _tool("intdata_cli", "Run a profile allowlisted CLI command with structured arguments.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "args": _args_prop()}, ["command"]),
]

VAULT_TOOLS = [
    _tool("intdata_vault_sanitize", "Run vault sanitizer. Defaults to dry-run; non-dry-run requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "dry_run": {"type": "boolean"}, "args": _args_prop()}),
    _tool("intdata_runtime_vault_gc", "Run runtime vault GC. Defaults to dry-run; non-dry-run requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "dry_run": {"type": "boolean"}, "args": _args_prop()}),
]

LOCKCTL_TOOLS = [
    _tool(
        "lockctl_acquire",
        "Acquire or renew a lease lock for a file.",
        {
            "repo_root": {"type": "string"},
            "path": {"type": "string"},
            "owner": {"type": "string"},
            "issue": {"type": "string"},
            "reason": {"type": "string"},
            "lease_sec": {"type": "integer"},
        },
        ["repo_root", "path", "owner"],
    ),
    _tool(
        "lockctl_renew",
        "Renew an active lock by lock id.",
        {
            "lock_id": {"type": "string"},
            "lease_sec": {"type": "integer"},
        },
        ["lock_id"],
    ),
    _tool(
        "lockctl_release_path",
        "Release one active lock by repo/path for the same owner.",
        {
            "repo_root": {"type": "string"},
            "path": {"type": "string"},
            "owner": {"type": "string"},
        },
        ["repo_root", "path", "owner"],
    ),
    _tool(
        "lockctl_release_issue",
        "Release all active locks for an issue in repo root.",
        {
            "repo_root": {"type": "string"},
            "issue": {"type": "string"},
        },
        ["repo_root", "issue"],
    ),
    _tool(
        "lockctl_status",
        "Read active/expired lock status for repo/path/owner/issue.",
        {
            "repo_root": {"type": "string"},
            "path": {"type": "string"},
            "owner": {"type": "string"},
            "issue": {"type": "string"},
        },
        ["repo_root"],
    ),
    _tool("lockctl_gc", "Delete expired locks from runtime storage.", {}),
]

INTBRAIN_TOOLS = [
    _tool("intbrain_context_pack", "Retrieve context package for an entity/person query.", {"owner_id": {"type": "integer"}, "entity_id": {"type": "integer"}, "query": {"type": "string"}, "limit": {"type": "integer"}, "depth": {"type": "integer"}}, ["owner_id"]),
    _tool("intbrain_people_resolve", "Resolve people by query.", {"owner_id": {"type": "integer"}, "q": {"type": "string"}, "limit": {"type": "integer"}}, ["owner_id", "q"]),
    _tool("intbrain_people_get", "Get person profile by entity id.", {"owner_id": {"type": "integer"}, "entity_id": {"type": "integer"}}, ["owner_id", "entity_id"]),
    _tool("intbrain_graph_neighbors", "Get graph neighbors for entity.", {"owner_id": {"type": "integer"}, "entity_id": {"type": "integer"}, "depth": {"type": "integer"}, "limit": {"type": "integer"}, "link_type": {"type": "string"}}, ["owner_id", "entity_id"]),
    _tool("intbrain_context_store", "Store context item (write scope required).", {**_mutation_props(), "owner_id": {"type": "integer"}, "kind": {"type": "string"}, "title": {"type": "string"}, "text_content": {"type": "string"}, "entity_id": {"type": "integer"}, "source_path": {"type": "string"}, "source_hash": {"type": "string"}, "chunk_kind": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}, "source": {"type": "string"}, "priority": {"type": "integer"}}, ["confirm_mutation", "issue_context", "owner_id", "kind", "title", "text_content"]),
    _tool("intbrain_graph_link", "Create/update typed graph edge (write scope required).", {**_mutation_props(), "owner_id": {"type": "integer"}, "from_entity_id": {"type": "integer"}, "to_entity_id": {"type": "integer"}, "link_type": {"type": "string"}, "weight": {"type": "number"}, "confidence": {"type": "number"}, "source": {"type": "string"}, "source_path": {"type": "string"}, "metadata": {"type": "object"}}, ["confirm_mutation", "issue_context", "owner_id", "from_entity_id", "to_entity_id", "link_type"]),
    _tool("intbrain_people_policy_tg_get", "Get effective Telegram policy for person by tg_user_id.", {"owner_id": {"type": "integer"}, "tg_user_id": {"type": "integer"}, "chat_id": {"type": "string"}}, ["owner_id", "tg_user_id"]),
    _tool("intbrain_group_policy_get", "Get group policy by chat_id.", {"owner_id": {"type": "integer"}, "chat_id": {"type": "string"}}, ["owner_id", "chat_id"]),
    _tool("intbrain_group_policy_upsert", "Create/update group policy (write scope required).", {**_mutation_props(), "owner_id": {"type": "integer"}, "chat_id": {"type": "string"}, "name": {"type": "string"}, "respond_mode": {"type": "string"}, "access_mode": {"type": "string"}, "tools_policy": {"type": "string"}, "project_scope": {"type": "string"}, "notes": {"type": "string"}, "metadata": {"type": "object"}}, ["confirm_mutation", "issue_context", "owner_id", "chat_id", "respond_mode", "access_mode", "tools_policy"]),
    _tool("intbrain_jobs_list", "List jobs with optional filters.", {"owner_id": {"type": "integer"}, "enabled": {"type": "boolean"}, "kind": {"type": "string"}, "limit": {"type": "integer"}}, ["owner_id"]),
    _tool("intbrain_jobs_get", "Get job details by job_id.", {"owner_id": {"type": "integer"}, "job_id": {"type": "string"}}, ["owner_id", "job_id"]),
    _tool("intbrain_job_policy_upsert", "Create/update job policy override (write scope required).", {**_mutation_props(), "owner_id": {"type": "integer"}, "job_id": {"type": "string"}, "policy_mode": {"type": "string"}, "notes": {"type": "string"}, "metadata": {"type": "object"}}, ["confirm_mutation", "issue_context", "owner_id", "job_id", "policy_mode"]),
    _tool("intbrain_jobs_sync_runtime", "Sync runtime jobs into intbrain (import scope required).", {**_mutation_props(), "owner_id": {"type": "integer"}, "source_root": {"type": "string"}, "runtime_url": {"type": "string"}}, ["confirm_mutation", "issue_context", "owner_id"]),
    _tool("intbrain_policy_events_list", "List append-only policy events/provenance.", {"owner_id": {"type": "integer"}, "since": {"type": "string"}, "limit": {"type": "integer"}}, ["owner_id"]),
    _tool("intbrain_pm_dashboard", "Get PM dashboard with 5-9 constraint evaluation.", {"owner_id": {"type": "integer"}, "date": {"type": "string"}, "timezone": {"type": "string"}}, ["owner_id"]),
    _tool("intbrain_pm_tasks", "List PM tasks by view (today, week, backlog).", {"owner_id": {"type": "integer"}, "view": {"type": "string", "enum": ["today", "week", "backlog"]}, "date": {"type": "string"}, "timezone": {"type": "string"}, "limit": {"type": "integer"}}, ["owner_id"]),
    _tool("intbrain_pm_task_create", "Create PM task with PARA/OKR links and constraints.", {**_mutation_props(), "owner_id": {"type": "integer"}, "title": {"type": "string"}, "due_at": {"type": "string"}, "priority": {"type": "integer"}, "energy_cost": {"type": "integer"}, "project_entity_id": {"type": "integer"}, "area_entity_id": {"type": "integer"}, "goal_entity_id": {"type": "integer"}, "okr_entity_id": {"type": "integer"}, "key_result_entity_id": {"type": "integer"}, "source_path": {"type": "string"}, "source_hash": {"type": "string"}, "active_pin": {"type": "boolean"}, "timezone": {"type": "string"}}, ["confirm_mutation", "issue_context", "owner_id", "title"]),
    _tool("intbrain_pm_task_patch", "Patch PM task fields and status.", {**_mutation_props(), "task_id": {"type": "integer"}, "owner_id": {"type": "integer"}, "title": {"type": "string"}, "status": {"type": "string", "enum": ["open", "done", "archived"]}, "due_at": {"type": "string"}, "priority": {"type": "integer"}, "energy_cost": {"type": "integer"}, "project_entity_id": {"type": "integer"}, "area_entity_id": {"type": "integer"}, "goal_entity_id": {"type": "integer"}, "okr_entity_id": {"type": "integer"}, "key_result_entity_id": {"type": "integer"}, "active_pin": {"type": "boolean"}, "archive": {"type": "boolean"}, "timezone": {"type": "string"}}, ["confirm_mutation", "issue_context", "task_id", "owner_id"]),
    _tool("intbrain_pm_para", "Get PARA map (projects/areas/resources/archive) for owner.", {"owner_id": {"type": "integer"}}, ["owner_id"]),
    _tool("intbrain_pm_health", "Get PM health metrics and constraint summary.", {"owner_id": {"type": "integer"}, "date": {"type": "string"}, "timezone": {"type": "string"}}, ["owner_id"]),
    _tool("intbrain_pm_constraints_validate", "Validate PM 5-9 constraints for owner/date/timezone.", {"owner_id": {"type": "integer"}, "date": {"type": "string"}, "timezone": {"type": "string"}}, ["owner_id"]),
    _tool("intbrain_import_vault_pm", "Import PM/PARA data from 2brain vault (admin token required).", {**_mutation_props(), "owner_id": {"type": "integer"}, "source_root": {"type": "string"}, "timezone": {"type": "string"}}, ["confirm_mutation", "issue_context", "owner_id", "source_root"]),
    _tool("intbrain_memory_sync_sessions", "Import Codex/OpenClaw session memory into IntBrain.", {**_mutation_props(), "owner_id": {"type": "integer"}, "codex_home": {"type": "string"}, "state_path": {"type": "string"}, "source_root": {"type": "string"}, "since": {"type": "string"}, "file": {"type": "string"}, "incremental": {"type": "boolean"}, "dry_run": {"type": "boolean"}}, []),
    _tool("intbrain_memory_search", "Search previously imported IntBrain memory items.", {"owner_id": {"type": "integer"}, "query": {"type": "string"}, "limit": {"type": "integer"}, "days": {"type": "integer"}, "repo": {"type": "string"}}, ["owner_id", "query"]),
    _tool("intbrain_memory_recent_work", "Summarize recent in-scope local Codex/OpenClaw sessions.", {"codex_home": {"type": "string"}, "state_path": {"type": "string"}, "source_root": {"type": "string"}, "days": {"type": "integer"}, "limit": {"type": "integer"}, "repo": {"type": "string"}}, []),
    _tool("intbrain_memory_session_brief", "Build a concise brief for one Codex/OpenClaw session.", {"session_id": {"type": "string"}, "codex_home": {"type": "string"}, "state_path": {"type": "string"}, "source_root": {"type": "string"}}, ["session_id"]),
    _tool("intbrain_memory_import_mempalace", "Inventory or import MemPalace palace data into IntBrain.", {**_mutation_props(), "owner_id": {"type": "integer"}, "palace_root": {"type": "string"}, "codex_home": {"type": "string"}, "state_path": {"type": "string"}, "limit": {"type": "integer"}, "dry_run": {"type": "boolean"}}, ["palace_root"]),
]

RUNTIME_TOOLS.extend(VAULT_TOOLS)
CONTROL_TOOLS = [*LOCKCTL_TOOLS, *OPEN_SPEC_TOOLS, *GOVERNANCE_TOOLS]

PROFILE_TOOLS: dict[str, list[dict[str, Any]]] = {
    "intbrain": INTBRAIN_TOOLS,
    "intdata-control": CONTROL_TOOLS,
    "intdata-runtime": RUNTIME_TOOLS,
    "intdb": INTDB_TOOLS,
}

INTBRAIN_ALWAYS_MUTATING = {
    "intbrain_context_store",
    "intbrain_graph_link",
    "intbrain_group_policy_upsert",
    "intbrain_job_policy_upsert",
    "intbrain_jobs_sync_runtime",
    "intbrain_pm_task_create",
    "intbrain_pm_task_patch",
    "intbrain_import_vault_pm",
}

INTBRAIN_DRY_RUN_IMPORTS = {
    "intbrain_memory_sync_sessions",
    "intbrain_memory_import_mempalace",
}

READ_ONLY_MULTICA: dict[str, set[str]] = {
    "issue": {"get", "list", "search", "runs", "run-messages"},
    "project": {"get", "list"},
    "agent": {"get", "list", "tasks"},
    "workspace": {"get", "list"},
    "repo": {"get", "list"},
    "skill": {"get", "list"},
    "runtime": {"activity", "list", "ping", "usage"},
    "attachment": {"get", "list"},
    "config": {"get", "list"},
}

OPEN_SPEC_READ_ONLY = {
    "list",
    "show",
    "validate",
    "status",
    "instructions",
    "templates",
    "schemas",
    "completion",
    "help",
}

PROFILE_COMMANDS: dict[str, dict[str, list[str]]] = {
    "intdb": {
        "intdb": ["python", str(ROOT_DIR / "intdb" / "lib" / "intdb.py")],
    },
}

INTBRAIN_DEFAULT_API_BASE = "https://brain.api.intdata.pro/api/core/v1"
INTBRAIN_DEFAULT_TIMEOUT = 15.0
INTBRAIN_ENV_NAME = "intbrain-agent.env"
INTBRAIN_ENV_LOADED = False


def _as_int(raw: Any, default: int) -> int:
    try:
        return int(raw)
    except Exception:
        return default


def _bool_value(raw: Any, default: bool) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    token = str(raw).strip().lower()
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"0", "false", "no", "off"}:
        return False
    return default


def _float_value(raw: Any, default: float) -> float:
    try:
        return float(raw)
    except Exception:
        return default


def _parse_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key:
            continue
        os.environ.setdefault(key, value.strip())


def _load_intbrain_env_once() -> None:
    global INTBRAIN_ENV_LOADED
    if INTBRAIN_ENV_LOADED:
        return
    INTBRAIN_ENV_LOADED = True
    if os.environ.get("INTBRAIN_AGENT_ID") and os.environ.get("INTBRAIN_AGENT_KEY"):
        return

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    runtime_root = Path(os.environ.get("CODEX_RUNTIME_ROOT", ROOT_DIR / ".runtime"))
    secrets_root = Path(os.environ.get("CODEX_SECRETS_ROOT", runtime_root / "codex-secrets"))
    legacy_root = Path(os.environ.get("LEGACY_CODEX_VAR_ROOT", codex_home / "var"))
    _parse_env_file(secrets_root / INTBRAIN_ENV_NAME)
    _parse_env_file(legacy_root / INTBRAIN_ENV_NAME)


def _coerce_pm_date_alias(value: Any, timezone: str | None) -> Any:
    if not isinstance(value, str):
        return value
    token = value.strip().lower()
    if token not in {"today", "tomorrow", "yesterday"}:
        return value
    tz_name = timezone or "Europe/Moscow"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    base = datetime.now(tz=tz).date()
    if token == "tomorrow":
        base = base + timedelta(days=1)
    elif token == "yesterday":
        base = base - timedelta(days=1)
    return base.isoformat()


def _coerce_pm_date_args(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in {
        "intbrain_pm_dashboard",
        "intbrain_pm_tasks",
        "intbrain_pm_health",
        "intbrain_pm_constraints_validate",
        "intbrain_pm_task_create",
        "intbrain_pm_task_patch",
    }:
        return arguments
    args = dict(arguments)
    if "date" in args and isinstance(args["date"], str):
        args["date"] = _coerce_pm_date_alias(args["date"], args.get("timezone"))
    if name in {"intbrain_pm_task_create", "intbrain_pm_task_patch"} and "due_at" in args and isinstance(args["due_at"], str):
        if args["due_at"].strip().lower() == "today":
            tz_name = args.get("timezone") or "Europe/Moscow"
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = ZoneInfo("UTC")
            args["due_at"] = datetime.now(tz=tz).isoformat(timespec="seconds")
    return args


def _intbrain_http_json(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    use_agent_auth: bool = True,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, Any]:
    _load_intbrain_env_once()
    api_base = os.environ.get("INTBRAIN_API_BASE_URL", INTBRAIN_DEFAULT_API_BASE).rstrip("/")
    agent_id = os.environ.get("INTBRAIN_AGENT_ID", "").strip()
    agent_key = os.environ.get("INTBRAIN_AGENT_KEY", "").strip()
    timeout = _float_value(os.environ.get("INTBRAIN_API_TIMEOUT_SEC"), INTBRAIN_DEFAULT_TIMEOUT)

    if use_agent_auth and (not agent_id or not agent_key):
        raise RuntimeError("INTBRAIN_AGENT_ID and INTBRAIN_AGENT_KEY must be set")

    url = f"{api_base}/{path.lstrip('/')}"
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        if query:
            url = f"{url}?{query}"

    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    request = urllib.request.Request(url=url, method=method.upper(), data=data)
    request.add_header("Accept", "application/json")
    request.add_header("Content-Type", "application/json")
    if use_agent_auth:
        request.add_header("X-Agent-Id", agent_id)
        request.add_header("X-Agent-Key", agent_key)
    for header_name, header_value in (extra_headers or {}).items():
        request.add_header(header_name, header_value)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="ignore")
            if not raw:
                return response.status, {}
            return response.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore")
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"raw": raw}
        return int(exc.code), body


def _write_message(payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if IO_MODE == "jsonl":
        sys.stdout.write(body.decode("utf-8"))
        sys.stdout.write("\n")
        sys.stdout.flush()
        return
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def _read_message() -> dict[str, Any] | None:
    global IO_MODE
    first_line = sys.stdin.buffer.readline()
    if not first_line:
        return None
    first_decoded = first_line.decode("utf-8", errors="ignore").strip()
    if first_decoded.startswith("{"):
        IO_MODE = "jsonl"
        return json.loads(first_decoded)
    headers: dict[str, str] = {}
    line = first_line
    while True:
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("utf-8", errors="ignore").strip()
        if ":" in decoded:
            key, value = decoded.split(":", 1)
            headers[key.strip().lower()] = value.strip()
        line = sys.stdin.buffer.readline()
        if not line:
            return None
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def _json_result(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _json_error(req_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": error}


def _text_content(value: Any) -> dict[str, str]:
    return {"type": "text", "text": json.dumps(value, ensure_ascii=False)}


def _safe_args(raw: Any) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError("args must be an array of strings")
    return raw


def _cwd(raw: Any) -> str:
    base = Path(str(raw or ROOT_DIR)).resolve()
    allowed_roots = [ROOT_DIR.resolve(), INT_ROOT.resolve()]
    if not any(base == root or root in base.parents for root in allowed_roots):
        raise ValueError(f"cwd must be under {INT_ROOT}")
    return str(base)


def _require_mutation(arguments: dict[str, Any]) -> None:
    if arguments.get("confirm_mutation") is not True:
        raise PermissionError("mutating command requires confirm_mutation=true")
    issue = str(arguments.get("issue_context") or "").strip()
    if not ISSUE_RE.match(issue):
        raise PermissionError("mutating command requires issue_context like INT-202")


def _run(argv: list[str], *, cwd: str, timeout_sec: int | None = None) -> dict[str, Any]:
    timeout = int(timeout_sec or 60)
    completed = subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        shell=False,
    )
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "argv": argv,
        "cwd": cwd,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _openspec_base() -> list[str]:
    if os.name == "nt":
        return ["pwsh", "-File", str(ROOT_DIR / "codex" / "bin" / "openspec.ps1")]
    return [str(ROOT_DIR / "codex" / "bin" / "openspec")]


def _is_openspec_mutating(args: list[str]) -> bool:
    if not args:
        return False
    command = args[0]
    if command in OPEN_SPEC_READ_ONLY:
        return False
    if command in {"change", "spec"} and len(args) > 1 and args[1] in {"list", "show", "get"}:
        return False
    return True


def _call_openspec(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    cwd = _cwd(arguments.get("cwd"))
    timeout = arguments.get("timeout_sec")
    if name == "openspec_list":
        args = ["list"]
        if arguments.get("specs"):
            args.append("--specs")
    elif name == "openspec_show":
        args = ["show", str(arguments["item"])]
        if arguments.get("json"):
            args.append("--json")
    elif name == "openspec_validate":
        args = ["validate"]
        if arguments.get("strict"):
            args.append("--strict")
        if arguments.get("item"):
            args.append(str(arguments["item"]))
    elif name == "openspec_status":
        args = ["status"]
        if arguments.get("item"):
            args.append(str(arguments["item"]))
    elif name == "openspec_instructions":
        args = ["instructions", str(arguments["artifact"]), *_safe_args(arguments.get("args"))]
    elif name == "openspec_archive":
        _require_mutation(arguments)
        args = ["archive", str(arguments["change_name"]), *_safe_args(arguments.get("args"))]
    elif name == "openspec_change_mutate":
        _require_mutation(arguments)
        args = ["change", str(arguments["subcommand"]), *_safe_args(arguments.get("args"))]
        if not _is_openspec_mutating(args):
            raise ValueError("openspec_change_mutate cannot run read-only subcommands")
    elif name == "openspec_spec_mutate":
        _require_mutation(arguments)
        args = ["spec", str(arguments["subcommand"]), *_safe_args(arguments.get("args"))]
        if not _is_openspec_mutating(args):
            raise ValueError("openspec_spec_mutate cannot run read-only subcommands")
    elif name == "openspec_new":
        _require_mutation(arguments)
        args = ["new", *_safe_args(arguments.get("args"))]
    elif name == "openspec_exec_mutate":
        _require_mutation(arguments)
        args = _safe_args(arguments.get("args"))
        if not _is_openspec_mutating(args):
            raise ValueError("openspec_exec_mutate cannot run read-only commands")
    else:
        raise ValueError(f"unknown openspec tool: {name}")
    return _run([*_openspec_base(), *args], cwd=cwd, timeout_sec=timeout)


def _call_governance(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    cwd = _cwd(arguments.get("cwd"))
    timeout = arguments.get("timeout_sec")
    if name == "routing_validate":
        argv = ["python", str(ROOT_DIR / "codex" / "bin" / "agent_tool_routing.py"), "validate"]
        if arguments.get("strict"):
            argv.append("--strict")
        if arguments.get("json"):
            argv.append("--json")
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    if name == "routing_resolve":
        argv = ["python", str(ROOT_DIR / "codex" / "bin" / "agent_tool_routing.py"), "resolve", "--intent", str(arguments["intent"])]
        if arguments.get("platform"):
            argv.extend(["--platform", str(arguments["platform"])])
        if arguments.get("json"):
            argv.append("--json")
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    if name == "gate_status":
        argv = ["python", str(ROOT_DIR / "gatesctl" / "gatesctl.py"), "status"]
        if arguments.get("repo_root"):
            argv.extend(["--repo-root", str(arguments["repo_root"])])
        if arguments.get("issue"):
            argv.extend(["--issue", str(arguments["issue"])])
        if arguments.get("receipt_id"):
            argv.extend(["--receipt-id", str(arguments["receipt_id"])])
        if arguments.get("commit"):
            argv.extend(["--commit", str(arguments["commit"])])
        if arguments.get("gate"):
            argv.extend(["--gate", str(arguments["gate"])])
        if arguments.get("owner"):
            argv.extend(["--owner", str(arguments["owner"])])
        if arguments.get("format"):
            argv.extend(["--format", str(arguments["format"])])
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    if name == "gate_receipt":
        argv = ["python", str(ROOT_DIR / "gatesctl" / "gatesctl.py"), "show-receipt"]
        if arguments.get("repo_root"):
            argv.extend(["--repo-root", str(arguments["repo_root"])])
        if arguments.get("receipt_id"):
            argv.extend(["--receipt-id", str(arguments["receipt_id"])])
        if arguments.get("commit"):
            argv.extend(["--commit", str(arguments["commit"])])
        if arguments.get("format"):
            argv.extend(["--format", str(arguments["format"])])
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    if name == "commit_binding":
        _require_mutation(arguments)
        argv = ["python", str(ROOT_DIR / "gatesctl" / "gatesctl.py"), "bind-commit", "--commit-sha", str(arguments["commit_sha"])]
        if arguments.get("repo_root"):
            argv.extend(["--repo-root", str(arguments["repo_root"])])
        if arguments.get("issue"):
            argv.extend(["--issue", str(arguments["issue"])])
        if arguments.get("receipt_id"):
            argv.extend(["--receipt-id", str(arguments["receipt_id"])])
        if arguments.get("repo"):
            argv.extend(["--repo", str(arguments["repo"])])
        if arguments.get("post_issue"):
            argv.append("--post-issue")
        if arguments.get("format"):
            argv.extend(["--format", str(arguments["format"])])
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    raise ValueError(f"unknown governance tool: {name}")


def _call_runtime(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    cwd = _cwd(arguments.get("cwd"))
    timeout = arguments.get("timeout_sec")
    if name == "host_verify":
        return _run(["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "codex-host-verify.cmd"), *_safe_args(arguments.get("args"))], cwd=cwd, timeout_sec=timeout)
    if name == "host_preflight":
        argv = ["pwsh", "-File", str(ROOT_DIR / "scripts" / "codex" / "codex_preflight.ps1")]
        if arguments.get("json"):
            argv.append("-Json")
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    if name == "host_bootstrap":
        _require_mutation(arguments)
        return _run(["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "codex-host-bootstrap.cmd"), *_safe_args(arguments.get("args"))], cwd=cwd, timeout_sec=timeout or 300)
    if name == "recovery_bundle":
        _require_mutation(arguments)
        return _run(["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "codex-recovery-bundle.cmd"), *_safe_args(arguments.get("args"))], cwd=cwd, timeout_sec=timeout or 300)
    if name == "ssh_resolve":
        argv = [
            "python",
            str(ROOT_DIR / "codex" / "bin" / "int_ssh_resolve.py"),
            "--requested-host",
            str(arguments["host"]),
            "--capability",
            "int_ssh_resolve",
            "--binding-origin",
            "codex/bin/mcp-intdata-cli.py",
        ]
        if arguments.get("mode"):
            argv.extend(["--mode", str(arguments["mode"])])
        if arguments.get("json"):
            argv.append("--json")
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    if name == "ssh_host":
        argv = ["pwsh", "-File", str(ROOT_DIR / "codex" / "bin" / "int_ssh_host.ps1"), "-Logical", str(arguments["host"])]
        if arguments.get("args"):
            argv.extend(_safe_args(arguments.get("args")))
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    if name == "browser_profile_launch":
        _require_mutation(arguments)
        profile = str(arguments["profile"])
        profile_config = BROWSER_PROFILE_REGISTRY.get(profile)
        if not profile_config:
            raise ValueError(f"unknown browser profile: {profile}")
        argv = [
            "python",
            str(ROOT_DIR / "codex" / "bin" / "firefox_mcp_launcher.py"),
            "--capability",
            str(profile_config["capability"]),
            "--binding-origin",
            "codex/bin/mcp-intdata-cli.py",
            "--profile-key",
            str(profile_config["profile_key"]),
            "--start-url",
            str(profile_config["start_url"]),
            "--viewport",
            str(profile_config.get("viewport", "1440x900")),
            *_safe_args(arguments.get("args")),
        ]
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    raise ValueError(f"unknown runtime tool: {name}")


def _call_intdb(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name != "intdata_cli":
        raise ValueError(f"unknown intdb tool: {name}")
    command = str(arguments["command"])
    commands = PROFILE_COMMANDS["intdb"]
    if command not in commands:
        raise ValueError(f"unknown intdb command: {command}")
    args = _safe_args(arguments.get("args"))
    safe_intdb = (
        not args
        or args[:1] in (["doctor"], ["--help"], ["-h"], ["help"])
        or args[:2] == ["migrate", "status"]
    )
    if not safe_intdb:
        _require_mutation(arguments)
    return _run([*commands[command], *args], cwd=_cwd(arguments.get("cwd")), timeout_sec=arguments.get("timeout_sec"))


def _call_vault(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    cwd = _cwd(arguments.get("cwd"))
    dry_run = arguments.get("dry_run", True) is not False
    if not dry_run:
        _require_mutation(arguments)
    script = "vault_sanitize.py" if name == "intdata_vault_sanitize" else "runtime_vault_gc.py"
    argv = ["python", str(ROOT_DIR / "vault" / "installers" / script)]
    if dry_run:
        argv.append("--dry-run")
    argv.extend(_safe_args(arguments.get("args")))
    return _run(argv, cwd=cwd, timeout_sec=arguments.get("timeout_sec") or 300)


def _call_lockctl(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        if name == "lockctl_acquire":
            payload = cmd_acquire(
                argparse.Namespace(
                    repo_root=str(arguments.get("repo_root", "")),
                    path=str(arguments.get("path", "")),
                    owner=str(arguments.get("owner", "")),
                    issue=arguments.get("issue"),
                    reason=arguments.get("reason"),
                    lease_sec=_as_int(arguments.get("lease_sec"), 60),
                )
            )
        elif name == "lockctl_renew":
            payload = cmd_renew(
                argparse.Namespace(
                    lock_id=str(arguments.get("lock_id", "")),
                    lease_sec=_as_int(arguments.get("lease_sec"), 60),
                )
            )
        elif name == "lockctl_release_path":
            payload = cmd_release_path(
                argparse.Namespace(
                    repo_root=str(arguments.get("repo_root", "")),
                    path=str(arguments.get("path", "")),
                    owner=str(arguments.get("owner", "")),
                )
            )
        elif name == "lockctl_release_issue":
            payload = cmd_release_issue(
                argparse.Namespace(
                    repo_root=str(arguments.get("repo_root", "")),
                    issue=arguments.get("issue"),
                )
            )
        elif name == "lockctl_status":
            payload = cmd_status(
                argparse.Namespace(
                    repo_root=str(arguments.get("repo_root", "")),
                    path=arguments.get("path"),
                    owner=arguments.get("owner"),
                    issue=arguments.get("issue"),
                )
            )
        elif name == "lockctl_gc":
            payload = cmd_gc(argparse.Namespace())
        else:
            raise ValueError(f"unknown lockctl tool: {name}")
    except LockCtlError as exc:
        payload = {"ok": False, "error": exc.code, "message": exc.message, **exc.payload}
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error": "UNEXPECTED_ERROR", "message": str(exc)}
    return payload


def _scope_roots(source_root: object) -> list[str]:
    if isinstance(source_root, str) and source_root.strip():
        return [source_root.strip()]
    return ["D:/int", "/int"]


def _store_memory_items(*, owner_id: int, items: list[dict[str, Any]]) -> dict[str, Any]:
    stored_items: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for item in items:
        payload = {
            "owner_id": owner_id,
            "kind": item.get("kind", "fact"),
            "title": item.get("title"),
            "text_content": item.get("text_content"),
            "source_path": item.get("source_path"),
            "source_hash": item.get("source_hash"),
            "chunk_kind": item.get("chunk_kind"),
            "tags": item.get("tags") or [],
            "source": item.get("source"),
            "priority": item.get("priority", 3),
        }
        code, body = _intbrain_http_json("POST", "context/store", payload=payload)
        if 200 <= code < 300:
            stored_items.append(item)
        else:
            failures.append({"item": item.get("source_hash"), "http_status": code, "body": body})
    return {
        "ok": not failures,
        "stored_count": len(stored_items),
        "failed_count": len(failures),
        "stored_items": stored_items,
        "failures": failures,
    }


def _call_intbrain(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    args = _coerce_pm_date_args(name, dict(arguments))
    core_admin_token = os.environ.get("INTBRAIN_CORE_ADMIN_TOKEN", "").strip()
    if name in INTBRAIN_ALWAYS_MUTATING:
        _require_mutation(args)
    if name in INTBRAIN_DRY_RUN_IMPORTS and args.get("dry_run", True) is False:
        _require_mutation(args)

    if name == "intbrain_context_pack":
        code, body = _intbrain_http_json("POST", "context/pack", payload=args)
    elif name == "intbrain_people_resolve":
        code, body = _intbrain_http_json("GET", "people/resolve", params=args)
    elif name == "intbrain_people_get":
        entity_id = args.get("entity_id")
        if entity_id is None:
            return {"ok": False, "error": "entity_id_required"}
        code, body = _intbrain_http_json("GET", f"people/{entity_id}", params={"owner_id": args.get("owner_id")})
    elif name == "intbrain_graph_neighbors":
        code, body = _intbrain_http_json("GET", "graph/neighbors", params=args)
    elif name == "intbrain_context_store":
        code, body = _intbrain_http_json("POST", "context/store", payload=args)
    elif name == "intbrain_graph_link":
        code, body = _intbrain_http_json("POST", "graph/link", payload=args)
    elif name == "intbrain_people_policy_tg_get":
        code, body = _intbrain_http_json("GET", "people/policy/telegram", params=args)
    elif name == "intbrain_group_policy_get":
        chat_id = args.get("chat_id")
        if chat_id is None:
            return {"ok": False, "error": "chat_id_required"}
        code, body = _intbrain_http_json("GET", f"groups/{chat_id}/policy", params={"owner_id": args.get("owner_id")})
    elif name == "intbrain_group_policy_upsert":
        chat_id = args.get("chat_id")
        if chat_id is None:
            return {"ok": False, "error": "chat_id_required"}
        payload = dict(args)
        payload.pop("chat_id", None)
        code, body = _intbrain_http_json("POST", f"groups/{chat_id}/policy", payload=payload)
    elif name == "intbrain_jobs_list":
        code, body = _intbrain_http_json("GET", "jobs", params=args)
    elif name == "intbrain_jobs_get":
        job_id = args.get("job_id")
        if not job_id:
            return {"ok": False, "error": "job_id_required"}
        code, body = _intbrain_http_json("GET", f"jobs/{job_id}", params={"owner_id": args.get("owner_id")})
    elif name == "intbrain_job_policy_upsert":
        job_id = args.get("job_id")
        if not job_id:
            return {"ok": False, "error": "job_id_required"}
        payload = dict(args)
        payload.pop("job_id", None)
        code, body = _intbrain_http_json("POST", f"jobs/{job_id}/policy", payload=payload)
    elif name == "intbrain_jobs_sync_runtime":
        code, body = _intbrain_http_json("POST", "jobs/sync/runtime", payload=args)
    elif name == "intbrain_policy_events_list":
        code, body = _intbrain_http_json("GET", "policies/events", params=args)
    elif name == "intbrain_pm_dashboard":
        code, body = _intbrain_http_json("GET", "pm/dashboard", params=args)
    elif name == "intbrain_pm_tasks":
        code, body = _intbrain_http_json("GET", "pm/tasks", params=args)
    elif name == "intbrain_pm_task_create":
        code, body = _intbrain_http_json("POST", "pm/task", payload=args)
    elif name == "intbrain_pm_task_patch":
        task_id = args.get("task_id")
        if task_id is None:
            return {"ok": False, "error": "task_id_required"}
        payload = dict(args)
        payload.pop("task_id", None)
        code, body = _intbrain_http_json("PATCH", f"pm/task/{task_id}", payload=payload)
    elif name == "intbrain_pm_para":
        owner_id = args.get("owner_id")
        if owner_id is None:
            return {"ok": False, "error": "owner_id_required"}
        code, body = _intbrain_http_json("GET", f"pm/para/{owner_id}")
    elif name == "intbrain_pm_health":
        code, body = _intbrain_http_json("GET", "pm/health", params=args)
    elif name == "intbrain_pm_constraints_validate":
        code, body = _intbrain_http_json("POST", "pm/constraints/validate", payload=args)
    elif name == "intbrain_import_vault_pm":
        if not core_admin_token:
            return {"ok": False, "error": "config_error", "message": "INTBRAIN_CORE_ADMIN_TOKEN is required for intbrain_import_vault_pm"}
        code, body = _intbrain_http_json(
            "POST",
            "import/vault/pm",
            payload=args,
            use_agent_auth=False,
            extra_headers={"X-Core-Admin-Token": core_admin_token},
        )
    elif name == "intbrain_memory_sync_sessions":
        memory = IntBrainMemory(
            codex_home=args.get("codex_home"),
            state_path=args.get("state_path"),
            scope_roots=_scope_roots(args.get("source_root")),
        )
        summary = memory.extract_session_items(
            file_path=args.get("file"),
            since=args.get("since"),
            incremental=args.get("incremental", True) is not False,
        )
        if args.get("dry_run", True) is not False:
            return {"ok": True, "data": summary}
        owner_id = args.get("owner_id")
        if owner_id is None:
            return {"ok": False, "error": "owner_id_required"}
        stored = _store_memory_items(owner_id=int(owner_id), items=summary.get("items") or [])
        memory.mark_stored(stored["stored_items"])
        return {"ok": stored["ok"], "data": {**summary, **stored}}
    elif name == "intbrain_memory_search":
        payload = {
            "owner_id": args.get("owner_id"),
            "query": args.get("query"),
            "limit": args.get("limit", 10),
            "depth": 1,
            "source": "intbrain.memory",
        }
        if args.get("days") is not None:
            payload["days"] = args.get("days")
        if args.get("repo"):
            payload["repo"] = args.get("repo")
        code, body = _intbrain_http_json("POST", "context/pack", payload=payload)
    elif name == "intbrain_memory_recent_work":
        memory = IntBrainMemory(
            codex_home=args.get("codex_home"),
            state_path=args.get("state_path"),
            scope_roots=_scope_roots(args.get("source_root")),
        )
        return {"ok": True, "data": memory.recent_work(days=_as_int(args.get("days"), 7), limit=_as_int(args.get("limit"), 10), repo=args.get("repo"))}
    elif name == "intbrain_memory_session_brief":
        memory = IntBrainMemory(
            codex_home=args.get("codex_home"),
            state_path=args.get("state_path"),
            scope_roots=_scope_roots(args.get("source_root")),
        )
        brief = memory.session_brief(session_id=str(args.get("session_id")))
        return {"ok": brief is not None, "data": None if brief is None else asdict(brief)}
    elif name == "intbrain_memory_import_mempalace":
        memory = IntBrainMemory(
            codex_home=args.get("codex_home"),
            state_path=args.get("state_path"),
            scope_roots=_scope_roots(None),
        )
        summary = memory.import_mempalace(palace_root=str(args.get("palace_root")), limit=args.get("limit"))
        if args.get("dry_run", True) is not False:
            return {"ok": True, "data": summary}
        owner_id = args.get("owner_id")
        if owner_id is None:
            return {"ok": False, "error": "owner_id_required"}
        stored = _store_memory_items(owner_id=int(owner_id), items=summary.get("items") or [])
        memory.mark_stored(stored["stored_items"])
        return {"ok": stored["ok"], "data": {**summary, **stored}}
    else:
        raise ValueError(f"unknown intbrain tool: {name}")

    if 200 <= code < 300:
        return {"ok": True, "data": body}
    return {"ok": False, "http_status": code, "body": body}


def _call_tool(profile: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if profile == "intbrain":
        return _call_intbrain(name, arguments)
    if profile == "intdata-control":
        if name.startswith("lockctl_"):
            return _call_lockctl(name, arguments)
        if name.startswith("openspec_"):
            return _call_openspec(name, arguments)
        return _call_governance(name, arguments)
    if profile == "intdata-runtime":
        if name in {tool["name"] for tool in VAULT_TOOLS}:
            return _call_vault(name, arguments)
        return _call_runtime(name, arguments)
    if profile == "intdb":
        return _call_intdb(name, arguments)
    raise ValueError(f"unknown profile: {profile}")


def _handle(profile: str, request: dict[str, Any]) -> dict[str, Any] | None:
    req_id = request.get("id")
    method = str(request.get("method") or "")
    params = request.get("params") or {}
    if method == "initialize":
        requested = str((params or {}).get("protocolVersion") or "").strip()
        return _json_result(req_id, {"protocolVersion": requested or PROTOCOL_VERSION, "capabilities": {"tools": {}}, "serverInfo": {"name": f"{profile}-mcp", "version": SERVER_VERSION}})
    if method.startswith("notifications/"):
        return None
    if method == "ping":
        return _json_result(req_id, {})
    if method == "tools/list":
        return _json_result(req_id, {"tools": PROFILE_TOOLS[profile]})
    if method == "tools/call":
        name = str((params or {}).get("name") or "")
        arguments = (params or {}).get("arguments") or {}
        if not name:
            return _json_error(req_id, -32602, "tools/call requires name")
        try:
            payload = _call_tool(profile, name, dict(arguments))
            return _json_result(req_id, {"content": [_text_content(payload)], "isError": not bool(payload.get("ok"))})
        except Exception as exc:  # noqa: BLE001
            return _json_result(req_id, {"content": [_text_content({"ok": False, "error": str(exc)})], "isError": True})
    return _json_error(req_id, -32601, f"Method not found: {method}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, choices=sorted(PROFILE_TOOLS))
    args = parser.parse_args()
    while True:
        message = _read_message()
        if message is None:
            return 0
        response = _handle(args.profile, message)
        if response is not None:
            _write_message(response)


if __name__ == "__main__":
    raise SystemExit(main())
