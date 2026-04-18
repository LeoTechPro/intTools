from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from agent_plane.audit import MemoryAuditStore
from agent_plane.dispatcher import StaticDispatcher, ToolDispatcher
from agent_plane.server import AgentPlane, make_handler


class AgentPlaneTest(unittest.TestCase):
    def test_rejects_unknown_facade_without_dispatch(self) -> None:
        dispatcher = StaticDispatcher()
        plane = AgentPlane(dispatcher=dispatcher, audit_store=MemoryAuditStore())

        response = plane.call_tool({"facade": "other", "principal": {"id": "x"}, "tool": "intbrain_context_pack"})

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "invalid_request")
        self.assertEqual(dispatcher.calls, [])

    def test_rejects_cabinet_tool_surface(self) -> None:
        dispatcher = StaticDispatcher()
        plane = AgentPlane(dispatcher=dispatcher, audit_store=MemoryAuditStore())

        response = plane.call_tool({"facade": "codex_app", "principal": {"id": "codex"}, "tool": "cabinet_search"})

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "invalid_request")
        self.assertEqual(dispatcher.calls, [])

    def test_runtime_dispatcher_hides_intbrain_cabinet_tools(self) -> None:
        dispatcher = ToolDispatcher()

        names = {tool["name"] for tool in dispatcher.list_tools()}

        self.assertNotIn("intbrain_cabinet_inventory", names)
        self.assertNotIn("intbrain_cabinet_import", names)
        self.assertNotIn("intbrain_cabinet_import", dispatcher.tool_to_profile)

    def test_guarded_tool_requires_approval_and_is_audited(self) -> None:
        audit = MemoryAuditStore()
        dispatcher = StaticDispatcher()
        plane = AgentPlane(dispatcher=dispatcher, audit_store=audit)

        response = plane.call_tool({"facade": "openclaw", "principal": {"chat_id": "-5266118767"}, "tool": "lockctl_acquire", "args": {}})

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "policy_rejected")
        self.assertEqual(dispatcher.calls, [])
        self.assertEqual(audit.recent()[0]["source_facade"], "openclaw")
        self.assertEqual(audit.recent()[0]["status"], "rejected")

    def test_allowed_call_dispatches_and_audits(self) -> None:
        audit = MemoryAuditStore()
        dispatcher = StaticDispatcher({"ok": True, "data": {"answer": 42}})
        plane = AgentPlane(dispatcher=dispatcher, audit_store=audit)

        response = plane.call_tool(
            {
                "facade": "codex_app",
                "principal": {"id": "codex"},
                "tool": "intbrain_context_pack",
                "args": {"owner_id": 1, "query": "test"},
            }
        )

        self.assertTrue(response["ok"])
        self.assertEqual(dispatcher.calls, [("intbrain_context_pack", {"owner_id": 1, "query": "test"})])
        self.assertEqual(audit.recent()[0]["source_facade"], "codex_app")
        self.assertEqual(audit.recent()[0]["status"], "ok")

    def test_http_smoke(self) -> None:
        plane = AgentPlane(dispatcher=StaticDispatcher(), audit_store=MemoryAuditStore())
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(plane))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_address[1]}"

        health = _get_json(base + "/health")
        self.assertTrue(health["ok"])

        payload = {
            "facade": "agno",
            "principal": {"agent_id": "agno-local"},
            "tool": "intbrain_context_pack",
            "args": {"owner_id": 1},
        }
        response = _post_json(base + "/v1/tools/call", payload)
        self.assertTrue(response["ok"])


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
