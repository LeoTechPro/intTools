import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "legacy_assess_sync.py"
SPEC = importlib.util.spec_from_file_location("legacy_assess_sync", MODULE_PATH)
legacy_assess_sync = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = legacy_assess_sync
SPEC.loader.exec_module(legacy_assess_sync)


class LegacyAssessSyncUnitTests(unittest.TestCase):
    def test_fingerprint_is_stable_for_same_payload_with_different_key_order(self):
        row_a = {
            "legacy_client_id": 11366,
            "diagnostic_id": 13,
            "result_at": datetime(2026, 3, 30, 15, 15, tzinfo=UTC),
            "payload": {"b": 2, "a": 1, "nested": {"y": 2, "x": 1}},
            "open_answer": "value",
        }
        row_b = {
            "legacy_client_id": 11366,
            "diagnostic_id": 13,
            "result_at": datetime(2026, 3, 30, 15, 15, tzinfo=UTC),
            "payload": {"nested": {"x": 1, "y": 2}, "a": 1, "b": 2},
            "open_answer": "value",
        }
        self.assertEqual(
            legacy_assess_sync.build_result_fingerprint(row_a),
            legacy_assess_sync.build_result_fingerprint(row_b),
        )

    def test_result_identity_stays_stable_when_payload_changes(self):
        row = {
            "legacy_client_id": 11366,
            "diagnostic_id": 13,
            "result_at": datetime(2026, 3, 30, 15, 15, tzinfo=UTC),
        }
        identity_a = legacy_assess_sync.result_identity_token(row)
        id_a = legacy_assess_sync.stable_uuid(legacy_assess_sync.RESULT_ID_NAMESPACE, identity_a)
        row_with_changed_payload = dict(row, payload={"different": True})
        identity_b = legacy_assess_sync.result_identity_token(row_with_changed_payload)
        id_b = legacy_assess_sync.stable_uuid(legacy_assess_sync.RESULT_ID_NAMESPACE, identity_b)
        self.assertEqual(identity_a, identity_b)
        self.assertEqual(id_a, id_b)

    def test_compute_since_uses_overlap_and_honors_override(self):
        stored = datetime(2026, 4, 9, 10, 0, tzinfo=UTC)
        override = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
        self.assertEqual(
            legacy_assess_sync.compute_since(stored=stored, override=None, overlap_minutes=5),
            stored - timedelta(minutes=5),
        )
        self.assertEqual(
            legacy_assess_sync.compute_since(stored=stored, override=override, overlap_minutes=5),
            override,
        )

    def test_state_store_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            store = legacy_assess_sync.StateStore(path)
            state = legacy_assess_sync.RunState()
            state.streams["results"].last_success_at = "2026-04-09T10:00:00Z"
            state.meta["source_alias_checksum"] = "abc"
            store.save(state)
            loaded = store.load()
            self.assertEqual(loaded.streams["results"].last_success_at, "2026-04-09T10:00:00Z")
            self.assertEqual(loaded.meta["source_alias_checksum"], "abc")

    def test_merge_person_metadata_preserves_target_only_fields(self):
        existing = {
            "custom_flag": True,
            "legacy_punktb": {
                "legacy_id": "old",
                "other": "keep",
            },
        }
        merged = legacy_assess_sync.merge_person_metadata(
            existing,
            legacy_id="11366",
            synced_at=datetime(2026, 4, 9, 10, 0, tzinfo=UTC),
            source_updated_at=datetime(2026, 4, 9, 9, 30, tzinfo=UTC),
        )
        self.assertTrue(merged["custom_flag"])
        self.assertEqual(merged["legacy_punktb"]["legacy_id"], "11366")
        self.assertEqual(merged["legacy_punktb"]["other"], "keep")

    def test_comparable_metadata_ignores_synced_at(self):
        left = {"legacy_punktb": {"legacy_id": "11366", "synced_at": "2026-04-09T10:00:00Z"}}
        right = {"legacy_punktb": {"legacy_id": "11366", "synced_at": "2026-04-09T11:00:00Z"}}
        self.assertEqual(
            legacy_assess_sync.comparable_person_metadata(left),
            legacy_assess_sync.comparable_person_metadata(right),
        )

    def test_comparable_result_payload_ignores_synced_at(self):
        left = {"score": 1, "_import": {"legacy_punktb": {"fingerprint": "x", "synced_at": "2026-04-09T10:00:00Z"}}}
        right = {"score": 1, "_import": {"legacy_punktb": {"fingerprint": "x", "synced_at": "2026-04-09T11:00:00Z"}}}
        self.assertEqual(
            legacy_assess_sync.comparable_result_payload(left),
            legacy_assess_sync.comparable_result_payload(right),
        )

    def test_source_sql_guard_rejects_mutation_tokens(self):
        with self.assertRaises(ValueError):
            legacy_assess_sync.assert_source_query_read_only("DELETE FROM public.clients", "clients")

    def test_report_is_json_serializable(self):
        stats = legacy_assess_sync.StreamStats(source_rows=1, created=1, next_watermark="2026-04-09T10:00:00Z")
        report = legacy_assess_sync.build_report(
            args=type("Args", (), {"dry_run": True, "entity": "all", "state_file": "x"})(),
            run_state=legacy_assess_sync.RunState(),
            results={"clients": stats},
            synced_at=datetime(2026, 4, 9, 10, 0, tzinfo=UTC),
        )
        json.dumps(report, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
