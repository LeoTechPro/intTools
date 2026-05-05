#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "0.1.0"
IO_MODE = "framed"

ROOT_DIR = Path(__file__).resolve().parents[2]
INT_ROOT = ROOT_DIR.parent
BRAIN_MCP = INT_ROOT / "brain" / "mcp" / "intbrain" / "bin" / "mcp-intbrain.py"

LOCKCTL_DIR = ROOT_DIR / "lockctl"
if str(LOCKCTL_DIR) not in sys.path:
    sys.path.insert(0, str(LOCKCTL_DIR))

COORDCTL_DIR = ROOT_DIR / "coordctl"
if str(COORDCTL_DIR) not in sys.path:
    sys.path.insert(0, str(COORDCTL_DIR))

from lockctl_core import LockCtlError, cmd_acquire, cmd_gc, cmd_release_issue, cmd_release_path, cmd_renew, cmd_status
from coordctl_core import (
    CoordCtlError,
    cmd_gc as coordctl_cmd_gc,
    cmd_heartbeat as coordctl_cmd_heartbeat,
    cmd_cleanup as coordctl_cmd_cleanup,
    cmd_intent_acquire as coordctl_cmd_intent_acquire,
    cmd_merge_dry_run as coordctl_cmd_merge_dry_run,
    cmd_release as coordctl_cmd_release,
    cmd_session_start as coordctl_cmd_session_start,
    cmd_status as coordctl_cmd_status,
)


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}


COMMON_RUN_PROPS = {
    "cwd": {"type": "string", "description": "Working directory under D:/int. Defaults to D:/int/tools."},
    "timeout_sec": {"type": "integer", "description": "Command timeout in seconds."},
}


def _args_prop(description: str = "Structured command arguments.") -> dict[str, Any]:
    return {"type": "array", "items": {"type": "string"}, "description": description}


def _path_prop(description: str) -> dict[str, Any]:
    return {"type": "string", "description": description}


def _mutation_props() -> dict[str, Any]:
    return {
        "confirm_mutation": {"type": "boolean"},
        "issue_context": {"type": "string", "description": "Current Multica issue identifier, e.g. INT-222."},
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
    _tool("openspec_show", "Show an OpenSpec change or spec.", {**COMMON_RUN_PROPS, "item": {"type": "string"}, "json": {"type": "boolean"}}, ["item"]),
    _tool("openspec_validate", "Validate an OpenSpec change/spec or full catalog.", {**COMMON_RUN_PROPS, "item": {"type": "string"}, "strict": {"type": "boolean"}}),
    _tool("openspec_status", "Show OpenSpec artifact completion status.", {**COMMON_RUN_PROPS, "item": {"type": "string"}}),
    _tool("openspec_instructions", "Output enriched OpenSpec instructions for an artifact.", {**COMMON_RUN_PROPS, "artifact": {"type": "string"}, "args": _args_prop("Additional OpenSpec instruction arguments.")}, ["artifact"]),
    _tool("openspec_archive", "Archive a completed OpenSpec change. Mutating; requires confirmation and issue context.", {**COMMON_RUN_PROPS, **_mutation_props(), "change_name": {"type": "string"}, "args": _args_prop()}, ["confirm_mutation", "issue_context", "change_name"]),
    _tool("openspec_change_mutate", "Run a mutating `openspec change` subcommand. Requires confirmation and issue context.", {**COMMON_RUN_PROPS, **_mutation_props(), "subcommand": {"type": "string"}, "args": _args_prop()}, ["confirm_mutation", "issue_context", "subcommand"]),
    _tool("openspec_spec_mutate", "Run a mutating `openspec spec` subcommand. Requires confirmation and issue context.", {**COMMON_RUN_PROPS, **_mutation_props(), "subcommand": {"type": "string"}, "args": _args_prop()}, ["confirm_mutation", "issue_context", "subcommand"]),
    _tool("openspec_new", "Run `openspec new`. Mutating; requires confirmation and issue context.", {**COMMON_RUN_PROPS, **_mutation_props(), "args": _args_prop()}, ["confirm_mutation", "issue_context"]),
    _tool("openspec_exec_mutate", "Run a mutating structured OpenSpec CLI command. Requires confirmation and issue context.", {**COMMON_RUN_PROPS, **_mutation_props(), "args": _args_prop("Arguments after the openspec executable.")}, ["confirm_mutation", "issue_context", "args"]),
]

GOVERNANCE_TOOLS = [
    _tool("routing_validate", "Validate high-risk agent tool routing registry.", {**COMMON_RUN_PROPS, "strict": {"type": "boolean"}, "json": {"type": "boolean"}}),
    _tool("routing_resolve", "Resolve a logical high-risk tooling intent.", {**COMMON_RUN_PROPS, "intent": {"type": "string"}, "platform": {"type": "string"}, "json": {"type": "boolean"}}, ["intent"]),
    _tool("gate_status", "Show gate receipts/bindings/approvals status.", {**COMMON_RUN_PROPS, "repo_root": {"type": "string"}, "issue": {"type": "string"}, "receipt_id": {"type": "string"}, "commit": {"type": "string"}, "gate": {"type": "string"}, "owner": {"type": "string"}, "format": {"type": "string", "enum": ["json", "text"]}}),
    _tool("gate_receipt", "Show a gate receipt by id or commit binding.", {**COMMON_RUN_PROPS, "repo_root": {"type": "string"}, "receipt_id": {"type": "string"}, "commit": {"type": "string"}, "format": {"type": "string", "enum": ["json", "text"]}}),
    _tool("commit_binding", "Bind a gate receipt to a commit. Mutating; requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "repo_root": {"type": "string"}, "issue": {"type": "string"}, "receipt_id": {"type": "string"}, "commit_sha": {"type": "string"}, "repo": {"type": "string"}, "post_issue": {"type": "boolean"}, "format": {"type": "string", "enum": ["json", "text"]}}, ["confirm_mutation", "issue_context", "commit_sha"]),
]

RUNTIME_TOOLS = [
    _tool("host_preflight", "Run Codex preflight.", {**COMMON_RUN_PROPS, "json": {"type": "boolean"}}),
    _tool("host_verify", "Run Codex host verification.", {**COMMON_RUN_PROPS, "args": _args_prop()}),
    _tool("host_bootstrap", "Run Codex host bootstrap. Mutating; requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "args": _args_prop()}, ["confirm_mutation", "issue_context"]),
    _tool("recovery_bundle", "Create a Codex recovery bundle. Mutating; requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "args": _args_prop()}, ["confirm_mutation", "issue_context"]),
    _tool("ssh_resolve", "Resolve IntData SSH host transport and optional destination-only diagnostics.", {**COMMON_RUN_PROPS, "host": {"type": "string"}, "mode": {"type": "string"}, "json": {"type": "boolean"}, "destination_only": {"type": "boolean"}}, ["host"]),
    _tool("browser_profile_launch", "Deprecated compatibility: launch an allowed Firefox MCP profile. Mutating; requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "profile": {"type": "string", "enum": BROWSER_PROFILE_NAMES}, "args": _args_prop("Optional launcher arguments.")}, ["confirm_mutation", "issue_context", "profile"]),
]

DBA_TOOLS = [
    _tool("intdata_cli", "Run a profile allowlisted CLI command with structured arguments.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "profile": {"type": "string", "description": "DBA profile injected as --profile/--target for commands that require one."}, "args": _args_prop()}, ["command"]),
]

VAULT_TOOLS = [
    _tool("intdata_vault_sanitize", "Run vault sanitizer. Defaults to dry-run; non-dry-run requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "dry_run": {"type": "boolean"}, "vault_root": _path_prop("Vault root. Defaults to D:/int/2brain on this host."), "brain_root": _path_prop("Brain repo root. Defaults to D:/int/brain on this host."), "tools_root": _path_prop("Tools repo root. Defaults to D:/int/tools."), "runtime_root": _path_prop("Runtime vault root override."), "args": _args_prop()}),
    _tool("intdata_runtime_vault_gc", "Run runtime vault GC. Defaults to dry-run; non-dry-run requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "dry_run": {"type": "boolean"}, "brain_root": _path_prop("Brain repo root. Defaults to D:/int/brain on this host."), "runtime_root": _path_prop("Runtime vault root override."), "archive_root": _path_prop("Archive root override. Defaults to D:/int/.tmp."), "args": _args_prop()}),
]

LOCKCTL_TOOLS = [
    _tool("lockctl_acquire", "Acquire or renew a lease lock for a file.", {"repo_root": {"type": "string"}, "path": {"type": "string"}, "owner": {"type": "string"}, "issue": {"type": "string"}, "reason": {"type": "string"}, "lease_sec": {"type": "integer"}}, ["repo_root", "path", "owner"]),
    _tool("lockctl_renew", "Renew an active lock by lock id.", {"lock_id": {"type": "string"}, "lease_sec": {"type": "integer"}}, ["lock_id"]),
    _tool("lockctl_release_path", "Release one active lock by repo/path for the same owner.", {"repo_root": {"type": "string"}, "path": {"type": "string"}, "owner": {"type": "string"}}, ["repo_root", "path", "owner"]),
    _tool("lockctl_release_issue", "Release all active locks for an issue in repo root.", {"repo_root": {"type": "string"}, "issue": {"type": "string"}}, ["repo_root", "issue"]),
    _tool("lockctl_status", "Read active/expired lock status for repo/path/owner/issue.", {"repo_root": {"type": "string"}, "path": {"type": "string"}, "owner": {"type": "string"}, "issue": {"type": "string"}}, ["repo_root"]),
    _tool("lockctl_gc", "Delete expired locks from runtime storage.", {}),
]

COORDCTL_TOOLS = [
    _tool("coordctl_session_start", "Start a Git-aware coordination session for an agent branch.", {"repo_root": {"type": "string"}, "owner": {"type": "string"}, "issue": {"type": "string"}, "branch": {"type": "string"}, "base": {"type": "string"}, "worktree_path": {"type": "string"}, "lease_sec": {"type": "integer"}}, ["repo_root", "owner", "branch", "base"]),
    _tool("coordctl_intent_acquire", "Acquire or renew a Git-aware edit intent for a file region.", {"repo_root": {"type": "string"}, "path": {"type": "string"}, "owner": {"type": "string"}, "issue": {"type": "string"}, "base": {"type": "string"}, "region_kind": {"type": "string", "enum": ["file", "hunk", "symbol", "json_path", "section"]}, "region_id": {"type": "string"}, "lease_sec": {"type": "integer"}, "session_id": {"type": "string"}}, ["repo_root", "path", "owner", "base", "region_kind", "region_id"]),
    _tool("coordctl_status", "Read active coordctl sessions and region leases.", {"repo_root": {"type": "string"}, "path": {"type": "string"}, "owner": {"type": "string"}, "issue": {"type": "string"}, "all": {"type": "boolean"}}, ["repo_root"]),
    _tool("coordctl_heartbeat", "Renew a coordctl session and its active region leases.", {"session_id": {"type": "string"}, "lease_sec": {"type": "integer"}}, ["session_id"]),
    _tool("coordctl_release", "Release coordctl sessions and region leases by session or issue.", {"session_id": {"type": "string"}, "repo_root": {"type": "string"}, "issue": {"type": "string"}}, []),
    _tool("coordctl_cleanup", "Dry-run or apply required cleanup for a coordctl session.", {"session_id": {"type": "string"}, "final_state": {"type": "string", "enum": ["merged", "released", "abandoned", "blocked-owner", "failed-cleanup"]}, "delete_worktree": {"type": "boolean"}, "delete_branch": {"type": "boolean"}, "dry_run": {"type": "boolean"}, "apply": {"type": "boolean"}}, ["session_id"]),
    _tool("coordctl_gc", "Dry-run or delete expired/final coordctl sessions and region leases.", {"dry_run": {"type": "boolean"}, "apply": {"type": "boolean"}}),
    _tool("coordctl_merge_dry_run", "Check whether two Git refs merge cleanly without changing tracked files.", {"repo_root": {"type": "string"}, "target": {"type": "string"}, "branch": {"type": "string"}}, ["repo_root", "target", "branch"]),
]

RUNTIME_TOOLS.extend(VAULT_TOOLS)
CONTROL_TOOLS = [*LOCKCTL_TOOLS, *COORDCTL_TOOLS, *OPEN_SPEC_TOOLS, *GOVERNANCE_TOOLS]
PROFILE_TOOLS: dict[str, list[dict[str, Any]]] = {
    "intbrain": [],
    "intdata-control": CONTROL_TOOLS,
    "intdata-runtime": RUNTIME_TOOLS,
    "dba": DBA_TOOLS,
}

OPEN_SPEC_READ_ONLY = {"list", "show", "validate", "status", "instructions", "templates", "schemas", "completion", "help"}
PROFILE_COMMANDS: dict[str, dict[str, list[str]]] = {"dba": {"dba": ["python", str(ROOT_DIR / "dba" / "lib" / "dba.py")]}}


def _as_int(raw: Any, default: int) -> int:
    try:
        return int(raw)
    except Exception:
        return default


def _safe_args(raw: Any) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError("args must be an array of strings")
    return raw


def _string_arg(arguments: dict[str, Any], key: str) -> str | None:
    raw = arguments.get(key)
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def _append_path_arg(argv: list[str], arguments: dict[str, Any], key: str, flag: str, default: Path | None = None) -> None:
    value = _string_arg(arguments, key)
    if value is None and default is not None:
        value = str(default)
    if value:
        argv.extend([flag, value])


def _has_arg(args: list[str], flag: str) -> bool:
    return flag in args


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
    if not issue.startswith("INT-"):
        raise PermissionError("mutating command requires issue_context like INT-222")


def _run(argv: list[str], *, cwd: str, timeout_sec: int | None = None) -> dict[str, Any]:
    timeout = int(timeout_sec or 60)
    completed = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=timeout, shell=False)
    return {"ok": completed.returncode == 0, "returncode": completed.returncode, "argv": argv, "cwd": cwd, "stdout": completed.stdout, "stderr": completed.stderr}


def _powershell_base() -> list[str]:
    candidates = ("pwsh", "powershell.exe", "powershell") if os.name == "nt" else ("pwsh", "powershell")
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return [resolved, "-NoProfile", "-ExecutionPolicy", "Bypass"]
    fallback = "powershell.exe" if os.name == "nt" else "pwsh"
    return [fallback, "-NoProfile", "-ExecutionPolicy", "Bypass"]


def _openspec_base() -> list[str]:
    if os.name == "nt":
        return [*_powershell_base(), "-File", str(ROOT_DIR / "codex" / "bin" / "openspec.ps1")]
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
        for key, flag in (("repo_root", "--repo-root"), ("issue", "--issue"), ("receipt_id", "--receipt-id"), ("commit", "--commit"), ("gate", "--gate"), ("owner", "--owner"), ("format", "--format")):
            if arguments.get(key):
                argv.extend([flag, str(arguments[key])])
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    if name == "gate_receipt":
        argv = ["python", str(ROOT_DIR / "gatesctl" / "gatesctl.py"), "show-receipt"]
        for key, flag in (("repo_root", "--repo-root"), ("receipt_id", "--receipt-id"), ("commit", "--commit"), ("format", "--format")):
            if arguments.get(key):
                argv.extend([flag, str(arguments[key])])
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    if name == "commit_binding":
        _require_mutation(arguments)
        argv = ["python", str(ROOT_DIR / "gatesctl" / "gatesctl.py"), "bind-commit", "--commit-sha", str(arguments["commit_sha"])]
        for key, flag in (("repo_root", "--repo-root"), ("issue", "--issue"), ("receipt_id", "--receipt-id"), ("repo", "--repo"), ("format", "--format")):
            if arguments.get(key):
                argv.extend([flag, str(arguments[key])])
        if arguments.get("post_issue"):
            argv.append("--post-issue")
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    raise ValueError(f"unknown governance tool: {name}")


def _call_runtime(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    cwd = _cwd(arguments.get("cwd"))
    timeout = arguments.get("timeout_sec")
    if name == "host_verify":
        payload = _run(["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "codex-host-verify.cmd"), *_safe_args(arguments.get("args"))], cwd=cwd, timeout_sec=timeout)
        output = f"{payload.get('stdout', '')}\n{payload.get('stderr', '')}"
        verify_ok = payload["returncode"] == 0 and "codex host verify: FAILED" not in output
        payload["verify_ok"] = verify_ok
        payload["ok"] = verify_ok
        return payload
    if name == "host_preflight":
        argv = [*_powershell_base(), "-File", str(ROOT_DIR / "codex" / "scripts" / "codex_preflight.ps1")]
        if arguments.get("json"):
            argv.append("-Json")
        payload = _run(argv, cwd=cwd, timeout_sec=timeout)
        payload["preflight_ok"] = payload["ok"]
        payload["ok"] = True
        return payload
    if name == "host_bootstrap":
        _require_mutation(arguments)
        return _run(["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "codex-host-bootstrap.cmd"), *_safe_args(arguments.get("args"))], cwd=cwd, timeout_sec=timeout or 300)
    if name == "recovery_bundle":
        _require_mutation(arguments)
        return _run(["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "codex-recovery-bundle.cmd"), *_safe_args(arguments.get("args"))], cwd=cwd, timeout_sec=timeout or 300)
    if name == "ssh_resolve":
        argv = ["python", str(ROOT_DIR / "codex" / "bin" / "int_ssh_resolve.py"), "--requested-host", str(arguments["host"]), "--capability", "int_ssh_resolve", "--binding-origin", "codex/bin/mcp-intdata-cli.py"]
        if arguments.get("mode"):
            argv.extend(["--mode", str(arguments["mode"])])
        if arguments.get("json"):
            argv.append("--json")
        if arguments.get("destination_only"):
            argv.append("--destination-only")
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    if name == "browser_profile_launch":
        _require_mutation(arguments)
        profile = str(arguments["profile"])
        profile_config = BROWSER_PROFILE_REGISTRY.get(profile)
        if not profile_config:
            raise ValueError(f"unknown browser profile: {profile}")
        argv = ["python", str(ROOT_DIR / "codex" / "bin" / "firefox_mcp_launcher.py"), "--capability", str(profile_config["capability"]), "--binding-origin", "codex/bin/mcp-intdata-cli.py", "--profile-key", str(profile_config["profile_key"]), "--start-url", str(profile_config["start_url"]), "--viewport", str(profile_config.get("viewport", "1440x900")), *_safe_args(arguments.get("args"))]
        return _run(argv, cwd=cwd, timeout_sec=timeout)
    raise ValueError(f"unknown runtime tool: {name}")


def _call_dba(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name != "intdata_cli":
        raise ValueError(f"unknown dba tool: {name}")
    command = str(arguments["command"])
    commands = PROFILE_COMMANDS["dba"]
    if command not in commands:
        raise ValueError(f"unknown dba command: {command}")
    args = _safe_args(arguments.get("args"))
    profile = _string_arg(arguments, "profile")
    if profile and args:
        if args[:1] in (["doctor"], ["sql"], ["file"]) and "--profile" not in args:
            args = [args[0], "--profile", profile, *args[1:]]
        elif args[:2] == ["migrate", "status"] and "--target" not in args:
            args = [args[0], args[1], "--target", profile, *args[2:]]
    safe_dba = not args or args[:1] in (["doctor"], ["--help"], ["-h"], ["help"]) or args[:2] == ["migrate", "status"]
    if not safe_dba:
        _require_mutation(arguments)
    return _run([*commands[command], *args], cwd=_cwd(arguments.get("cwd")), timeout_sec=arguments.get("timeout_sec"))


def _call_vault(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    cwd = _cwd(arguments.get("cwd"))
    args = _safe_args(arguments.get("args"))
    dry_run = arguments.get("dry_run", True) is not False
    if dry_run and _has_arg(args, "--apply"):
        raise ValueError("--apply requires dry_run=false and mutation confirmation")
    if not dry_run and _has_arg(args, "--dry-run"):
        raise ValueError("dry_run=false cannot be combined with --dry-run")
    if not dry_run:
        _require_mutation(arguments)
    script = "vault_sanitize.py" if name == "intdata_vault_sanitize" else "runtime_vault_gc.py"
    argv = ["python", str(ROOT_DIR / "vault" / "installers" / script)]
    if dry_run:
        argv.append("--dry-run")
    else:
        argv.append("--apply")
    if name == "intdata_vault_sanitize":
        _append_path_arg(argv, arguments, "vault_root", "--vault-root", INT_ROOT / "2brain")
        _append_path_arg(argv, arguments, "brain_root", "--brain-root", INT_ROOT / "brain")
        _append_path_arg(argv, arguments, "tools_root", "--tools-root", ROOT_DIR)
        _append_path_arg(argv, arguments, "runtime_root", "--runtime-root")
    else:
        _append_path_arg(argv, arguments, "brain_root", "--brain-root", INT_ROOT / "brain")
        _append_path_arg(argv, arguments, "runtime_root", "--runtime-root")
        _append_path_arg(argv, arguments, "archive_root", "--archive-root")
    argv.extend(args)
    return _run(argv, cwd=cwd, timeout_sec=arguments.get("timeout_sec") or 300)


def _call_lockctl(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        if name == "lockctl_acquire":
            payload = cmd_acquire(argparse.Namespace(repo_root=str(arguments.get("repo_root", "")), path=str(arguments.get("path", "")), owner=str(arguments.get("owner", "")), issue=arguments.get("issue"), reason=arguments.get("reason"), lease_sec=_as_int(arguments.get("lease_sec"), 60)))
        elif name == "lockctl_renew":
            payload = cmd_renew(argparse.Namespace(lock_id=str(arguments.get("lock_id", "")), lease_sec=_as_int(arguments.get("lease_sec"), 60)))
        elif name == "lockctl_release_path":
            payload = cmd_release_path(argparse.Namespace(repo_root=str(arguments.get("repo_root", "")), path=str(arguments.get("path", "")), owner=str(arguments.get("owner", ""))))
        elif name == "lockctl_release_issue":
            payload = cmd_release_issue(argparse.Namespace(repo_root=str(arguments.get("repo_root", "")), issue=arguments.get("issue")))
        elif name == "lockctl_status":
            payload = cmd_status(argparse.Namespace(repo_root=str(arguments.get("repo_root", "")), path=arguments.get("path"), owner=arguments.get("owner"), issue=arguments.get("issue")))
        elif name == "lockctl_gc":
            payload = cmd_gc(argparse.Namespace())
        else:
            raise ValueError(f"unknown lockctl tool: {name}")
    except LockCtlError as exc:
        payload = {"ok": False, "error": exc.code, "message": exc.message, **exc.payload}
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error": "UNEXPECTED_ERROR", "message": str(exc)}
    return payload


def _call_coordctl(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        if name == "coordctl_session_start":
            payload = coordctl_cmd_session_start(argparse.Namespace(repo_root=str(arguments.get("repo_root", "")), owner=str(arguments.get("owner", "")), issue=arguments.get("issue"), branch=str(arguments.get("branch", "")), base=str(arguments.get("base", "")), worktree_path=arguments.get("worktree_path"), lease_sec=_as_int(arguments.get("lease_sec"), 60)))
        elif name == "coordctl_intent_acquire":
            payload = coordctl_cmd_intent_acquire(argparse.Namespace(repo_root=str(arguments.get("repo_root", "")), path=str(arguments.get("path", "")), owner=str(arguments.get("owner", "")), issue=arguments.get("issue"), base=str(arguments.get("base", "")), region_kind=str(arguments.get("region_kind", "")), region_id=str(arguments.get("region_id", "")), lease_sec=_as_int(arguments.get("lease_sec"), 60), session_id=arguments.get("session_id")))
        elif name == "coordctl_status":
            payload = coordctl_cmd_status(argparse.Namespace(repo_root=str(arguments.get("repo_root", "")), path=arguments.get("path"), owner=arguments.get("owner"), issue=arguments.get("issue"), all=bool(arguments.get("all", False))))
        elif name == "coordctl_heartbeat":
            payload = coordctl_cmd_heartbeat(argparse.Namespace(session_id=str(arguments.get("session_id", "")), lease_sec=_as_int(arguments.get("lease_sec"), 60)))
        elif name == "coordctl_release":
            payload = coordctl_cmd_release(argparse.Namespace(session_id=arguments.get("session_id"), repo_root=arguments.get("repo_root"), issue=arguments.get("issue")))
        elif name == "coordctl_cleanup":
            payload = coordctl_cmd_cleanup(argparse.Namespace(session_id=str(arguments.get("session_id", "")), final_state=str(arguments.get("final_state") or "released"), delete_worktree=bool(arguments.get("delete_worktree", False)), delete_branch=bool(arguments.get("delete_branch", False)), dry_run=bool(arguments.get("dry_run", False)), apply=bool(arguments.get("apply", False))))
        elif name == "coordctl_gc":
            payload = coordctl_cmd_gc(argparse.Namespace(dry_run=bool(arguments.get("dry_run", False)), apply=bool(arguments.get("apply", False))))
        elif name == "coordctl_merge_dry_run":
            payload = coordctl_cmd_merge_dry_run(argparse.Namespace(repo_root=str(arguments.get("repo_root", "")), target=str(arguments.get("target", "")), branch=str(arguments.get("branch", ""))))
        else:
            raise ValueError(f"unknown coordctl tool: {name}")
    except CoordCtlError as exc:
        payload = {"ok": False, "error": exc.code, "message": exc.message, **exc.payload}
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error": "UNEXPECTED_ERROR", "message": str(exc)}
    return payload


def _call_tool(profile: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if profile == "intdata-control":
        if name.startswith("lockctl_"):
            return _call_lockctl(name, arguments)
        if name.startswith("coordctl_"):
            return _call_coordctl(name, arguments)
        if name.startswith("openspec_"):
            return _call_openspec(name, arguments)
        return _call_governance(name, arguments)
    if profile == "intdata-runtime":
        if name in {tool["name"] for tool in VAULT_TOOLS}:
            return _call_vault(name, arguments)
        return _call_runtime(name, arguments)
    if profile == "dba":
        return _call_dba(name, arguments)
    raise ValueError(f"unknown profile: {profile}")


def _json_result(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _json_error(req_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": error}


def _text_content(value: Any) -> dict[str, str]:
    return {"type": "text", "text": json.dumps(value, ensure_ascii=False)}


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


def _delegate_intbrain() -> int:
    if not BRAIN_MCP.exists():
        print(json.dumps({"ok": False, "error": "config_error", "message": f"brain-owned intbrain MCP not found: {BRAIN_MCP}"}), file=sys.stderr)
        return 2
    print("warning: /int/tools intbrain profile is deprecated; delegating to /int/brain/mcp/intbrain", file=sys.stderr)
    os.execv(sys.executable, [sys.executable, str(BRAIN_MCP), "--stdio"])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, choices=sorted(PROFILE_TOOLS))
    args = parser.parse_args()
    if args.profile == "intbrain":
        return _delegate_intbrain()
    while True:
        message = _read_message()
        if message is None:
            return 0
        response = _handle(args.profile, message)
        if response is not None:
            _write_message(response)


if __name__ == "__main__":
    raise SystemExit(main())
