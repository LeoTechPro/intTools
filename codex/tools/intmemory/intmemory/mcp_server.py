from __future__ import annotations

from dataclasses import asdict
import json
import sys
from typing import Any

from .config import IntMemoryConfig
from .service import IntMemoryService


PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "intmemory-mcp"
SERVER_VERSION = "0.1.0"
IO_MODE = "framed"

TOOLS: list[dict[str, Any]] = [
    {
        "name": "intmemory_sync_now",
        "description": "Sync Codex session memory into IntBrain.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "incremental": {"type": "boolean"},
                "since": {"type": "string"},
                "file": {"type": "string"},
                "dry_run": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "intmemory_search",
        "description": "Search previously stored Codex memory items.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "days": {"type": "integer"},
                "repo": {"type": "string"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "intmemory_recent_work",
        "description": "Summarize what Codex worked on recently from local sessions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer"},
                "limit": {"type": "integer"},
                "repo": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "intmemory_session_brief",
        "description": "Build a concise brief for one Codex session by session_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
            },
            "required": ["session_id"],
            "additionalProperties": False,
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


def _json_error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _text_content(value: Any) -> dict[str, Any]:
    return {"type": "text", "text": json.dumps(value, ensure_ascii=False)}


def _call_tool(service: IntMemoryService, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "intmemory_sync_now":
        return service.sync(
            incremental=bool(arguments.get("incremental", True)),
            since=arguments.get("since"),
            file_path=arguments.get("file"),
            dry_run=bool(arguments.get("dry_run", False)),
            owner_id=arguments.get("owner_id"),
        )
    if name == "intmemory_search":
        return service.search(
            query=str(arguments.get("query") or ""),
            limit=int(arguments.get("limit") or 10),
            days=int(arguments["days"]) if arguments.get("days") is not None else None,
            repo=arguments.get("repo"),
            owner_id=arguments.get("owner_id"),
        )
    if name == "intmemory_recent_work":
        return service.recent_work(
            days=int(arguments.get("days") or 7),
            limit=int(arguments.get("limit") or 10),
            repo=arguments.get("repo"),
        )
    if name == "intmemory_session_brief":
        brief = service.session_brief(session_id=str(arguments.get("session_id") or ""))
        return {"found": brief is not None, "brief": asdict(brief) if brief else None}
    raise RuntimeError(f"unknown_tool:{name}")


def _handle_request(service: IntMemoryService, request: dict[str, Any]) -> dict[str, Any] | None:
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
        try:
            result = _call_tool(service, str(name), dict(arguments))
            return _json_result(req_id, {"content": [_text_content(result)], "isError": False})
        except Exception as exc:  # noqa: BLE001
            return _json_result(req_id, {"content": [_text_content({"error": str(exc)})], "isError": True})
    return _json_error(req_id, -32601, f"Method not found: {method}")


def main() -> int:
    service = IntMemoryService(IntMemoryConfig.from_env())
    while True:
        message = _read_message()
        if message is None:
            return 0
        response = _handle_request(service, message)
        if response is not None:
            _write_message(response)


if __name__ == "__main__":
    raise SystemExit(main())
