from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from int_tools_mcp.server import IntToolsMcpApp, ServerConfig, TOOL_NAMES, make_handler


class FakeAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def call_tool(self, name: str, arguments: dict) -> dict:
        self.calls.append((name, arguments))
        return {
            "structuredContent": {"ok": True, "tool": name, "arguments": arguments},
            "content": [{"type": "text", "text": f"{name} ok"}],
            "isError": False,
        }


class ServerTest(unittest.TestCase):
    def test_tools_list_exposes_exact_v1_allowlist(self) -> None:
        app = IntToolsMcpApp(adapter=FakeAdapter(), config=ServerConfig())

        response = app.handle_rpc({"id": 1, "method": "tools/list", "params": {}})
        tools = response["result"]["tools"]
        names = [tool["name"] for tool in tools]

        self.assertEqual(names, list(TOOL_NAMES))
        self.assertNotIn("agent_plane_call", names)
        self.assertFalse([name for name in names if name.startswith("multica_")])
        self.assertFalse([name for name in names if name.startswith("openspec_")])
        self.assertFalse([name for name in names if name in {"lockctl_acquire", "browser_profile_launch"}])

    def test_tool_descriptors_are_read_only_and_apps_friendly(self) -> None:
        app = IntToolsMcpApp(adapter=FakeAdapter(), config=ServerConfig())

        for tool in app.tools():
            self.assertTrue(tool["description"].startswith("Use this when"))
            self.assertEqual(tool["inputSchema"]["type"], "object")
            self.assertTrue(tool["annotations"]["readOnlyHint"])
            self.assertFalse(tool["annotations"]["destructiveHint"])

    def test_call_result_uses_structured_content(self) -> None:
        adapter = FakeAdapter()
        app = IntToolsMcpApp(adapter=adapter, config=ServerConfig())

        response = app.handle_rpc({"id": 2, "method": "tools/call", "params": {"name": "search", "arguments": {"query": "x"}}})
        result = response["result"]

        self.assertIn("structuredContent", result)
        self.assertEqual(result["content"][0]["type"], "text")
        self.assertEqual(adapter.calls, [("search", {"query": "x"})])

    def test_unknown_tool_is_tool_error_not_dispatch(self) -> None:
        app = IntToolsMcpApp(adapter=FakeAdapter(), config=ServerConfig())

        response = app.handle_rpc({"id": 3, "method": "tools/call", "params": {"name": "agent_plane_call", "arguments": {}}})
        result = response["result"]

        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["error"]["code"], "unknown_tool")

    def test_http_auth(self) -> None:
        app = IntToolsMcpApp(adapter=FakeAdapter(), config=ServerConfig(bearer_token="secret"))
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_address[1]}/mcp"
        payload = {"id": 1, "method": "tools/list", "params": {}}

        with self.assertRaises(urllib.error.HTTPError) as raised:
            _post_json(url, payload)
        self.assertEqual(raised.exception.code, 401)
        raised.exception.close()

        response = _post_json(url, payload, token="secret")
        self.assertEqual([tool["name"] for tool in response["result"]["tools"]], list(TOOL_NAMES))


def _post_json(url: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST", headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
