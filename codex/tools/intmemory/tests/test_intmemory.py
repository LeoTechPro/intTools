from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from intmemory.config import IntMemoryConfig
from intmemory.extractor import derive_repo, extract_items, session_in_scope
from intmemory.parser import iter_jsonl, load_session_meta
from intmemory.service import IntMemoryService


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines), encoding="utf-8")


class FakeClient:
    def __init__(self) -> None:
        self.stored: list[dict] = []
        self.search_payloads: list[dict] = []

    def store_context(self, payload: dict) -> dict:
        self.stored.append(payload)
        return {"ok": True}

    def retrieve_context(self, payload: dict) -> dict:
        self.search_payloads.append(payload)
        return {
            "items": [
                {
                    "id": 1,
                    "title": "Assistant outcome: Fixed sync issue",
                    "text_content": "Fixed sync issue and verified state file handling.",
                    "source_path": "C:/Users/intData/.codex/sessions/2026/04/14/rollout-2026-04-14T10-00-00-session.jsonl",
                    "source_hash": "abc",
                    "chunk_kind": "summary",
                    "tags": ["codex", "intmemory", "repo:tools", "session:test"],
                    "rank": 0.9,
                }
            ]
        }


class IntMemoryTests(unittest.TestCase):
    def test_iter_jsonl_respects_offset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "session.jsonl"
            raw = (
                json.dumps({"type": "session_meta", "payload": {"id": "s1", "cwd": "D:\\int\\tools"}})
                + "\n"
                + json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Implement sync worker"}]}})
                + "\n"
            )
            path.write_text(raw, encoding="utf-8")
            first_offset = len(raw.splitlines()[0].encode("utf-8")) + 1
            records = list(iter_jsonl(path, start_offset=first_offset))
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].data["payload"]["role"], "user")

    def test_scope_and_repo_detection(self) -> None:
        self.assertTrue(session_in_scope("D:\\int\\brain", ("D:\\int", "/int")))
        self.assertFalse(session_in_scope("D:\\work", ("D:\\int", "/int")))
        self.assertEqual(derive_repo("D:\\int\\tools\\codex"), "tools")

    def test_extractor_ignores_environment_wrapper_and_keeps_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "session.jsonl"
            lines = [
                {"type": "session_meta", "payload": {"id": "s1", "timestamp": "2026-04-14T10:00:00Z", "cwd": "D:\\int\\tools"}},
                {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "<environment_context>\n  <cwd>D:\\int\\tools</cwd>\n</environment_context>"}]}},
                {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Implement intMemory sync for Codex sessions and store summaries in IntBrain."}]}},
                {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Implemented the sync worker, added dedup state, and verified that repeated runs produce zero duplicate inserts."}]}},
                {"type": "response_item", "payload": {"type": "function_call_output", "output": "Process exited with code 1\nOutput:\nTraceback: sample failure"}},
            ]
            _write_jsonl(path, lines)
            meta = load_session_meta(path)
            self.assertIsNotNone(meta)
            items = extract_items(meta, list(iter_jsonl(path)), scope_roots=("D:\\int", "/int"))
            self.assertTrue(any(item.kind == "task" for item in items))
            self.assertTrue(any(item.chunk_kind == "agent_note" for item in items))
            self.assertTrue(any(item.chunk_kind == "summary" for item in items))

    def test_extractor_drops_noisy_success_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "session.jsonl"
            lines = [
                {"type": "session_meta", "payload": {"id": "s1", "timestamp": "2026-04-14T10:00:00Z", "cwd": "D:\\int\\tools"}},
                {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Implement intMemory sync for Codex sessions and store summaries in IntBrain."}]}},
                {"type": "response_item", "payload": {"type": "function_call_output", "output": "Process exited with code 0\nOutput:\nTotal output lines: 228\n# AGENTS\nVery long policy dump that should not be kept in memory because it carries no operational signal."}},
            ]
            _write_jsonl(path, lines)
            meta = load_session_meta(path)
            self.assertIsNotNone(meta)
            items = extract_items(meta, list(iter_jsonl(path)), scope_roots=("D:\\int", "/int"))
            self.assertFalse(any(item.chunk_kind == "agent_note" for item in items))

    def test_session_brief_reads_real_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            codex_home = Path(tmp_dir)
            session_path = codex_home / "sessions" / "2026" / "04" / "14" / "rollout-2026-04-14T10-00-00-session-123.jsonl"
            _write_jsonl(
                session_path,
                [
                    {"type": "session_meta", "payload": {"id": "session-123", "timestamp": "2026-04-14T10:00:00Z", "cwd": "D:\\int\\tools"}},
                    {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Implement intMemory for codex sessions with IntBrain sync."}]}},
                    {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Implemented parser and sync path. Verified incremental offsets and dedup with recent work summaries."}]}},
                ],
            )
            config = IntMemoryConfig(
                owner_id=1,
                api_base_url="http://example/api/core/v1",
                agent_id="codex",
                agent_key="secret",
                api_timeout_sec=5,
                codex_home=codex_home,
                state_path=codex_home / "memories" / "intmemory" / "state.json",
                scope_roots=("D:\\int", "/int"),
            )
            service = IntMemoryService(config)
            brief = service.session_brief(session_id="session-123")
            self.assertIsNotNone(brief)
            assert brief is not None
            self.assertEqual(brief.repo, "tools")
            self.assertIn("Implement intMemory", brief.user_goal or "")

    def test_sync_dedup_prevents_repeat_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            codex_home = Path(tmp_dir)
            session_path = codex_home / "sessions" / "2026" / "04" / "14" / "rollout-2026-04-14T10-00-00-session-123.jsonl"
            _write_jsonl(
                session_path,
                [
                    {"type": "session_meta", "payload": {"id": "session-123", "timestamp": "2026-04-14T10:00:00Z", "cwd": "D:\\int\\tools"}},
                    {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Implement intMemory for codex sessions with IntBrain sync."}]}},
                    {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Implemented parser and sync path. Verified incremental offsets and dedup with recent work summaries."}]}},
                ],
            )
            config = IntMemoryConfig(
                owner_id=1,
                api_base_url="http://example/api/core/v1",
                agent_id="codex",
                agent_key="secret",
                api_timeout_sec=5,
                codex_home=codex_home,
                state_path=codex_home / "memories" / "intmemory" / "state.json",
                scope_roots=("D:\\int", "/int"),
            )
            service = IntMemoryService(config)
            fake_client = FakeClient()
            service.client = fake_client
            first = service.sync(incremental=True, dry_run=False)
            second = service.sync(incremental=True, dry_run=False)
            self.assertGreater(first["items_stored"], 0)
            self.assertEqual(second["items_stored"], 0)
            self.assertEqual(len(fake_client.stored), first["items_stored"])

    def test_search_filters_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            codex_home = Path(tmp_dir)
            config = IntMemoryConfig(
                owner_id=1,
                api_base_url="http://example/api/core/v1",
                agent_id="codex",
                agent_key="secret",
                api_timeout_sec=5,
                codex_home=codex_home,
                state_path=codex_home / "memories" / "intmemory" / "state.json",
                scope_roots=("D:\\int", "/int"),
            )
            service = IntMemoryService(config)
            fake_client = FakeClient()
            service.client = fake_client
            result = service.search(query="sync", limit=5, repo="tools")
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["items"][0]["repo"], "tools")


if __name__ == "__main__":
    unittest.main()
