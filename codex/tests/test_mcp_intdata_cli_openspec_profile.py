import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "bin" / "mcp-intdata-cli.py"
SPEC = importlib.util.spec_from_file_location("mcp_intdata_cli_openspec_profile", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OpenSpecProfileTest(unittest.TestCase):
    def test_new_schema_requires_delta_or_full(self) -> None:
        schema = next(
            tool["inputSchema"] for tool in MODULE.OPEN_SPEC_TOOLS if tool["name"] == "openspec_new"
        )
        self.assertIn("spec_level", schema["required"])
        self.assertEqual(["delta", "full"], schema["properties"]["spec_level"]["enum"])

    def test_none_is_rejected_for_mutation(self) -> None:
        with self.assertRaisesRegex(ValueError, "none"):
            MODULE._require_spec_level({"spec_level": "none"})

    def test_change_name_must_match_issue_context(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not match"):
            MODULE._new_change_name(
                {
                    "issue_context": "#801",
                    "args": ["change", "issue-802-risk-based-openspec"],
                }
            )

    def test_delta_profile_accepts_proposal_and_spec_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            change = root / "openspec" / "changes" / "issue-801-delta"
            (change / "specs" / "process").mkdir(parents=True)
            (change / "proposal.md").write_text(
                "https://github.com/LeoTechPro/int/issues/801\n", encoding="utf-8"
            )
            (change / "specs" / "process" / "spec.md").write_text(
                "## ADDED Requirements\n", encoding="utf-8"
            )
            self.assertEqual([], MODULE._openspec_profile_errors(root, change.name, "delta"))

    def test_delta_profile_rejects_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            change = root / "openspec" / "changes" / "issue-801-delta"
            (change / "specs" / "process").mkdir(parents=True)
            (change / "proposal.md").write_text(
                "https://github.com/LeoTechPro/int/issues/801\n", encoding="utf-8"
            )
            (change / "specs" / "process" / "spec.md").write_text("spec\n", encoding="utf-8")
            (change / "tasks.md").write_text("tasks\n", encoding="utf-8")
            self.assertIn(
                "delta profile forbids tasks.md",
                MODULE._openspec_profile_errors(root, change.name, "delta"),
            )

    def test_full_profile_requires_rollback_or_migration_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            change = root / "openspec" / "changes" / "issue-801-full"
            (change / "specs" / "process").mkdir(parents=True)
            (change / "proposal.md").write_text(
                "https://github.com/LeoTechPro/int/issues/801\n", encoding="utf-8"
            )
            (change / "specs" / "process" / "spec.md").write_text("spec\n", encoding="utf-8")
            (change / "design.md").write_text("# Design\n", encoding="utf-8")
            (change / "tasks.md").write_text("tasks\n", encoding="utf-8")
            self.assertIn(
                "full profile design.md requires a Rollback or Migration Plan section",
                MODULE._openspec_profile_errors(root, change.name, "full"),
            )

    def test_validate_keeps_legacy_mode_without_profile(self) -> None:
        with mock.patch.object(MODULE, "_openspec_base", return_value=["openspec"]), mock.patch.object(
            MODULE, "_run", return_value={"ok": True, "returncode": 0}
        ) as run:
            result = MODULE._call_openspec(
                "openspec_validate",
                {
                    "cwd": str(MODULE.ROOT_DIR),
                    "item": "legacy-change",
                    "strict": True,
                },
            )
        self.assertTrue(result["ok"])
        self.assertNotIn("profile_errors", result)
        run.assert_called_once_with(
            ["openspec", "validate", "--strict", "legacy-change"],
            cwd=str(MODULE.ROOT_DIR),
            timeout_sec=None,
        )

    def test_new_removes_generated_readme(self) -> None:
        with mock.patch.object(MODULE, "_openspec_base", return_value=["openspec"]), mock.patch.object(
            MODULE, "_run", return_value={"ok": True, "returncode": 0}
        ), mock.patch.object(MODULE, "_remove_scaffold_readme") as remove:
            result = MODULE._call_openspec(
                "openspec_new",
                {
                    "cwd": str(MODULE.ROOT_DIR),
                    "confirm_mutation": True,
                    "issue_context": "#801",
                    "spec_level": "full",
                    "args": ["change", "issue-801-risk-based-openspec"],
                },
            )
        self.assertTrue(result["ok"])
        remove.assert_called_once_with(
            str(MODULE.ROOT_DIR),
            "issue-801-risk-based-openspec",
        )


if __name__ == "__main__":
    unittest.main()
