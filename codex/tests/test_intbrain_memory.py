from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT_DIR = Path(__file__).resolve().parents[1]
LIB_DIR = ROOT_DIR / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from intbrain_memory import IntBrainMemory, derive_repo, extract_items, iter_jsonl, load_session_meta, sanitize_text, session_in_scope


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines), encoding="utf-8")


class IntBrainMemoryTests(unittest.TestCase):
    def test_scope_repo_and_offset_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "session.jsonl"
            raw = (
                json.dumps({"type": "session_meta", "payload": {"id": "s1", "cwd": "D:\\int\\tools"}})
                + "\n"
                + json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Implement IntBrain memory import now"}]}})
                + "\n"
            )
            path.write_text(raw, encoding="utf-8")
            first_offset = len(raw.splitlines()[0].encode("utf-8")) + 1
            records = list(iter_jsonl(path, start_offset=first_offset))
            self.assertEqual(len(records), 1)
            self.assertTrue(session_in_scope("D:\\int\\tools", ("D:/int", "/int")))
            self.assertEqual(derive_repo("D:\\int\\tools\\codex"), "tools")

    def test_session_extraction_redacts_secret_and_summarizes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "session.jsonl"
            _write_jsonl(
                path,
                [
                    {"type": "session_meta", "payload": {"id": "s1", "timestamp": "2026-04-14T10:00:00Z", "cwd": "D:\\int\\tools"}},
                    {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Store api_key=super-secret-value from the old session memory without leaking it."}]}},
                    {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Implemented the memory import path and verified that token-like values are redacted before storage."}]}},
                    {"type": "response_item", "payload": {"type": "function_call_output", "output": "Process exited with code 1\nOutput:\nTraceback: sample failure"}},
                ],
            )
            meta = load_session_meta(path)
            self.assertIsNotNone(meta)
            assert meta is not None
            items = extract_items(meta, list(iter_jsonl(path)), scope_roots=("D:/int", "/int"))
            text = "\n".join(item.text_content for item in items)
            self.assertIn("[redacted-secret]", text)
            self.assertNotIn("super-secret-value", text)
            self.assertTrue(any(item.chunk_kind == "summary" for item in items))
            self.assertTrue(all(item.source == "intbrain.memory.session.v1" for item in items))

    def test_recent_work_and_archived_brief(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            codex_home = Path(tmp_dir)
            session_path = codex_home / "archived_sessions" / "rollout-2026-04-14T10-00-00-session-123.jsonl"
            _write_jsonl(
                session_path,
                [
                    {"type": "session_meta", "payload": {"id": "session-123", "timestamp": "2026-04-14T10:00:00Z", "cwd": "D:\\int\\tools"}},
                    {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Find archived memory session and summarize it through IntBrain."}]}},
                    {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Archived session is still available for recall and summary generation across sessions."}]}},
                ],
            )
            memory = IntBrainMemory(codex_home=codex_home, state_path=codex_home / "state.json")
            brief = memory.session_brief(session_id="session-123")
            self.assertIsNotNone(brief)
            assert brief is not None
            self.assertEqual(brief.repo, "tools")

    def test_session_reads_require_explicit_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = IntBrainMemory(state_path=Path(tmp_dir) / "state.json")
            with self.assertRaises(ValueError):
                memory.extract_session_items()
            with self.assertRaises(ValueError):
                memory.recent_work()
            with self.assertRaises(ValueError):
                memory.session_brief(session_id="session-123")

    def test_mempalace_import_counts_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "palace"
            (root / "room").mkdir(parents=True)
            (root / "room" / "drawer.md").write_text("Remember that MemPalace is being merged into IntBrain.", encoding="utf-8")
            memory = IntBrainMemory(codex_home=Path(tmp_dir) / ".codex", state_path=Path(tmp_dir) / "state.json")
            result = memory.import_mempalace(palace_root=root)
            self.assertEqual(result["items_candidate"], 1)
            self.assertEqual(result["items"][0]["source"], "intbrain.memory.mempalace.v1")

    def test_cabinet_inventory_classifies_workspace_and_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "cabinet"
            (root / "data").mkdir(parents=True)
            (root / "server").mkdir(parents=True)
            (root / "node_modules" / "ignored").mkdir(parents=True)
            (root / "README.md").write_text("Cabinet workspace product notes.", encoding="utf-8")
            (root / "data" / "index.md").write_text("Cabinet source-of-truth workspace data.", encoding="utf-8")
            (root / "server" / "cabinet-daemon.ts").write_text("export const daemon = 'runtime metadata';", encoding="utf-8")
            (root / "node_modules" / "ignored" / "package.json").write_text("{}", encoding="utf-8")
            memory = IntBrainMemory(codex_home=Path(tmp_dir) / ".codex", state_path=Path(tmp_dir) / "state.json")
            result = memory.inventory_cabinet(cabinet_root=root)
            sources = {item["source"] for item in result["items"]}
            self.assertIn("intbrain.cabinet.workspace.v1", sources)
            self.assertIn("intbrain.cabinet.runtime.v1", sources)
            self.assertEqual(result["data_roots"]["data"]["files"], 1)
            self.assertNotIn("node_modules", "\n".join(item["source_path"] for item in result["items"]))

    def test_sanitize_redacts_bearer_and_long_blob(self) -> None:
        long_blob = "a" * 90
        text = sanitize_text(f"Authorization: token Bearer abc.def {long_blob}")
        self.assertIn("[redacted-secret]", text)
        self.assertIn("[redacted-blob]", text)


if __name__ == "__main__":
    unittest.main()
