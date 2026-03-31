#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import unittest
import json
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

    def test_resolve_state_dir_uses_codex_home(self):
        with mock.patch.dict(os.environ, {"LOCKCTL_STATE_DIR": "", "CODEX_HOME": r"D:\\users\\me\\.codex"}, clear=False):
            expected = (Path(r"D:\users\me\.codex") / "memories" / "lockctl").resolve()
            self.assertEqual(lockctl_core.resolve_state_dir(), expected)

    def test_normalize_path_accepts_windows_absolute_under_repo(self):
        repo_root = str(Path(r"D:\int\tools").resolve())
        abs_path = str((Path(repo_root) / "README.md").resolve())
        self.assertEqual(lockctl_core.normalize_path(repo_root, abs_path), "README.md")

    def test_normalize_path_rejects_escape(self):
        repo_root = str(Path(r"D:\int\tools").resolve())
        with self.assertRaises(lockctl_core.LockCtlError):
            lockctl_core.normalize_path(repo_root, "..\\outside.txt")

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

    def test_windows_legacy_state_migration_moves_with_backup_and_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            canonical = tmp_path / "canonical"
            legacy = tmp_path / "legacy"
            legacy.mkdir(parents=True, exist_ok=True)
            sample = legacy / "events.jsonl"
            sample.write_text("{\"ok\": true}\n", encoding="utf-8")

            env = {
                "LOCKCTL_SKIP_WINDOWS_MIGRATION": "",
                "LOCKCTL_LEGACY_WINDOWS_STATE_DIR": str(legacy),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(lockctl_core.os, "name", "nt"):
                    lockctl_core._maybe_migrate_windows_legacy_state(canonical)

            self.assertTrue((canonical / "events.jsonl").exists())
            self.assertFalse(legacy.exists())
            marker = canonical / lockctl_core.WINDOWS_MIGRATION_MARKER
            self.assertTrue(marker.exists())
            payload = json.loads(marker.read_text(encoding="utf-8"))
            backup_dir = Path(payload["backup_dir"])
            self.assertTrue(backup_dir.exists())
            self.assertTrue((backup_dir / "events.jsonl").exists())

    def test_windows_legacy_state_migration_is_idempotent_after_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            canonical = tmp_path / "canonical"
            legacy = tmp_path / "legacy"
            canonical.mkdir(parents=True, exist_ok=True)
            legacy.mkdir(parents=True, exist_ok=True)
            marker = canonical / lockctl_core.WINDOWS_MIGRATION_MARKER
            marker.write_text("already-migrated\n", encoding="utf-8")

            env = {
                "LOCKCTL_SKIP_WINDOWS_MIGRATION": "",
                "LOCKCTL_LEGACY_WINDOWS_STATE_DIR": str(legacy),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(lockctl_core.os, "name", "nt"):
                    lockctl_core._maybe_migrate_windows_legacy_state(canonical)

            self.assertTrue(legacy.exists())
            self.assertEqual(marker.read_text(encoding="utf-8"), "already-migrated\n")


if __name__ == "__main__":
    unittest.main()
