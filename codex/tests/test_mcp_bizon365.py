#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path("/git/tools/codex/bin/mcp-bizon365.py")
SPEC = importlib.util.spec_from_file_location("mcp_bizon365", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Bizon365ModuleTest(unittest.TestCase):
    def test_extract_captcha(self) -> None:
        html = """
        <script>
        window.captcha_1 = '12345';
        window.captcha_2 = 'abcde';
        </script>
        """
        self.assertEqual(MODULE._extract_captcha(html), ("12345", "abcde"))

    def test_allowed_tool_names_for_role(self) -> None:
        viewer_tools = MODULE.allowed_tool_names_for_role("viewer")
        operator_tools = MODULE.allowed_tool_names_for_role("operator")
        admin_tools = MODULE.allowed_tool_names_for_role("admin")
        self.assertIn("bizon_list_rooms", viewer_tools)
        self.assertNotIn("bizon_download_disk_file", viewer_tools)
        self.assertIn("bizon_download_disk_file", operator_tools)
        self.assertNotIn("bizon_raw_post", operator_tools)
        self.assertIn("bizon_raw_post", admin_tools)

    def test_build_server_registers_tools(self) -> None:
        server = MODULE.build_server(
            env={
                "BIZON365_PROJECT_ID": "101412",
                "BIZON365_LOGIN": "x",
                "BIZON365_PASSWORD": "y",
                "BIZON365_MCP_PROFILE_ROLES": json.dumps({"codex": "operator", "openclaw": "admin"}),
            },
            client_profile="codex",
        )
        self.assertEqual(server.name, "bizon365")

    def test_validate_path_allowlist(self) -> None:
        env = {
            "BIZON365_PROJECT_ID": "101412",
            "BIZON365_LOGIN": "x",
            "BIZON365_PASSWORD": "y",
        }
        client = MODULE.BizonClient(env)
        self.assertEqual(
            client._validate_path("/admin/account/api/101412/getProjectInfo", "raw", method="GET"),
            "/admin/account/api/101412/getProjectInfo",
        )
        with self.assertRaises(MODULE.BizonError) as blocked:
            client._validate_path("/admin/account/api/101412/saveCommonSettings", "raw", method="POST")
        self.assertEqual(blocked.exception.code, "unsafe_operation_blocked")
        with self.assertRaises(MODULE.BizonError) as denied:
            client._validate_path("/admin/kassa/101412/orders", "raw", method="GET")
        self.assertEqual(denied.exception.code, "endpoint_not_allowed")

    def test_normalize_disk_file_builds_direct_url(self) -> None:
        env = {
            "BIZON365_PROJECT_ID": "101412",
            "BIZON365_LOGIN": "x",
            "BIZON365_PASSWORD": "y",
        }
        services = MODULE.BizonMCPServices(env=env, role="operator", client_profile="codex")
        normalized = services._normalize_disk_file(
            {
                "name": "101412-course-2906_2023-06-29-14-05.mp4",
                "content_type": "video",
                "bytes": 407798594,
                "created": "2023-06-29T14:06:16.000000000Z",
            },
            {
                "cdn": "https://cdn.bizon365.ru",
                "url": "/userfiles/101412",
                "commonPath": "/userfiles/common/",
            },
        )
        self.assertEqual(normalized["storage"], "project")
        self.assertTrue(normalized["direct_url"].startswith("https://cdn.bizon365.ru/101412/"))
        self.assertIn("course-2906", normalized["direct_url"])

    def test_find_archive_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "room_recs_101412-course-2906_B1L0LfPxA.json").write_text(
                json.dumps({"room": "101412:course-2906", "data": []}),
                encoding="utf-8",
            )
            (root / "101412-course-2906_2023-06-29-14-05.mp4").write_bytes(b"video")
            env = {
                "BIZON365_PROJECT_ID": "101412",
                "BIZON365_LOGIN": "x",
                "BIZON365_PASSWORD": "y",
                "BIZON365_ARCHIVE_YADISK_ROOT": str(root),
            }
            services = MODULE.BizonMCPServices(env=env, role="operator", client_profile="codex")
            matches = services._find_archive_matches("course 2906", limit=5, kinds={"room_recs", "mp4"})
            self.assertEqual(len(matches), 2)
            self.assertEqual(matches[0]["source"], "archive_yadisk")

    def test_get_archive_room_rec_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payload = {
                "app": "bizon-script-editor",
                "room": "101412:profstory",
                "data": [
                    {"action": "goOnline", "timeshift": 10, "data": {}},
                    {"action": "post", "timeshift": 20, "username": "User 1", "message": "Hello", "role": "guest"},
                    {"action": "post", "timeshift": 30, "username": "Admin", "message": "Hi", "role": "admin"},
                    {"action": "stopRecord", "timeshift": 40, "data": {}},
                ],
            }
            file_path = root / "room_recs_101412-profstory_He5Y4k2lR.json"
            file_path.write_text(json.dumps(payload), encoding="utf-8")
            env = {
                "BIZON365_PROJECT_ID": "101412",
                "BIZON365_LOGIN": "x",
                "BIZON365_PASSWORD": "y",
                "BIZON365_ARCHIVE_YADISK_ROOT": str(root),
            }
            services = MODULE.BizonMCPServices(env=env, role="operator", client_profile="codex")
            response = services.tool_get_archive_room_rec(room="profstory")
            self.assertTrue(response["ok"])
            self.assertEqual(response["source"], "archive_yadisk")
            self.assertEqual(response["data"]["post_count"], 2)
            self.assertEqual(response["data"]["timeshift_range_sec"]["max"], 40)

    def test_archive_room_rec_blocks_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            outside = root.parent / "outside.json"
            outside.write_text(json.dumps({"room": "outside", "data": []}), encoding="utf-8")
            env = {
                "BIZON365_PROJECT_ID": "101412",
                "BIZON365_LOGIN": "x",
                "BIZON365_PASSWORD": "y",
                "BIZON365_ARCHIVE_YADISK_ROOT": str(root),
            }
            services = MODULE.BizonMCPServices(env=env, role="operator", client_profile="codex")
            with self.assertRaises(MODULE.BizonError) as blocked:
                services.tool_get_archive_room_rec(filename=str(outside))
            self.assertEqual(blocked.exception.code, "endpoint_not_allowed")


if __name__ == "__main__":
    unittest.main()
