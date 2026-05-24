from __future__ import annotations

import asyncio
import unittest

from bitrix24_mcp import client, server


class Bitrix24ClientTests(unittest.TestCase):
    def test_allows_read_only_methods(self) -> None:
        self.assertEqual(client.normalize_method("crm.deal.get"), "crm.deal.get")
        self.assertEqual(client.normalize_method("crm.timeline.comment.list.json"), "crm.timeline.comment.list")

    def test_blocks_mutating_methods(self) -> None:
        with self.assertRaises(client.Bitrix24APIError):
            client.normalize_method("crm.deal.update")

    def test_blocks_unknown_methods(self) -> None:
        with self.assertRaises(client.Bitrix24APIError):
            client.normalize_method("batch")

    def test_redacts_webhook_url(self) -> None:
        value = client.redact("https://example.bitrix24.ru/rest/1/secret-code/profile.json")

        self.assertEqual(value, "https://example.bitrix24.ru/rest/***/profile.json")


class Bitrix24ServerTests(unittest.TestCase):
    def test_registered_tool_count(self) -> None:
        async def run() -> list[str]:
            tools = await server.mcp.list_tools()
            return sorted(tool.name for tool in tools)

        names = asyncio.run(run())
        self.assertEqual(len(names), 16)
        self.assertIn("bitrix24_deal_get", names)
        self.assertIn("bitrix24_raw_read_call", names)


if __name__ == "__main__":
    unittest.main()
