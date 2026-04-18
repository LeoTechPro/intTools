from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .audit import AuditStore, create_audit_store
from .dispatcher import ToolDispatcher
from .models import ToolCallRequest, ValidationError
from .policy import PolicyEngine


class AgentPlane:
    def __init__(
        self,
        dispatcher: Any | None = None,
        policy: PolicyEngine | None = None,
        audit_store: AuditStore | None = None,
    ) -> None:
        self.dispatcher = dispatcher or ToolDispatcher()
        self.policy = policy or PolicyEngine()
        self.audit_store = audit_store or create_audit_store()

    def health(self) -> dict[str, Any]:
        return {"ok": True, "service": "int-agent-plane"}

    def tools(self) -> dict[str, Any]:
        return {"ok": True, "tools": self.dispatcher.list_tools()}

    def audit_recent(self, limit: int = 50) -> dict[str, Any]:
        return {"ok": True, "items": self.audit_store.recent(limit)}

    def call_tool(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            request = ToolCallRequest.from_payload(payload)
        except ValidationError as exc:
            return {"ok": False, "error": {"code": "invalid_request", "message": str(exc)}}

        decision = self.policy.decide(request)
        if not decision.allowed:
            error = {"code": "policy_rejected", "message": decision.reason}
            entry = self.audit_store.record(request, decision, "rejected", error=error)
            return {
                "ok": False,
                "policy_decision_id": decision.decision_id,
                "tool_call_id": entry.id,
                "error": error,
            }

        try:
            result = self.dispatcher.call(request.tool, request.args)
        except Exception as exc:  # noqa: BLE001
            error = {"code": "dispatch_error", "message": str(exc)}
            entry = self.audit_store.record(request, decision, "error", error=error)
            return {
                "ok": False,
                "policy_decision_id": decision.decision_id,
                "tool_call_id": entry.id,
                "error": error,
            }

        status = "ok" if bool(result.get("ok")) else "error"
        entry = self.audit_store.record(request, decision, status, result=result)
        return {
            "ok": bool(result.get("ok")),
            "result": result,
            "policy_decision_id": decision.decision_id,
            "tool_call_id": entry.id,
            "error": None if result.get("ok") else {"code": "tool_error", "message": "canonical tool returned error"},
        }


def make_handler(plane: AgentPlane) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "int-agent-plane/0.1"

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._json(200, plane.health())
                return
            if self.path == "/v1/tools":
                self._json(200, plane.tools())
                return
            if self.path.startswith("/v1/audit/tool-calls"):
                self._json(200, plane.audit_recent(_limit_from_path(self.path)))
                return
            self._json(404, {"ok": False, "error": {"code": "not_found", "message": self.path}})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/tools/call":
                self._json(404, {"ok": False, "error": {"code": "not_found", "message": self.path}})
                return
            try:
                payload = self._read_json()
            except ValueError as exc:
                self._json(400, {"ok": False, "error": {"code": "invalid_json", "message": str(exc)}})
                return
            response = plane.call_tool(payload)
            self._json(200 if response.get("ok") else 400, response)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            if os.getenv("AGENT_PLANE_ACCESS_LOG", "").lower() in {"1", "true", "yes"}:
                super().log_message(format, *args)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("payload must be an object")
            return payload

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def run(host: str, port: int, plane: AgentPlane | None = None) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(plane or AgentPlane()))
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("AGENT_PLANE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("AGENT_PLANE_PORT", "9192")))
    args = parser.parse_args()
    run(args.host, args.port)
    return 0


def _limit_from_path(path: str) -> int:
    if "limit=" not in path:
        return 50
    try:
        return max(1, min(500, int(path.split("limit=", 1)[1].split("&", 1)[0])))
    except ValueError:
        return 50


if __name__ == "__main__":
    raise SystemExit(main())
