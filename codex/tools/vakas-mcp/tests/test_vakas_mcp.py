from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vakas_mcp import client, config, server


class DestinationTests(unittest.TestCase):
    def test_allows_vakas_https_host_and_subdomain(self) -> None:
        client.validate_destination("https://vakas-tools.ru/private-hook")
        client.validate_destination("https://events.vakas-tools.ru/private-hook")

    def test_rejects_lookalike_insecure_and_credential_urls(self) -> None:
        for endpoint in (
            "http://vakas-tools.ru/private-hook",
            "https://evilvakas-tools.ru/private-hook",
            "https://user:pass@vakas-tools.ru/private-hook",
            "https://vakas-tools.ru:444/private-hook",
        ):
            with self.subTest(endpoint=endpoint), self.assertRaises(client.VakasError):
                client.validate_destination(endpoint)


class PayloadTests(unittest.TestCase):
    def test_documented_registration_payload_is_accepted(self) -> None:
        normalized = client.normalize_payload(
            "registration",
            {"email": "person@example.com", "name": "Person", "utm_source": "site"},
        )
        self.assertEqual(set(normalized), {"email", "name", "utm_source"})

    def test_unknown_fields_and_missing_contact_are_rejected(self) -> None:
        with self.assertRaises(client.VakasError) as unknown:
            client.normalize_payload("registration", {"email": "x@example.com", "token": "secret"})
        self.assertEqual(unknown.exception.code, "unsupported_fields")
        with self.assertRaises(client.VakasError) as missing:
            client.normalize_payload("order", {"number": "42"})
        self.assertEqual(missing.exception.code, "missing_contact")

    def test_summary_never_contains_values(self) -> None:
        payload = {"email": "person@example.com", "phone": "+70000000000"}
        summary = client.payload_summary("registration", payload)
        rendered = repr(summary)
        self.assertNotIn("person@example.com", rendered)
        self.assertNotIn("+70000000000", rendered)
        self.assertEqual(summary["fields"], ["email", "phone"])


class ConfigTests(unittest.TestCase):
    def test_endpoint_file_must_be_private_and_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "endpoint"
            path.write_text("https://vakas-tools.ru/private-hook", encoding="utf-8")
            path.chmod(0o600)
            with mock.patch.dict(os.environ, {"VAKAS_REGISTRATION_ENDPOINT_FILE": str(path)}, clear=True):
                loaded = config.Config.load()
        self.assertEqual(loaded.endpoint_sources["registration"], "file")
        self.assertIsNotNone(loaded.endpoints["registration"])


def make_config(endpoint: str | None = None) -> config.Config:
    return config.Config(
        endpoints={"registration": endpoint, "report": None, "order": None},
        endpoint_sources={
            "registration": "file" if endpoint else "unset",
            "report": "unset",
            "order": "unset",
        },
        timeout_seconds=15,
        dedupe_ttl_seconds=86400,
        transport="stdio",
        port=8768,
    )


class ServerGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        server._config = make_config()
        server._client = None

    def tearDown(self) -> None:
        server._config = None
        server._client = None

    def test_health_does_not_expose_endpoint_values(self) -> None:
        server._config = make_config("https://vakas-tools.ru/private-secret-path?token=secret")
        result = asyncio.run(server.vakas_health())
        rendered = repr(result)
        self.assertTrue(result["ok"])
        self.assertNotIn("private-secret-path", rendered)
        self.assertNotIn("token=secret", rendered)

    def test_default_submission_is_dry_run_without_network(self) -> None:
        with mock.patch.object(server, "_get_client") as get_client:
            result = asyncio.run(server.vakas_submit_registration({"email": "person@example.com"}))
        get_client.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["network_attempted"])
        self.assertNotIn("person@example.com", repr(result))

    def test_confirmed_submission_requires_endpoint(self) -> None:
        result = asyncio.run(
            server.vakas_submit_registration(
                {"email": "person@example.com"},
                idempotency_key="event-42",
                confirm_write=True,
            )
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_code"], "endpoint_not_configured")

    def test_confirmed_submission_requires_idempotency_key(self) -> None:
        server._config = make_config("https://vakas-tools.ru/private-secret-path")
        result = asyncio.run(
            server.vakas_submit_registration(
                {"email": "person@example.com"},
                confirm_write=True,
            )
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_code"], "idempotency_key_required")

    def test_confirmed_dispatch_returns_redacted_metadata(self) -> None:
        server._config = make_config("https://vakas-tools.ru/private-secret-path")
        fake_client = mock.Mock()
        fake_client.dispatch = mock.AsyncMock(
            return_value=client.DispatchResult(status_code=204, accepted=True)
        )
        with mock.patch.object(server, "_get_client", return_value=fake_client):
            result = asyncio.run(
                server.vakas_submit_registration(
                    {"email": "person@example.com"},
                    idempotency_key="event-42",
                    confirm_write=True,
                )
            )
        self.assertTrue(result["ok"])
        self.assertFalse(result["dry_run"])
        self.assertNotIn("private-secret-path", repr(result))
        self.assertNotIn("person@example.com", repr(result))


class DedupeTests(unittest.TestCase):
    def test_duplicate_idempotency_key_is_suppressed(self) -> None:
        async def run() -> None:
            vakas = client.VakasClient(dedupe_ttl_seconds=60)
            await vakas._reserve("registration", "same-key")
            with self.assertRaises(client.VakasError) as duplicate:
                await vakas._reserve("registration", "same-key")
            self.assertEqual(duplicate.exception.code, "duplicate_suppressed")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
