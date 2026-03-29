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
IO_MODE = "framed"

API_BASE = os.environ.get("INTBRAIN_API_BASE_URL", "https://brain.api.intdata.pro/api/core/v1").rstrip("/")
AGENT_ID = os.environ.get("INTBRAIN_AGENT_ID", "").strip()
AGENT_KEY = os.environ.get("INTBRAIN_AGENT_KEY", "").strip()
CORE_ADMIN_TOKEN = os.environ.get("INTBRAIN_CORE_ADMIN_TOKEN", "").strip()
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
    {
        "name": "intbrain_people_policy_tg_get",
        "description": "Get effective Telegram policy for person by tg_user_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "tg_user_id": {"type": "integer"},
                "chat_id": {"type": "string"},
            },
            "required": ["owner_id", "tg_user_id"],
        },
    },
    {
        "name": "intbrain_group_policy_get",
        "description": "Get group policy by chat_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "chat_id": {"type": "string"},
            },
            "required": ["owner_id", "chat_id"],
        },
    },
    {
        "name": "intbrain_group_policy_upsert",
        "description": "Create/update group policy (write scope required).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "chat_id": {"type": "string"},
                "name": {"type": "string"},
                "respond_mode": {"type": "string"},
                "access_mode": {"type": "string"},
                "tools_policy": {"type": "string"},
                "project_scope": {"type": "string"},
                "notes": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["owner_id", "chat_id", "respond_mode", "access_mode", "tools_policy"],
        },
    },
    {
        "name": "intbrain_jobs_list",
        "description": "List jobs with optional filters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "enabled": {"type": "boolean"},
                "kind": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["owner_id"],
        },
    },
    {
        "name": "intbrain_jobs_get",
        "description": "Get job details by job_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "job_id": {"type": "string"},
            },
            "required": ["owner_id", "job_id"],
        },
    },
    {
        "name": "intbrain_job_policy_upsert",
        "description": "Create/update job policy override (write scope required).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "job_id": {"type": "string"},
                "policy_mode": {"type": "string"},
                "notes": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["owner_id", "job_id", "policy_mode"],
        },
    },
    {
        "name": "intbrain_jobs_sync_runtime",
        "description": "Sync runtime jobs into intbrain (import scope required).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "source_root": {"type": "string"},
                "runtime_url": {"type": "string"},
            },
            "required": ["owner_id"],
        },
    },
    {
        "name": "intbrain_policy_events_list",
        "description": "List append-only policy events/provenance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "since": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["owner_id"],
        },
    },
    {
        "name": "intbrain_pm_dashboard",
        "description": "Get PM dashboard with 5-9 constraint evaluation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "date": {"type": "string"},
                "timezone": {"type": "string"},
            },
            "required": ["owner_id"],
        },
    },
    {
        "name": "intbrain_pm_tasks",
        "description": "List PM tasks by view (today, week, backlog).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "view": {"type": "string", "enum": ["today", "week", "backlog"]},
                "date": {"type": "string"},
                "timezone": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["owner_id"],
        },
    },
    {
        "name": "intbrain_pm_task_create",
        "description": "Create PM task with PARA/OKR links and constraints.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "title": {"type": "string"},
                "due_at": {"type": "string"},
                "priority": {"type": "integer"},
                "energy_cost": {"type": "integer"},
                "project_entity_id": {"type": "integer"},
                "area_entity_id": {"type": "integer"},
                "goal_entity_id": {"type": "integer"},
                "okr_entity_id": {"type": "integer"},
                "key_result_entity_id": {"type": "integer"},
                "source_path": {"type": "string"},
                "source_hash": {"type": "string"},
                "active_pin": {"type": "boolean"},
                "timezone": {"type": "string"},
            },
            "required": ["owner_id", "title"],
        },
    },
    {
        "name": "intbrain_pm_task_patch",
        "description": "Patch PM task fields and status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "owner_id": {"type": "integer"},
                "title": {"type": "string"},
                "status": {"type": "string", "enum": ["open", "done", "archived"]},
                "due_at": {"type": "string"},
                "priority": {"type": "integer"},
                "energy_cost": {"type": "integer"},
                "project_entity_id": {"type": "integer"},
                "area_entity_id": {"type": "integer"},
                "goal_entity_id": {"type": "integer"},
                "okr_entity_id": {"type": "integer"},
                "key_result_entity_id": {"type": "integer"},
                "active_pin": {"type": "boolean"},
                "archive": {"type": "boolean"},
                "timezone": {"type": "string"},
            },
            "required": ["task_id", "owner_id"],
        },
    },
    {
        "name": "intbrain_pm_para",
        "description": "Get PARA map (projects/areas/resources/archive) for owner.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
            },
            "required": ["owner_id"],
        },
    },
    {
        "name": "intbrain_pm_health",
        "description": "Get PM health metrics and constraint summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "date": {"type": "string"},
                "timezone": {"type": "string"},
            },
            "required": ["owner_id"],
        },
    },
    {
        "name": "intbrain_pm_constraints_validate",
        "description": "Validate PM 5-9 constraints for owner/date/timezone.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "date": {"type": "string"},
                "timezone": {"type": "string"},
            },
            "required": ["owner_id"],
        },
    },
    {
        "name": "intbrain_import_vault_pm",
        "description": "Import PM/PARA data from 2brain vault (admin token required).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner_id": {"type": "integer"},
                "source_root": {"type": "string"},
                "timezone": {"type": "string"},
            },
            "required": ["owner_id", "source_root"],
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


def _http_json(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    use_agent_auth: bool = True,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, Any]:
    if use_agent_auth and (not AGENT_ID or not AGENT_KEY):
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
    if use_agent_auth:
        req.add_header("X-Agent-Id", AGENT_ID)
        req.add_header("X-Agent-Key", AGENT_KEY)
    for header_name, header_value in (extra_headers or {}).items():
        req.add_header(header_name, header_value)
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
    elif name == "intbrain_people_policy_tg_get":
        code, body = _http_json("GET", "people/policy/telegram", params=arguments)
    elif name == "intbrain_group_policy_get":
        chat_id = arguments.get("chat_id")
        if chat_id is None:
            return False, {"error": "chat_id_required"}
        params = {"owner_id": arguments.get("owner_id")}
        code, body = _http_json("GET", f"groups/{chat_id}/policy", params=params)
    elif name == "intbrain_group_policy_upsert":
        chat_id = arguments.get("chat_id")
        if chat_id is None:
            return False, {"error": "chat_id_required"}
        payload = dict(arguments)
        payload.pop("chat_id", None)
        code, body = _http_json("POST", f"groups/{chat_id}/policy", payload=payload)
    elif name == "intbrain_jobs_list":
        code, body = _http_json("GET", "jobs", params=arguments)
    elif name == "intbrain_jobs_get":
        job_id = arguments.get("job_id")
        if not job_id:
            return False, {"error": "job_id_required"}
        params = {"owner_id": arguments.get("owner_id")}
        code, body = _http_json("GET", f"jobs/{job_id}", params=params)
    elif name == "intbrain_job_policy_upsert":
        job_id = arguments.get("job_id")
        if not job_id:
            return False, {"error": "job_id_required"}
        payload = dict(arguments)
        payload.pop("job_id", None)
        code, body = _http_json("POST", f"jobs/{job_id}/policy", payload=payload)
    elif name == "intbrain_jobs_sync_runtime":
        code, body = _http_json("POST", "jobs/sync/runtime", payload=arguments)
    elif name == "intbrain_policy_events_list":
        code, body = _http_json("GET", "policies/events", params=arguments)
    elif name == "intbrain_pm_dashboard":
        code, body = _http_json("GET", "pm/dashboard", params=arguments)
    elif name == "intbrain_pm_tasks":
        code, body = _http_json("GET", "pm/tasks", params=arguments)
    elif name == "intbrain_pm_task_create":
        code, body = _http_json("POST", "pm/task", payload=arguments)
    elif name == "intbrain_pm_task_patch":
        task_id = arguments.get("task_id")
        if task_id is None:
            return False, {"error": "task_id_required"}
        payload = dict(arguments)
        payload.pop("task_id", None)
        code, body = _http_json("PATCH", f"pm/task/{task_id}", payload=payload)
    elif name == "intbrain_pm_para":
        owner_id = arguments.get("owner_id")
        if owner_id is None:
            return False, {"error": "owner_id_required"}
        code, body = _http_json("GET", f"pm/para/{owner_id}")
    elif name == "intbrain_pm_health":
        code, body = _http_json("GET", "pm/health", params=arguments)
    elif name == "intbrain_pm_constraints_validate":
        code, body = _http_json("POST", "pm/constraints/validate", payload=arguments)
    elif name == "intbrain_import_vault_pm":
        if not CORE_ADMIN_TOKEN:
            return False, {
                "error": "config_error",
                "message": "INTBRAIN_CORE_ADMIN_TOKEN is required for intbrain_import_vault_pm",
            }
        code, body = _http_json(
            "POST",
            "import/vault/pm",
            payload=arguments,
            use_agent_auth=False,
            extra_headers={"X-Core-Admin-Token": CORE_ADMIN_TOKEN},
        )
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
