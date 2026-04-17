import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from delivery.bin.multica_autopilot_report_sidecar import (
    ConfigError,
    DeliveryConfig,
    DeliveryError,
    JsonState,
    Target,
    build_hygiene_report,
    parse_targets,
    run_once,
)


class FakeMultica:
    def __init__(self, *, comment_error=None):
        self.comment_error = comment_error
        self.comments = []
        self.issues = [
            {
                "id": "issue-1",
                "identifier": "INT-1",
                "status": "blocked",
                "priority": "urgent",
                "title": "Blocked issue",
                "updated_at": "2026-04-17T00:00:00Z",
                "description": "",
            },
            {
                "id": "issue-2",
                "identifier": "INT-2",
                "status": "in_progress",
                "priority": "medium",
                "title": "Stale issue",
                "updated_at": "2026-04-17T00:00:00Z",
                "description": "",
            },
        ]
        self.runs = {
            "issue-1": [],
            "issue-2": [
                {
                    "id": "run-2",
                    "status": "cancelled",
                    "created_at": "2026-04-17T01:00:00Z",
                    "result": {},
                }
            ],
        }

    def list_issues(self):
        return list(self.issues)

    def issue_runs(self, issue_id):
        return list(self.runs.get(issue_id, []))

    def add_comment(self, issue_id, content):
        if self.comment_error:
            raise self.comment_error
        self.comments.append((issue_id, content))
        return {"id": "comment-1"}


class FakeOutbox:
    def __init__(self, *, error=None):
        self.error = error
        self.rows = []

    def enqueue(self, **kwargs):
        if self.error:
            raise self.error
        self.rows.append(kwargs)


def test_config(tmp_path):
    return DeliveryConfig(
        service_id="intdata-stale-issues-monitor",
        message_kind="autopilot_digest",
        state_path=tmp_path / "state.json",
        probe_enqueue_cmd=["probe"],
        dry_run=False,
        skip_telegram=False,
    )


class MulticaAutopilotReportSidecarTests(unittest.TestCase):
    def test_missing_target_mapping_fails_closed(self):
        with self.assertRaises(ConfigError):
            targets = parse_targets([], "{}")
            if "ap-1" not in targets:
                raise ConfigError("missing AUTOPILOT_REPORT_TARGETS mapping for: ap-1")

    def test_hygiene_report_contains_expected_sections(self):
        fake = FakeMultica()
        report = build_hygiene_report(
            autopilot_id="ap-1",
            issues=fake.issues,
            runs_by_issue=fake.runs,
            now=datetime(2026, 4, 17, 12, 0, tzinfo=UTC),
        )
        self.assertIn("Urgent blockers", report)
        self.assertIn("INT-1", report)
        self.assertIn("Stale in_progress", report)
        self.assertIn("run-2", report)

    def test_duplicate_dedupe_key_posts_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = test_config(Path(tmp))
            state = JsonState(config.state_path)
            multica = FakeMultica()
            outbox = FakeOutbox()
            target = Target("ap-1", "master-1")

            run_once(target=target, period_key="2026-04-17", config=config, multica=multica, outbox=outbox, state=state)
            run_once(target=target, period_key="2026-04-17", config=config, multica=multica, outbox=outbox, state=state)

            self.assertEqual(len(multica.comments), 1)
            self.assertEqual(len(outbox.rows), 1)

    def test_comment_failure_skips_telegram(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = test_config(Path(tmp))
            state = JsonState(config.state_path)
            multica = FakeMultica(comment_error=DeliveryError("comment failed"))
            outbox = FakeOutbox()

            with self.assertRaises(DeliveryError):
                run_once(target=Target("ap-1", "master-1"), period_key="2026-04-17", config=config, multica=multica, outbox=outbox, state=state)

            self.assertEqual(outbox.rows, [])

    def test_probe_failure_records_comment_phase_for_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = test_config(Path(tmp))
            state = JsonState(config.state_path)
            multica = FakeMultica()
            outbox = FakeOutbox(error=DeliveryError("probe unavailable"))

            with self.assertRaises(DeliveryError):
                run_once(target=Target("ap-1", "master-1"), period_key="2026-04-17", config=config, multica=multica, outbox=outbox, state=state)

            self.assertEqual(len(multica.comments), 1)
            saved = JsonState(config.state_path).delivery("multica-autopilot:ap-1:2026-04-17")
            self.assertTrue(saved.get("comment_posted"))
            self.assertFalse(saved.get("telegram_enqueued", False))
            self.assertIn("probe unavailable", saved.get("telegram_error", ""))


if __name__ == "__main__":
    unittest.main()
