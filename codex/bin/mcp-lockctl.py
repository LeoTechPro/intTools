#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "lockctl-mcp"
SERVER_VERSION = "0.1.0"
IO_MODE = "framed"

ROOT_DIR = Path(__file__).resolve().parents[2]
LOCKCTL_DIR = ROOT_DIR / "lockctl"
if str(LOCKCTL_DIR) not in sys.path:
    sys.path.insert(0, str(LOCKCTL_DIR))

from lockctl_core import LockCtlError, cmd_acquire, cmd_gc, cmd_release_issue, cmd_release_path, cmd_renew, cmd_status


TOOLS: list[dict[str, Any]] = [
    {
        "name": "lockctl_acquire",
        "description": "Acquire or renew a lease lock for a file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_root": {"type": "string"},
                "path": {"type": "string"},
                "owner": {"type": "string"},
                "issue": {"type": "string"},
                "reason": {"type": "string"},
                "lease_sec": {"type": "integer"},
            },
            "required": ["repo_root", "path", "owner"],
        },
    },
    {
        "name": "lockctl_renew",
        "description": "Renew an active lock by lock id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lock_id": {"type": "string"},
                "lease_sec": {"type": "integer"},
            },
            "required": ["lock_id"],
        },
    },
    {
        "name": "lockctl_release_path",
        "description": "Release one active lock by repo/path for the same owner.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_root": {"type": "string"},
                "path": {"type": "string"},
                "owner": {"type": "string"},
            },
            "required": ["repo_root", "path", "owner"],
        },
    },
    {
        "name": "lockctl_release_issue",
        "description": "Release all active locks for an issue in repo root.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_root": {"type": "string"},
                "issue": {"type": "string"},
            },
            "required": ["repo_root", "issue"],
        },
    },
    {
        "name": "lockctl_status",
        "description": "Read active/expired lock status for repo/path/owner/issue.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_root": {"type": "string"},
                "path": {"type": "string"},
                "owner": {"type": "string"},
                "issue": {"type": "string"},
            },
            "required": ["repo_root"],
        },
    },
    {
        "name": "lockctl_gc",
        "description": "Delete expired locks from runtime storage.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def _write_message(payload: dict[str, Any]) -> None:
    if IO_MODE == "jsonl":
        sys.stdout.write(json.dumps(payload, ensure_ascii=False))
        sys.stdout.write("\n")
        sys.stdout.flush()
        return
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    sys.stdout.buffer.write(header)
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def _read_message() -> dict[str, Any] | None:
    global IO_MODE
    headers: dict[str, str] = {}
    first_line = sys.stdin.buffer.readline()
    if not first_line:
        return None
    first_decoded = first_line.decode("utf-8", errors="ignore").strip()
    if first_decoded.startswith("{"):
        IO_MODE = "jsonl"
        return json.loads(first_decoded)
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

    content_length = int(headers.get("content-length", "0"))
    if content_length <= 0:
        return None
    body = sys.stdin.buffer.read(content_length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def _json_result(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _json_error(req_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def _text_content(value: Any) -> dict[str, Any]:
    return {"type": "text", "text": json.dumps(value, ensure_ascii=False)}


def _to_ns(values: dict[str, Any]) -> argparse.Namespace:
    return argparse.Namespace(**values)


def _lease_sec(arguments: dict[str, Any], default: int) -> int:
    raw = arguments.get("lease_sec", default)
    try:
        return int(raw)
    except Exception:
        return default


def _call_tool(name: str, arguments: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    try:
        if name == "lockctl_acquire":
            payload = cmd_acquire(
                _to_ns(
                    {
                        "repo_root": str(arguments.get("repo_root", "")),
                        "path": str(arguments.get("path", "")),
                        "owner": str(arguments.get("owner", "")),
                        "issue": arguments.get("issue"),
                        "reason": arguments.get("reason"),
                        "lease_sec": _lease_sec(arguments, 60),
                    }
                )
            )
        elif name == "lockctl_renew":
            payload = cmd_renew(
                _to_ns(
                    {
                        "lock_id": str(arguments.get("lock_id", "")),
                        "lease_sec": _lease_sec(arguments, 60),
                    }
                )
            )
        elif name == "lockctl_release_path":
            payload = cmd_release_path(
                _to_ns(
                    {
                        "repo_root": str(arguments.get("repo_root", "")),
                        "path": str(arguments.get("path", "")),
                        "owner": str(arguments.get("owner", "")),
                    }
                )
            )
        elif name == "lockctl_release_issue":
            payload = cmd_release_issue(
                _to_ns(
                    {
                        "repo_root": str(arguments.get("repo_root", "")),
                        "issue": arguments.get("issue"),
                    }
                )
            )
        elif name == "lockctl_status":
            payload = cmd_status(
                _to_ns(
                    {
                        "repo_root": str(arguments.get("repo_root", "")),
                        "path": arguments.get("path"),
                        "owner": arguments.get("owner"),
                        "issue": arguments.get("issue"),
                    }
                )
            )
        elif name == "lockctl_gc":
            payload = cmd_gc(_to_ns({}))
        else:
            return False, {"ok": False, "error": "unknown_tool", "message": f"Unknown tool: {name}"}
    except LockCtlError as exc:
        payload = {"ok": False, "error": exc.code, "message": exc.message, **exc.payload}
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error": "UNEXPECTED_ERROR", "message": str(exc)}
    return bool(payload.get("ok")), payload


def _handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    req_id = request.get("id")
    method = str(request.get("method") or "")
    params = request.get("params") or {}

    if method == "initialize":
        requested_protocol = str((params or {}).get("protocolVersion") or "").strip()
        return _json_result(
            req_id,
            {
                "protocolVersion": requested_protocol or PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )

    if method.startswith("notifications/"):
        return None

    if method == "ping":
        return _json_result(req_id, {})

    if method == "tools/list":
        return _json_result(req_id, {"tools": TOOLS})

    if method == "tools/call":
        name = (params or {}).get("name")
        arguments = (params or {}).get("arguments") or {}
        if not name:
            return _json_error(req_id, -32602, "tools/call requires name")
        ok, data = _call_tool(str(name), arguments)
        return _json_result(req_id, {"content": [_text_content(data)], "isError": not ok})

    return _json_error(req_id, -32601, f"Method not found: {method}")


def main() -> int:
    while True:
        message = _read_message()
        if message is None:
            return 0
        response = _handle_request(message)
        if response is not None:
            _write_message(response)


if __name__ == "__main__":
    raise SystemExit(main())
