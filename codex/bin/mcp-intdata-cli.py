#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "0.1.0"
IO_MODE = "framed"

ROOT_DIR = Path(__file__).resolve().parents[2]
INT_ROOT = ROOT_DIR.parent
ISSUE_RE = re.compile(r"^INT-\d+$")


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}


COMMON_RUN_PROPS = {
    "cwd": {"type": "string", "description": "Working directory under D:/int. Defaults to D:/int/tools."},
    "timeout_sec": {"type": "integer", "description": "Command timeout in seconds."},
}


def _args_prop(description: str = "Structured command arguments.") -> dict[str, Any]:
    return {"type": "array", "items": {"type": "string"}, "description": description}


def _mutation_props() -> dict[str, Any]:
    return {
        "confirm_mutation": {"type": "boolean"},
        "issue_context": {"type": "string", "description": "Current Multica issue identifier, e.g. INT-202."},
    }


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"name": name, "description": description, "inputSchema": _schema(properties, required)}


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
        "openspec_change",
        "Run an allowlisted `openspec change` subcommand. Mutating subcommands require confirmation.",
        {**COMMON_RUN_PROPS, **_mutation_props(), "subcommand": {"type": "string"}, "args": _args_prop()},
        ["subcommand"],
    ),
    _tool(
        "openspec_spec",
        "Run an allowlisted `openspec spec` subcommand. Mutating subcommands require confirmation.",
        {**COMMON_RUN_PROPS, **_mutation_props(), "subcommand": {"type": "string"}, "args": _args_prop()},
        ["subcommand"],
    ),
    _tool(
        "openspec_new",
        "Run `openspec new`. Mutating; requires confirmation and issue context.",
        {**COMMON_RUN_PROPS, **_mutation_props(), "args": _args_prop()},
        ["confirm_mutation", "issue_context"],
    ),
    _tool(
        "openspec_exec",
        "Run a structured OpenSpec CLI command. Mutating commands require confirmation.",
        {**COMMON_RUN_PROPS, **_mutation_props(), "args": _args_prop("Arguments after the openspec executable.")},
        ["args"],
    ),
]

MULTICA_TOOLS = [
    _tool("multica_issue", "Run structured `multica issue` commands.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "args": _args_prop()}, ["command"]),
    _tool("multica_project", "Run structured `multica project` commands.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "args": _args_prop()}, ["command"]),
    _tool("multica_agent", "Run structured `multica agent` commands.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "args": _args_prop()}, ["command"]),
    _tool("multica_workspace", "Run structured `multica workspace` commands.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "args": _args_prop()}, ["command"]),
    _tool("multica_repo", "Run structured `multica repo` commands.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "args": _args_prop()}, ["command"]),
    _tool("multica_skill", "Run structured `multica skill` commands.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "args": _args_prop()}, ["command"]),
    _tool("multica_runtime", "Run structured `multica runtime` commands.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "args": _args_prop()}, ["command"]),
    _tool("multica_daemon", "Run structured `multica daemon` commands. Control commands require confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "args": _args_prop()}, ["command"]),
    _tool("multica_attachment", "Run structured `multica attachment` commands.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "args": _args_prop()}, ["command"]),
    _tool("multica_auth", "Run structured `multica auth/login/setup` commands. Mutating auth setup requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "args": _args_prop()}, ["command"]),
    _tool("multica_config", "Run structured `multica config` commands.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "args": _args_prop()}, ["command"]),
    _tool("multica_exec", "Run a structured Multica CLI command. Mutating commands require confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "args": _args_prop("Arguments after the multica executable.")}, ["args"]),
]

ROUTING_TOOLS = [
    _tool("intdata_routing_validate", "Validate high-risk agent tool routing registry.", {**COMMON_RUN_PROPS, "strict": {"type": "boolean"}, "json": {"type": "boolean"}}),
    _tool("intdata_routing_resolve", "Resolve a logical high-risk tooling intent.", {**COMMON_RUN_PROPS, "intent": {"type": "string"}, "platform": {"type": "string"}, "json": {"type": "boolean"}}, ["intent"]),
]

DELIVERY_TOOLS = [
    _tool("intdata_sync_gate", "Run int git sync gate. Finish/push modes require confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "stage": {"type": "string", "enum": ["start", "finish"]}, "push": {"type": "boolean"}, "all_repos": {"type": "boolean"}, "root_path": {"type": "string"}}, ["stage"]),
    _tool("intdata_publish", "Run a canonical publish wrapper. Mutating; requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "target": {"type": "string"}, "no_push": {"type": "boolean"}, "no_deploy": {"type": "boolean"}, "args": _args_prop()}, ["confirm_mutation", "issue_context", "target"]),
]

GENERIC_TOOL = [
    _tool("intdata_cli", "Run a profile allowlisted CLI command with structured arguments.", {**COMMON_RUN_PROPS, **_mutation_props(), "command": {"type": "string"}, "args": _args_prop()}, ["command"]),
]

HOST_TOOLS = [
    _tool("intdata_host_verify", "Run Codex host verification.", {**COMMON_RUN_PROPS, "args": _args_prop()}),
    _tool("intdata_host_preflight", "Run Codex preflight.", {**COMMON_RUN_PROPS, "json": {"type": "boolean"}}),
    _tool("intdata_host_bootstrap", "Run Codex host bootstrap. Mutating; requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "args": _args_prop()}, ["confirm_mutation", "issue_context"]),
    _tool("intdata_recovery_bundle", "Create a Codex recovery bundle. Mutating; requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "args": _args_prop()}, ["confirm_mutation", "issue_context"]),
]

SSH_TOOLS = [
    _tool("intdata_ssh_resolve", "Resolve IntData SSH host transport.", {**COMMON_RUN_PROPS, "host": {"type": "string"}, "mode": {"type": "string"}, "json": {"type": "boolean"}}, ["host"]),
    _tool("intdata_ssh_host", "Print SSH host config/diagnostics, not an interactive shell.", {**COMMON_RUN_PROPS, "host": {"type": "string"}, "args": _args_prop()}, ["host"]),
]

VAULT_TOOLS = [
    _tool("intdata_vault_sanitize", "Run vault sanitizer. Defaults to dry-run; non-dry-run requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "dry_run": {"type": "boolean"}, "args": _args_prop()}),
    _tool("intdata_runtime_vault_gc", "Run runtime vault GC. Defaults to dry-run; non-dry-run requires confirmation.", {**COMMON_RUN_PROPS, **_mutation_props(), "dry_run": {"type": "boolean"}, "args": _args_prop()}),
]


PROFILE_TOOLS: dict[str, list[dict[str, Any]]] = {
    "openspec": OPEN_SPEC_TOOLS,
    "multica": MULTICA_TOOLS,
    "intdata-routing": ROUTING_TOOLS,
    "intdata-delivery": DELIVERY_TOOLS,
    "intdb": GENERIC_TOOL,
    "gatesctl": GENERIC_TOOL,
    "intdata-browser": GENERIC_TOOL,
    "intdata-host": HOST_TOOLS,
    "intdata-ssh": SSH_TOOLS,
    "intdata-vault": VAULT_TOOLS,
    "punktb-connectors": GENERIC_TOOL,
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
    "gatesctl": {
        "gatesctl": ["python", str(ROOT_DIR / "gatesctl" / "gatesctl.py")],
    },
    "intdata-browser": {
        "firefox-default": ["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "mcp-firefox-default.cmd")],
        "firefox-assess-client": ["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "mcp-firefox-assess-client.cmd")],
        "firefox-assess-specialist-v1": ["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "mcp-firefox-assess-specialist-v1.cmd")],
        "firefox-assess-specialist-v2": ["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "mcp-firefox-assess-specialist-v2.cmd")],
        "firefox-assess-admin": ["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "mcp-firefox-assess-admin.cmd")],
        "firefox-assess-specialist-restricted": ["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "mcp-firefox-assess-specialist-restricted.cmd")],
    },
    "punktb-connectors": {
        "bizon365": ["python", str(ROOT_DIR / "codex" / "bin" / "mcp-bizon365.py")],
        "salebot": ["node", str(ROOT_DIR / "codex" / "bin" / "mcp-salebot.mjs")],
        "timeweb-readonly": ["node", str(ROOT_DIR / "codex" / "bin" / "mcp-timeweb-readonly.mjs")],
        "timeweb": ["bash", str(ROOT_DIR / "codex" / "bin" / "mcp-timeweb.sh")],
        "bitrix24": ["bash", str(ROOT_DIR / "codex" / "bin" / "mcp-bitrix24.sh")],
    },
}


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
    elif name == "openspec_change":
        args = ["change", str(arguments["subcommand"]), *_safe_args(arguments.get("args"))]
        if _is_openspec_mutating(args):
            _require_mutation(arguments)
    elif name == "openspec_spec":
        args = ["spec", str(arguments["subcommand"]), *_safe_args(arguments.get("args"))]
        if _is_openspec_mutating(args):
            _require_mutation(arguments)
    elif name == "openspec_new":
        _require_mutation(arguments)
        args = ["new", *_safe_args(arguments.get("args"))]
    elif name == "openspec_exec":
        args = _safe_args(arguments.get("args"))
        if _is_openspec_mutating(args):
            _require_mutation(arguments)
    else:
        raise ValueError(f"unknown openspec tool: {name}")
    return _run([*_openspec_base(), *args], cwd=cwd, timeout_sec=timeout)


def _is_multica_mutating(domain: str, command: str) -> bool:
    return command not in READ_ONLY_MULTICA.get(domain, set())


def _call_multica(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    cwd = _cwd(arguments.get("cwd"))
    timeout = arguments.get("timeout_sec")
    if name == "multica_exec":
        args = _safe_args(arguments.get("args"))
        if args and _is_multica_mutating(args[0], args[1] if len(args) > 1 else ""):
            _require_mutation(arguments)
        return _run(["multica", *args], cwd=cwd, timeout_sec=timeout)
    domain = name.removeprefix("multica_")
    command = str(arguments["command"])
    if _is_multica_mutating(domain, command):
        _require_mutation(arguments)
    if domain == "auth" and command in {"login", "setup"}:
        _require_mutation(arguments)
        return _run(["multica", command, *_safe_args(arguments.get("args"))], cwd=cwd, timeout_sec=timeout)
    return _run(["multica", domain, command, *_safe_args(arguments.get("args"))], cwd=cwd, timeout_sec=timeout)


def _call_routing(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    cwd = _cwd(arguments.get("cwd"))
    argv = ["python", str(ROOT_DIR / "codex" / "bin" / "agent_tool_routing.py")]
    if name == "intdata_routing_validate":
        argv.append("validate")
        if arguments.get("strict"):
            argv.append("--strict")
        if arguments.get("json"):
            argv.append("--json")
    elif name == "intdata_routing_resolve":
        argv.extend(["resolve", "--intent", str(arguments["intent"])])
        if arguments.get("platform"):
            argv.extend(["--platform", str(arguments["platform"])])
        if arguments.get("json"):
            argv.append("--json")
    else:
        raise ValueError(f"unknown routing tool: {name}")
    return _run(argv, cwd=cwd, timeout_sec=arguments.get("timeout_sec"))


def _call_delivery(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    cwd = _cwd(arguments.get("cwd"))
    if name == "intdata_sync_gate":
        argv = ["python", str(ROOT_DIR / "scripts" / "codex" / "int_git_sync_gate.py"), "--stage", str(arguments["stage"])]
        if arguments.get("push"):
            _require_mutation(arguments)
            argv.append("--push")
        if arguments.get("stage") == "finish":
            _require_mutation(arguments)
        if arguments.get("all_repos"):
            argv.append("--all-repos")
        if arguments.get("root_path"):
            argv.extend(["--root-path", str(arguments["root_path"])])
        return _run(argv, cwd=cwd, timeout_sec=arguments.get("timeout_sec"))
    if name == "intdata_publish":
        _require_mutation(arguments)
        target = str(arguments["target"])
        script = ROOT_DIR / "delivery" / "bin" / f"publish_{target}.py"
        if target == "bundle-dint":
            script = ROOT_DIR / "delivery" / "bin" / "publish_bundle_dint.py"
        if not script.exists():
            raise ValueError(f"unknown publish target: {target}")
        argv = ["python", str(script)]
        if arguments.get("no_push"):
            argv.append("--no-push")
        if arguments.get("no_deploy"):
            argv.append("--no-deploy")
        argv.extend(_safe_args(arguments.get("args")))
        return _run(argv, cwd=cwd, timeout_sec=arguments.get("timeout_sec") or 300)
    raise ValueError(f"unknown delivery tool: {name}")


def _call_generic(profile: str, arguments: dict[str, Any]) -> dict[str, Any]:
    command = str(arguments["command"])
    commands = PROFILE_COMMANDS.get(profile, {})
    if command not in commands:
        raise ValueError(f"unknown {profile} command: {command}")
    args = _safe_args(arguments.get("args"))
    if profile == "gatesctl" and (not args or args[0] not in {"status", "show-receipt", "audit-range", "help", "--help", "-h"}):
        _require_mutation(arguments)
    if profile in {"intdata-browser", "punktb-connectors"}:
        _require_mutation(arguments)
    if profile == "intdb":
        safe_intdb = (
            not args
            or args[:1] in (["doctor"], ["--help"], ["-h"], ["help"])
            or args[:2] == ["migrate", "status"]
        )
        if not safe_intdb:
            _require_mutation(arguments)
    return _run([*commands[command], *args], cwd=_cwd(arguments.get("cwd")), timeout_sec=arguments.get("timeout_sec"))


def _call_host(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    cwd = _cwd(arguments.get("cwd"))
    if name == "intdata_host_verify":
        return _run(["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "codex-host-verify.cmd"), *_safe_args(arguments.get("args"))], cwd=cwd, timeout_sec=arguments.get("timeout_sec"))
    if name == "intdata_host_preflight":
        argv = ["pwsh", "-File", str(ROOT_DIR / "scripts" / "codex" / "codex_preflight.ps1")]
        if arguments.get("json"):
            argv.append("-Json")
        return _run(argv, cwd=cwd, timeout_sec=arguments.get("timeout_sec"))
    if name == "intdata_host_bootstrap":
        _require_mutation(arguments)
        return _run(["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "codex-host-bootstrap.cmd"), *_safe_args(arguments.get("args"))], cwd=cwd, timeout_sec=arguments.get("timeout_sec") or 300)
    if name == "intdata_recovery_bundle":
        _require_mutation(arguments)
        return _run(["cmd.exe", "/d", "/s", "/c", str(ROOT_DIR / "codex" / "bin" / "codex-recovery-bundle.cmd"), *_safe_args(arguments.get("args"))], cwd=cwd, timeout_sec=arguments.get("timeout_sec") or 300)
    raise ValueError(f"unknown host tool: {name}")


def _call_ssh(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    cwd = _cwd(arguments.get("cwd"))
    if name == "intdata_ssh_resolve":
        argv = [
            "python",
            str(ROOT_DIR / "codex" / "bin" / "int_ssh_resolve.py"),
            "--requested-host",
            str(arguments["host"]),
            "--capability",
            "intdata_ssh_resolve",
            "--binding-origin",
            "codex/bin/mcp-intdata-cli.py",
        ]
        if arguments.get("mode"):
            argv.extend(["--mode", str(arguments["mode"])])
        if arguments.get("json"):
            argv.append("--json")
        return _run(argv, cwd=cwd, timeout_sec=arguments.get("timeout_sec"))
    if name == "intdata_ssh_host":
        argv = ["pwsh", "-File", str(ROOT_DIR / "codex" / "bin" / "int_ssh_host.ps1"), "-Logical", str(arguments["host"])]
        if arguments.get("args"):
            argv.extend(_safe_args(arguments.get("args")))
        return _run(argv, cwd=cwd, timeout_sec=arguments.get("timeout_sec"))
    raise ValueError(f"unknown ssh tool: {name}")


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


def _call_tool(profile: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if profile == "openspec":
        return _call_openspec(name, arguments)
    if profile == "multica":
        return _call_multica(name, arguments)
    if profile == "intdata-routing":
        return _call_routing(name, arguments)
    if profile == "intdata-delivery":
        return _call_delivery(name, arguments)
    if profile in {"intdb", "gatesctl", "intdata-browser", "punktb-connectors"}:
        return _call_generic(profile, arguments)
    if profile == "intdata-host":
        return _call_host(name, arguments)
    if profile == "intdata-ssh":
        return _call_ssh(name, arguments)
    if profile == "intdata-vault":
        return _call_vault(name, arguments)
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
