from __future__ import annotations

import unittest

from int_tools_mcp.adapter import IntToolsAdapter, ToolCallError


class StubRuntime:
    def __init__(self, search_payload: dict | None = None) -> None:
        self.search_payload = search_payload or {"ok": True, "data": {"items": []}}
        self.calls: list[tuple[str, str, dict]] = []

    def _call_tool(self, profile: str, name: str, arguments: dict) -> dict:
        self.calls.append((profile, name, arguments))
        if name == "intbrain_memory_search":
            return self.search_payload
        return {"ok": True, "stdout": "ok", "argv": ["internal"], "cwd": "D:/int/tools"}


class AdapterTest(unittest.TestCase):
    def test_search_normalizes_results_and_fetches_cached_item(self) -> None:
        runtime = StubRuntime(
            {
                "ok": True,
                "data": {
                    "items": [
                        {
                            "source_hash": "abc123",
                            "title": "Found item",
                            "text_content": "Detailed memory text",
                            "source": "intbrain.memory",
                            "kind": "fact",
                        }
                    ]
                },
            }
        )
        adapter = IntToolsAdapter(runtime=runtime, default_owner_id=1)

        search = adapter.search({"query": "memory", "limit": 5})
        results = search["structuredContent"]["results"]

        self.assertEqual(search["structuredContent"]["count"], 1)
        self.assertEqual(results[0]["fetch_id"], "memory:abc123")
        fetch = adapter.fetch({"id": "memory:abc123"})
        self.assertTrue(fetch["structuredContent"]["found"])
        self.assertEqual(fetch["structuredContent"]["item"]["source_hash"], "abc123")
        self.assertEqual(runtime.calls[0], ("intbrain", "intbrain_memory_search", {"owner_id": 1, "query": "memory", "limit": 5}))

    def test_search_empty_result_is_not_error(self) -> None:
        adapter = IntToolsAdapter(runtime=StubRuntime(), default_owner_id=1)

        result = adapter.search({"query": "missing"})

        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"]["results"], [])

    def test_fetch_unknown_safe_id_is_empty_result(self) -> None:
        adapter = IntToolsAdapter(runtime=StubRuntime(), default_owner_id=1)

        result = adapter.fetch({"id": "memory:unknown"})

        self.assertFalse(result["isError"])
        self.assertFalse(result["structuredContent"]["found"])

    def test_fetch_rejects_forbidden_id(self) -> None:
        adapter = IntToolsAdapter(runtime=StubRuntime(), default_owner_id=1)

        with self.assertRaises(ToolCallError) as raised:
            adapter.fetch({"id": "file:D:/int/.env"})

        self.assertEqual(raised.exception.code, "forbidden_fetch_id")

    def test_control_uses_allowlisted_internal_tool_and_prunes_argv(self) -> None:
        runtime = StubRuntime()
        adapter = IntToolsAdapter(runtime=runtime, default_owner_id=1)

        result = adapter.control("lockctl_status", {"repo_root": "D:/int/tools"})

        self.assertEqual(runtime.calls[0][0:2], ("intdata-control", "lockctl_status"))
        self.assertNotIn("argv", result["structuredContent"]["result"])


if __name__ == "__main__":
    unittest.main()
