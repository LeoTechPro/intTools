from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "0.1.0"


TOOLS = [
    {
        "name": "agent_plane_tools",
        "description": "List tools exposed by the neutral intData Agent Tool Plane.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "agent_plane_call",
        "description": "Call a canonical tool through the neutral intData Agent Tool Plane.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "facade": {"type": "string", "enum": ["codex_app", "openclaw", "agno"]},
                "principal": {"type": "object"},
                "tool": {"type": "string"},
                "args": {"type": "object"},
                "context": {"type": "object"},
                "dry_run": {"type": "boolean"},
                "approval_ref": {"type": "string"},
            },
            "required": ["tool", "principal"],
        },
    },
    {
        "name": "agent_plane_audit_recent",
        "description": "Read recent neutral Agent Tool Plane audit entries.",
        "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}}},
    },
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.getenv("AGENT_PLANE_URL", "http://127.0.0.1:9192"))
    args = parser.parse_args()
    while True:
        request = _read_message()
        if request is None:
            return 0
        response = _handle(args.url.rstrip("/"), request)
        if response is not None:
            _write_message(response)


def _handle(base_url: str, request: dict[str, Any]) -> dict[str, Any] | None:
    req_id = request.get("id")
    method = str(request.get("method") or "")
    params = request.get("params") or {}
    if method == "initialize":
        requested = str((params or {}).get("protocolVersion") or "").strip()
        return _json_result(req_id, {"protocolVersion": requested or PROTOCOL_VERSION, "capabilities": {"tools": {}}, "serverInfo": {"name": "agent-plane-mcp", "version": SERVER_VERSION}})
    if method.startswith("notifications/"):
        return None
    if method == "tools/list":
        return _json_result(req_id, {"tools": TOOLS})
    if method == "tools/call":
        name = str((params or {}).get("name") or "")
        arguments = (params or {}).get("arguments") or {}
        try:
            payload = _call_tool(base_url, name, dict(arguments))
            return _json_result(req_id, {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}], "isError": not bool(payload.get("ok"))})
        except Exception as exc:  # noqa: BLE001
            return _json_result(req_id, {"content": [{"type": "text", "text": json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)}], "isError": True})
    return _json_error(req_id, -32601, f"Method not found: {method}")


def _call_tool(base_url: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "agent_plane_tools":
        return _http_json("GET", f"{base_url}/v1/tools")
    if name == "agent_plane_audit_recent":
        limit = int(arguments.get("limit") or 50)
        return _http_json("GET", f"{base_url}/v1/audit/tool-calls?limit={limit}")
    if name == "agent_plane_call":
        payload = {
            "facade": arguments.get("facade") or "codex_app",
            "principal": arguments.get("principal") or {"id": "codex_app"},
            "tool": arguments["tool"],
            "args": arguments.get("args") or {},
            "context": arguments.get("context") or {},
            "dry_run": bool(arguments.get("dry_run", False)),
        }
        if arguments.get("approval_ref"):
            payload["approval_ref"] = str(arguments["approval_ref"])
        return _http_json("POST", f"{base_url}/v1/tools/call", payload=payload)
    return {"ok": False, "error": f"unknown tool: {name}"}


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return json.loads(body)


def _read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if line == b"":
            return None
        if line in (b"\r\n", b"\n"):
            break
        key, value = line.decode("ascii").split(":", 1)
        headers[key.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def _write_message(message: dict[str, Any]) -> None:
    body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def _json_result(req_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _json_error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


if __name__ == "__main__":
    raise SystemExit(main())
