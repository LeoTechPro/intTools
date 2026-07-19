from __future__ import annotations

import asyncio
import unittest
from unittest import mock

import httpx

from bitrix24_mcp import api_manifest, client, server
from scripts import update_api_manifest


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

    def test_manifest_allows_documented_non_crm_method(self) -> None:
        self.assertEqual(client.normalize_manifest_method("tasks.task.list"), "tasks.task.list")

    def test_manifest_blocks_unknown_method(self) -> None:
        with self.assertRaises(client.Bitrix24APIError):
            client.normalize_manifest_method("private.ui.method")

    def test_redacts_webhook_url(self) -> None:
        value = client.redact("https://example.bitrix24.ru/rest/1/secret-code/profile.json")

        self.assertEqual(value, "https://example.bitrix24.ru/rest/***/profile.json")


class Bitrix24ServerTests(unittest.TestCase):
    def test_registered_tool_count(self) -> None:
        async def run() -> list[str]:
            tools = await server.mcp.list_tools()
            return sorted(tool.name for tool in tools)

        names = asyncio.run(run())
        self.assertEqual(len(names), 19)
        self.assertIn("bitrix24_deal_get", names)
        self.assertIn("bitrix24_raw_read_call", names)
        self.assertIn("bitrix24_api_call", names)
        self.assertIn("bitrix24_api_manifest", names)

    def test_manifest_has_pinned_official_provenance_and_broad_coverage(self) -> None:
        manifest = api_manifest.load_manifest()

        self.assertEqual(manifest["official_repository"], "https://github.com/bitrix24/b24restdocs")
        self.assertRegex(manifest["official_commit"], r"^[0-9a-f]{40}$")
        self.assertGreater(manifest["counts"]["server_methods"], 1000)
        self.assertGreater(manifest["counts"]["events"], 0)
        self.assertGreater(manifest["counts"]["browser_js"], 0)
        self.assertGreater(manifest["counts"]["outdated"], 0)

    def test_manifest_resolves_read_and_write_server_methods(self) -> None:
        self.assertEqual(api_manifest.resolve_server_method("crm.item.list")["risk"], "read")
        self.assertEqual(api_manifest.resolve_server_method("crm.item.add")["risk"], "write")

    def test_manifest_resolves_documented_single_token_methods(self) -> None:
        for method in ("batch", "events", "methods", "profile", "scope"):
            with self.subTest(method=method):
                self.assertEqual(api_manifest.resolve_server_method(method)["method"], method)

        self.assertEqual(
            api_manifest.load_manifest()["single_token_endpoints"],
            ["batch", "events", "methods", "profile", "scope"],
        )

    def test_non_callable_manifest_entries_fail_closed(self) -> None:
        for kind in ("browser_js", "event", "outdated"):
            with self.subTest(kind=kind):
                excluded = next(row for row in api_manifest.load_manifest()["entries"] if row["kind"] == kind)
                with self.assertRaises(api_manifest.ManifestError):
                    api_manifest.resolve_server_method(excluded["method"])

    def test_generator_classifies_representative_surfaces(self) -> None:
        self.assertEqual(update_api_manifest._entry_kind("crm.item.list", "api-reference/crm/item.md"), "server_method")
        self.assertEqual(update_api_manifest._entry_kind("BX24.placement.call", "api-reference/widgets/x.md"), "browser_js")
        self.assertEqual(update_api_manifest._entry_kind("CATALOG.PRICE.ON.ADD", "api-reference/catalog/events/x.md"), "event")
        self.assertEqual(update_api_manifest._entry_kind("rpa.item.list", "api-reference/outdated/rpa/x.md"), "outdated")

    def test_generator_pins_single_token_methods_to_official_pages(self) -> None:
        self.assertEqual(
            update_api_manifest.EXPLICIT_SINGLE_TOKEN_METHODS["settings/how-to-call-rest-api/batch.md"],
            "batch",
        )

    def test_manifest_call_preserves_method_and_uses_configured_host(self) -> None:
        async def run() -> None:
            async def handler(request: httpx.Request) -> httpx.Response:
                self.assertTrue(request.url.path.endswith("/tasks.task.list.json"))
                self.assertEqual(request.headers["content-type"], "application/json")
                self.assertEqual(request.content, b'{"filter":{"STATUS":2}}')
                return httpx.Response(200, json={"result": {"tasks": []}})

            config = mock.Mock(webhook_url="https://example.bitrix24.ru/rest/1/secret/", timeout=30.0)
            instance = client.Bitrix24Client(config)
            await instance._client.aclose()
            instance._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            try:
                result = await instance.call_manifest("tasks.task.list", {"filter": {"STATUS": 2}})
                self.assertIn("result", result)
            finally:
                await instance.close()

        asyncio.run(run())

    def test_error_envelope_does_not_return_remote_personal_data(self) -> None:
        exc = client.Bitrix24APIError(
            "denied",
            403,
            {"error": "ACCESS_DENIED", "error_description": "user@example.test"},
        )

        self.assertEqual(
            server._error(exc),
            {"ok": False, "error": "denied", "status_code": 403, "remote_error_code": "ACCESS_DENIED"},
        )


if __name__ == "__main__":
    unittest.main()
