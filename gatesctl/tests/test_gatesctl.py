#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import gatesctl  # noqa: E402


class GatesCtlStateTest(unittest.TestCase):
    def test_resolve_state_dir_uses_env_override(self):
        with mock.patch.dict(os.environ, {"GATESCTL_STATE_DIR": r"D:\\tmp\\gatesctl-state"}, clear=False):
            self.assertEqual(gatesctl.resolve_state_dir(), Path(r"D:\tmp\gatesctl-state").resolve())

    def test_resolve_state_dir_uses_tools_runtime_even_with_codex_home(self):
        env = {"GATESCTL_STATE_DIR": "", "CODEX_HOME": r"D:\\users\\me\\.codex"}
        with mock.patch.dict(os.environ, env, clear=False):
            expected = (MODULE_DIR.parent / ".runtime" / "gatesctl").resolve()
            self.assertEqual(gatesctl.resolve_state_dir(), expected)

    def test_legacy_state_migration_copies_without_removing_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            canonical = tmp_path / "canonical"
            legacy = tmp_path / "legacy"
            legacy.mkdir(parents=True, exist_ok=True)
            sample = legacy / "events.jsonl"
            sample.write_text("{\"ok\": true}\n", encoding="utf-8")

            env = {
                "GATESCTL_SKIP_LEGACY_MIGRATION": "",
                "GATESCTL_LEGACY_STATE_DIR": str(legacy),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                gatesctl.maybe_migrate_legacy_state(canonical)

            self.assertTrue((canonical / "events.jsonl").exists())
            self.assertTrue(legacy.exists())
            self.assertTrue((legacy / "events.jsonl").exists())
            marker = canonical / gatesctl.LEGACY_MIGRATION_MARKER
            self.assertTrue(marker.exists())
            payload = json.loads(marker.read_text(encoding="utf-8"))
            self.assertIn(str(legacy.resolve()), payload["legacy_dirs"])


if __name__ == "__main__":
    unittest.main()
