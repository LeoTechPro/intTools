from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .adapter import IntToolsAdapter, ToolCallError


PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "0.1.0"
TOOL_NAMES = ("search", "fetch", "routing_validate", "lockctl_status")


@dataclass(frozen=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 9193
    bearer_token: str | None = None
    access_log: bool = False

    @classmethod
    def from_env(cls) -> "ServerConfig":
        token = os.getenv("INT_TOOLS_MCP_BEARER_TOKEN", "").strip() or None
        return cls(
            host=os.getenv("INT_TOOLS_MCP_HOST", "127.0.0.1"),
            port=int(os.getenv("INT_TOOLS_MCP_PORT", "9193")),
            bearer_token=token,
            access_log=os.getenv("INT_TOOLS_MCP_ACCESS_LOG", "").lower() in {"1", "true", "yes"},
        )


class IntToolsMcpApp:
    def __init__(self, adapter: IntToolsAdapter | None = None, config: ServerConfig | None = None) -> None:
        self.adapter = adapter or IntToolsAdapter.from_env()
        self.config = config or ServerConfig.from_env()

    def tools(self) -> list[dict[str, Any]]:
        return [TOOL_DESCRIPTORS[name] for name in TOOL_NAMES]

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "service": "int-tools-chatgpt-mcp",
            "version": SERVER_VERSION,
            "auth_required": bool(self.config.bearer_token),
            "tools": list(TOOL_NAMES),
        }

    def handle_rpc(self, request: dict[str, Any], *, actor: str | None = None) -> dict[str, Any] | None:
        req_id = request.get("id")
        method = str(request.get("method") or "")
        params = request.get("params") or {}
        if method == "initialize":
            requested = str(params.get("protocolVersion") or "").strip()
            return _json_result(
                req_id,
                {
                    "protocolVersion": requested or PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "int-tools-chatgpt-mcp", "version": SERVER_VERSION},
                },
            )
        if method.startswith("notifications/"):
            return None
        if method == "ping":
            return _json_result(req_id, {})
        if method == "tools/list":
            return _json_result(req_id, {"tools": self.tools()})
        if method == "tools/call":
            return _json_result(req_id, self._call_tool(params, actor=actor))
        return _json_error(req_id, -32601, f"Method not found: {method}")

    def _call_tool(self, params: dict[str, Any], *, actor: str | None = None) -> dict[str, Any]:
        name = str(params.get("name") or "")
        arguments = params.get("arguments") or {}
        started = time.perf_counter()
        decision = "allowlisted" if name in TOOL_NAMES else "rejected"
        try:
            if name not in TOOL_NAMES:
                raise ToolCallError("unknown_tool", f"unknown tool: {name}")
            if not isinstance(arguments, dict):
                raise ToolCallError("invalid_arguments", "arguments must be an object")
            result = self.adapter.call_tool(name, arguments)
            self._log_tool_call(actor, name, started, decision, result_class="error" if result.get("isError") else "ok")
            return result
        except ToolCallError as exc:
            self._log_tool_call(actor, name, started, decision, result_class=exc.code)
            return {
                "structuredContent": {"ok": False, "error": {"code": exc.code, "message": exc.message, "details": exc.details}},
                "content": [{"type": "text", "text": exc.message}],
                "isError": True,
            }
        except Exception as exc:  # noqa: BLE001
            self._log_tool_call(actor, name, started, decision, result_class="unexpected_error")
            return {
                "structuredContent": {"ok": False, "error": {"code": "unexpected_error", "message": str(exc)}},
                "content": [{"type": "text", "text": "Unexpected internal error."}],
                "isError": True,
            }

    def _log_tool_call(self, actor: str | None, name: str, started: float, decision: str, *, result_class: str) -> None:
        if not self.config.access_log:
            return
        event = {
            "event": "tool_call",
            "request_id": secrets.token_hex(8),
            "actor": actor or "unknown",
            "tool": name,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "result_class": result_class,
            "guard_decision": decision,
        }
        print(json.dumps(event, ensure_ascii=False, sort_keys=True), file=sys.stderr)


def make_handler(app: IntToolsMcpApp) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "int-tools-chatgpt-mcp/0.1"

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._common_headers()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._json(200, app.health())
                return
            self._json(404, {"ok": False, "error": {"code": "not_found", "message": self.path}})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/mcp":
                self._json(404, {"ok": False, "error": {"code": "not_found", "message": self.path}})
                return
            if not self._authorized():
                self._json(401, {"ok": False, "error": {"code": "unauthorized", "message": "Bearer token required"}})
                return
            try:
                payload = self._read_json()
            except ValueError as exc:
                self._json(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}})
                return
            actor = self.headers.get("X-OpenAI-User-ID") or self.headers.get("X-Actor-ID")
            if isinstance(payload, list):
                responses = [app.handle_rpc(item, actor=actor) for item in payload if isinstance(item, dict)]
                self._json(200, [item for item in responses if item is not None])
                return
            if not isinstance(payload, dict):
                self._json(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "request must be an object"}})
                return
            response = app.handle_rpc(payload, actor=actor)
            self._json(200, response or {})

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            if app.config.access_log:
                super().log_message(format, *args)

        def _authorized(self) -> bool:
            token = app.config.bearer_token
            if not token:
                return True
            header = self.headers.get("Authorization", "")
            prefix = "Bearer "
            return header.startswith(prefix) and secrets.compare_digest(header[len(prefix) :].strip(), token)

        def _read_json(self) -> Any:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length)
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError("invalid JSON") from exc

        def _json(self, status: int, payload: Any) -> None:
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self._common_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _common_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "authorization, content-type, x-actor-id, x-openai-user-id")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    return Handler


def run(config: ServerConfig | None = None, adapter: IntToolsAdapter | None = None) -> None:
    app = IntToolsMcpApp(adapter=adapter, config=config or ServerConfig.from_env())
    server = ThreadingHTTPServer((app.config.host, app.config.port), make_handler(app))
    server.serve_forever()


def main() -> int:
    config = ServerConfig.from_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=config.host)
    parser.add_argument("--port", type=int, default=config.port)
    parser.add_argument("--access-log", action="store_true", default=config.access_log)
    args = parser.parse_args()
    run(ServerConfig(host=args.host, port=args.port, bearer_token=config.bearer_token, access_log=args.access_log))
    return 0


def _json_result(req_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _json_error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or [], "additionalProperties": False}


READ_ONLY_ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}


TOOL_DESCRIPTORS: dict[str, dict[str, Any]] = {
    "search": {
        "name": "search",
        "title": "Search intData knowledge",
        "description": "Use this when ChatGPT needs to search intData knowledge, memory, or context.",
        "inputSchema": _schema(
            {
                "query": {"type": "string", "minLength": 1},
                "owner_id": {"type": "integer"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 25},
                "days": {"type": "integer", "minimum": 0, "maximum": 3650},
                "repo": {"type": "string"},
            },
            ["query"],
        ),
        "annotations": READ_ONLY_ANNOTATIONS,
    },
    "fetch": {
        "name": "fetch",
        "title": "Fetch intData knowledge item",
        "description": "Use this when ChatGPT needs one specific intData memory item returned by search.",
        "inputSchema": _schema({"id": {"type": "string", "minLength": 1}}, ["id"]),
        "annotations": READ_ONLY_ANNOTATIONS,
    },
    "routing_validate": {
        "name": "routing_validate",
        "title": "Validate tool routing",
        "description": "Use this when ChatGPT needs to validate the high-risk intData tooling routing registry.",
        "inputSchema": _schema({"strict": {"type": "boolean"}, "json": {"type": "boolean"}, "cwd": {"type": "string"}, "timeout_sec": {"type": "integer", "minimum": 1, "maximum": 120}}),
        "annotations": READ_ONLY_ANNOTATIONS,
    },
    "lockctl_status": {
        "name": "lockctl_status",
        "title": "Lock status",
        "description": "Use this when ChatGPT needs read-only lock state for a repo, path, owner, or issue.",
        "inputSchema": _schema(
            {"repo_root": {"type": "string", "minLength": 1}, "path": {"type": "string"}, "owner": {"type": "string"}, "issue": {"type": "string"}},
            ["repo_root"],
        ),
        "annotations": READ_ONLY_ANNOTATIONS,
    },
}


if __name__ == "__main__":
    raise SystemExit(main())
