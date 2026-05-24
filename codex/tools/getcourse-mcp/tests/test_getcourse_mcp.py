from __future__ import annotations

import asyncio
import unittest
from unittest import mock

from getcourse_mcp import client, server


class GetCourseClientTests(unittest.TestCase):
    def test_pending_export_payload_is_not_error(self) -> None:
        payload = {"success": False, "info": {"export_id": 123}}

        self.assertTrue(client.is_export_pending_payload(payload))
        self.assertEqual(client.export_id_from_payload(payload), "123")

    def test_redact_nested_secret_fields(self) -> None:
        payload = {"user": {"api_key": "secret", "name": "User"}}

        self.assertEqual(client.redact(payload)["user"]["api_key"], "***redacted***")
        self.assertEqual(client.redact(payload)["user"]["name"], "User")

    def test_export_throttle_905_is_transient(self) -> None:
        payload = {"success": False, "error_code": 905, "error": "export is busy"}

        self.assertTrue(client.is_transient_export_error_payload(payload))
        self.assertEqual(client.error_code_from_payload(payload), 905)

    def test_export_910_is_not_ready(self) -> None:
        payload = {"success": False, "error_code": 910, "error": "file is not ready"}

        self.assertTrue(client.is_export_not_ready_payload(payload))
        self.assertFalse(client.is_transient_export_error_payload(payload))


class GetCourseServerTests(unittest.TestCase):
    def test_user_filters_use_getcourse_range_shape(self) -> None:
        params = server._build_user_filters(
            status="active",
            created_from="2026-05-01",
            created_to="2026-05-09",
        )

        self.assertEqual(
            params,
            {
                "status": "active",
                "created_at[from]": "2026-05-01",
                "created_at[to]": "2026-05-09",
            },
        )

    def test_empty_typed_export_filters_are_rejected(self) -> None:
        with self.assertRaises(client.GetCourseAPIError):
            server._require_filter({}, "users")

    def test_poll_bounds_are_clamped(self) -> None:
        self.assertEqual(server._bounded_int(99, minimum=1, maximum=10, name="attempts"), 10)
        self.assertEqual(server._bounded_float(99, minimum=0, maximum=10, name="interval"), 10)

    def test_export_wait_stops_when_export_is_ready(self) -> None:
        async def run() -> dict:
            with mock.patch.object(
                server,
                "_read_export",
                mock.AsyncMock(return_value={"ok": True, "pending": False, "data": {"items": [1]}}),
            ) as read_export:
                result = await server._wait_for_export(
                    "42",
                    attempts=3,
                    interval_seconds=0,
                )
                self.assertEqual(read_export.await_count, 1)
                return result

        result = asyncio.run(run())
        self.assertFalse(result["pending"])
        self.assertEqual(result["attempt"], 1)

    def test_export_result_910_http_200_is_pending(self) -> None:
        async def run() -> dict:
            api_error = client.GetCourseAPIError(
                "True",
                200,
                {"success": False, "error": True, "error_code": 910},
            )
            fake_client = mock.Mock()
            fake_client.get = mock.AsyncMock(side_effect=api_error)
            with mock.patch.object(server, "_get_client", return_value=fake_client):
                return await server._read_export("42")

        result = asyncio.run(run())
        self.assertTrue(result["ok"])
        self.assertTrue(result["pending"])
        self.assertEqual(result["export_id"], "42")

    def test_users_export_start_rejects_unfiltered_call_without_api(self) -> None:
        result = asyncio.run(server.getcourse_users_export_start())

        self.assertFalse(result["ok"])
        self.assertEqual(result["status_code"], 400)

    def test_group_users_export_rejects_unfiltered_call_without_api(self) -> None:
        result = asyncio.run(server.getcourse_group_users_export("123"))

        self.assertFalse(result["ok"])
        self.assertEqual(result["status_code"], 400)
        self.assertEqual(result["detail"]["dataset"], "group_users")

    def test_write_tools_require_explicit_confirmation(self) -> None:
        result = asyncio.run(server.getcourse_user_import({"user": {"email": "x@example.com"}}))

        self.assertFalse(result["ok"])
        self.assertEqual(result["status_code"], 400)
        self.assertIn("confirm_write=True", result["error"])

    def test_user_groups_update_builds_documented_update_payload(self) -> None:
        async def run() -> dict:
            with mock.patch.object(
                server,
                "_post_import",
                mock.AsyncMock(return_value={"ok": True}),
            ) as post_import:
                result = await server.getcourse_user_groups_update(
                    "123",
                    ["Group A", " "],
                    confirm_write=True,
                )
                post_import.assert_awaited_once_with(
                    resource="users",
                    action="update",
                    params={"user": {"id": "123", "group_name": ["Group A"]}},
                    confirm_write=True,
                    max_items=25,
                )
                return result

        result = asyncio.run(run())
        self.assertTrue(result["ok"])

    def test_group_users_export_uses_filters(self) -> None:
        async def run() -> dict:
            fake_client = mock.Mock()
            fake_client.get = mock.AsyncMock(return_value={"success": False, "info": {"export_id": 123}})
            with mock.patch.object(server, "_get_client", return_value=fake_client):
                result = await server.getcourse_group_users_export(
                    "456",
                    status="active",
                    added_from="2026-05-01",
                )
                fake_client.get.assert_awaited_once_with(
                    "/pl/api/account/groups/456/users",
                    params={"status": "active", "added_at[from]": "2026-05-01"},
                )
                return result

        result = asyncio.run(run())
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["info"]["export_id"], 123)

    def test_transient_export_error_response_has_retry_hint(self) -> None:
        exc = client.GetCourseAPIError(
            "too many requests",
            200,
            {"success": False, "error_code": 903, "error": "too many requests"},
        )

        result = server._error(exc)

        self.assertFalse(result["ok"])
        self.assertTrue(result["transient"])
        self.assertEqual(result["error_code"], 903)
        self.assertIn("retry", result["retry_hint"])


if __name__ == "__main__":
    unittest.main()
