#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "intbrain-mcp"
SERVER_VERSION = "0.1.0"

API_BASE = os.environ.get("INTBRAIN_API_BASE_URL", "https://brain.api.intdata.pro/api/core/v1").rstrip("/")
AGENT_ID = os.environ.get("INTBRAIN_AGENT_ID", "").strip()
AGENT_KEY = os.environ.get("INTBRAIN_AGENT_KEY", "").strip()
TIMEOUT = float(os.environ.get("INTBRAIN_API_TIMEOUT_SEC", "15"))


TOOLS: list[dict[str, Any]] = [
    {
        "name": "intbrain_context_pack",
        "description": "Retrieve context package for an entity/person query.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "entity_id": {"type": "integer"},
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "depth": {"type": "integer"},
            },
            "required": ["owner_id"],
        },
    },
    {
        "name": "intbrain_people_resolve",
        "description": "Resolve people by query.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "q": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["owner_id", "q"],
        },
    },
    {
        "name": "intbrain_people_get",
        "description": "Get person profile by entity id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "entity_id": {"type": "integer"},
            },
            "required": ["owner_id", "entity_id"],
        },
    },
    {
        "name": "intbrain_graph_neighbors",
        "description": "Get graph neighbors for entity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "entity_id": {"type": "integer"},
                "depth": {"type": "integer"},
                "limit": {"type": "integer"},
                "link_type": {"type": "string"},
            },
            "required": ["owner_id", "entity_id"],
        },
    },
    {
        "name": "intbrain_context_store",
        "description": "Store context item (write scope required).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "kind": {"type": "string"},
                "title": {"type": "string"},
                "text_content": {"type": "string"},
                "entity_id": {"type": "integer"},
                "source_path": {"type": "string"},
                "source_hash": {"type": "string"},
                "chunk_kind": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "source": {"type": "string"},
                "priority": {"type": "integer"},
            },
            "required": ["owner_id", "kind", "title", "text_content"],
        },
    },
    {
        "name": "intbrain_graph_link",
        "description": "Create/update typed graph edge (write scope required).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "from_entity_id": {"type": "integer"},
                "to_entity_id": {"type": "integer"},
                "link_type": {"type": "string"},
                "weight": {"type": "number"},
                "confidence": {"type": "number"},
                "source": {"type": "string"},
                "source_path": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["owner_id", "from_entity_id", "to_entity_id", "link_type"],
        },
    },
]


def _write_message(payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    sys.stdout.buffer.write(header)
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def _read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("utf-8", errors="ignore").strip()
        if ":" not in decoded:
            continue
        key, value = decoded.split(":", 1)
        headers[key.strip().lower()] = value.strip()

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


def _http_json(method: str, path: str, *, params: dict[str, Any] | None = None, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    if not AGENT_ID or not AGENT_KEY:
        raise RuntimeError("INTBRAIN_AGENT_ID and INTBRAIN_AGENT_KEY must be set")

    url = f"{API_BASE}/{path.lstrip('/')}"
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        if query:
            url = f"{url}?{query}"

    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url=url, method=method.upper(), data=data)
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Agent-Id", AGENT_ID)
    req.add_header("X-Agent-Key", AGENT_KEY)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            if not raw:
                return resp.status, {}
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore")
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"raw": raw}
        return int(exc.code), body


def _call_tool(name: str, arguments: dict[str, Any]) -> tuple[bool, Any]:
    if name == "intbrain_context_pack":
        code, body = _http_json("POST", "context/pack", payload=arguments)
    elif name == "intbrain_people_resolve":
        code, body = _http_json("GET", "people/resolve", params=arguments)
    elif name == "intbrain_people_get":
        entity_id = arguments.get("entity_id")
        if entity_id is None:
            return False, {"error": "entity_id_required"}
        params = {"owner_id": arguments.get("owner_id")}
        code, body = _http_json("GET", f"people/{entity_id}", params=params)
    elif name == "intbrain_graph_neighbors":
        code, body = _http_json("GET", "graph/neighbors", params=arguments)
    elif name == "intbrain_context_store":
        code, body = _http_json("POST", "context/store", payload=arguments)
    elif name == "intbrain_graph_link":
        code, body = _http_json("POST", "graph/link", payload=arguments)
    else:
        return False, {"error": "unknown_tool", "tool": name}

    ok = 200 <= code < 300
    if ok:
        return True, body
    return False, {"http_status": code, "body": body}


def _handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    req_id = request.get("id")
    method = str(request.get("method") or "")
    params = request.get("params") or {}

    if method == "initialize":
        return _json_result(
            req_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )

    if method == "notifications/initialized":
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
            ok, data = _call_tool(str(name), arguments)
        except Exception as exc:  # noqa: BLE001
            return _json_result(req_id, {"content": [_text_content({"error": str(exc)})], "isError": True})
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

