#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import lockctl_core  # noqa: E402


class LockCtlCoreTest(unittest.TestCase):
    def test_resolve_state_dir_uses_env_override(self):
        with mock.patch.dict(os.environ, {"LOCKCTL_STATE_DIR": r"D:\\tmp\\lockctl-state"}, clear=False):
            self.assertEqual(lockctl_core.resolve_state_dir(), Path(r"D:\tmp\lockctl-state").resolve())

    def test_resolve_state_dir_uses_tools_runtime_even_with_codex_home(self):
        with mock.patch.dict(os.environ, {"LOCKCTL_STATE_DIR": "", "CODEX_HOME": r"D:\\users\\me\\.codex"}, clear=False):
            expected = (MODULE_DIR.parent / ".runtime" / "lockctl").resolve()
            self.assertEqual(lockctl_core.resolve_state_dir(), expected)

    def test_normalize_path_accepts_windows_absolute_under_repo(self):
        repo_root = str(Path(r"D:\int\tools").resolve())
        abs_path = str((Path(repo_root) / "README.md").resolve())
        self.assertEqual(lockctl_core.normalize_path(repo_root, abs_path), "README.md")

    def test_normalize_path_rejects_escape(self):
        repo_root = str(Path(r"D:\int\tools").resolve())
        with self.assertRaises(lockctl_core.LockCtlError):
            lockctl_core.normalize_path(repo_root, "..\\outside.txt")

    def test_normalize_issue_is_optional(self):
        self.assertIsNone(lockctl_core.normalize_issue(None))
        self.assertIsNone(lockctl_core.normalize_issue(""))
        self.assertIsNone(lockctl_core.normalize_issue("   "))

    def test_normalize_issue_accepts_legacy_numeric_id(self):
        self.assertEqual(lockctl_core.normalize_issue("224"), "224")

    def test_normalize_issue_accepts_full_multica_id(self):
        self.assertEqual(lockctl_core.normalize_issue("INT-224"), "INT-224")
        self.assertEqual(lockctl_core.normalize_issue("int-224"), "INT-224")

    def test_normalize_issue_rejects_invalid_ids(self):
        for value in ("0", "0224", "INT-0", "INT-0224", "PB-224", "abc"):
            with self.subTest(value=value):
                with self.assertRaises(lockctl_core.LockCtlError):
                    lockctl_core.normalize_issue(value)

    def test_normalize_repo_root_accepts_posix_style_on_windows(self):
        if os.name != "nt":
            self.skipTest("Windows-only compatibility behavior")
        normalized = lockctl_core.normalize_repo_root("/int/tools")
        self.assertEqual(normalized, str(Path(r"D:\int\tools").resolve()))

    def test_normalize_repo_root_posix_windows_not_bound_to_cwd_drive(self):
        if os.name != "nt":
            self.skipTest("Windows-only compatibility behavior")
        module_drive = Path(lockctl_core.__file__).resolve().drive
        with mock.patch.object(lockctl_core.Path, "cwd", return_value=Path(r"C:\temp")):
            normalized = lockctl_core.normalize_repo_root("/int/tools")
        self.assertTrue(normalized.lower().endswith(r"\int\tools"))
        self.assertTrue(normalized.upper().startswith(module_drive.upper()))

    def test_ensure_state_dir_does_not_migrate_legacy_codex_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            canonical = tmp_path / "canonical"
            legacy = tmp_path / "legacy"
            legacy.mkdir(parents=True, exist_ok=True)
            (legacy / "events.jsonl").write_text("{\"ok\": true}\n", encoding="utf-8")

            env = {
                "CODEX_HOME": str(tmp_path / ".codex"),
                "LOCKCTL_LEGACY_WINDOWS_STATE_DIR": str(legacy),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(lockctl_core, "STATE_DIR", canonical):
                    lockctl_core.ensure_state_dir()

            self.assertTrue(canonical.exists())
            self.assertFalse((canonical / "events.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
