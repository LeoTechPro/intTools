from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_DIR = Path(__file__).resolve().parents[1]
TOOLS_ROOT = MODULE_DIR.parent
LOCKCTL_DIR = TOOLS_ROOT / "lockctl"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import coordctl_core  # noqa: E402


BASE = "a\nb\nc\nd\ne\nf\ng\nh\ni\n"
TAX = "a\nb\nTAX\nd\ne\nf\ng\nh\ni\n"
FORMAT = "a\nb\nc\nd\ne\nf\ng\nh\nFORMAT\n"
THRESHOLD = "a\nb\nc\nTHRESHOLD\ne\nf\ng\nh\ni\n"
RATE = "a\nb\nc\nRATE\ne\nf\ng\nh\ni\n"


def git(repo: Path, *args: str, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, input=input_text, text=True, capture_output=True, check=check)


def git_out(repo: Path, *args: str, input_text: str | None = None) -> str:
    return git(repo, *args, input_text=input_text).stdout.strip()


def commit_content(repo: Path, content: str, message: str, parent: str | None = None) -> str:
    blob = git_out(repo, "hash-object", "-w", "--stdin", input_text=content)
    git_out(repo, "update-index", "--add", "--cacheinfo", "100644", blob, "invoice.js")
    tree = git_out(repo, "write-tree")
    args = ["commit-tree", tree, "-m", message]
    if parent:
        args.extend(["-p", parent])
    return git_out(repo, *args)


def make_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    git_out(repo, "init", "--initial-branch=main")
    git_out(repo, "config", "user.name", "Coord Integration")
    git_out(repo, "config", "user.email", "coord@example.invalid")
    initial = commit_content(repo, BASE, "initial")
    git_out(repo, "reset", "--hard", initial)
    return repo


def branch_with_content(repo: Path, branch: str, content: str) -> None:
    parent = git_out(repo, "rev-parse", "main")
    commit = commit_content(repo, content, branch, parent=parent)
    git_out(repo, "branch", branch, commit)
    git_out(repo, "reset", "--hard", "main")


class CoordCtlIntegrationTest(unittest.TestCase):
    def test_non_overlapping_same_file_edits_are_allowed_and_merge_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            branch_with_content(repo, "agent-a", TAX)
            branch_with_content(repo, "agent-b", FORMAT)

            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "coord-state")}, clear=False):
                first = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="hunk", region_id="3:3", lease_sec=60, session_id=None))
                second = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:b", issue=None, base="main", region_kind="hunk", region_id="9:9", lease_sec=60, session_id=None))
                dry = coordctl_core.cmd_merge_dry_run(mock.Mock(repo_root=str(repo), target="agent-a", branch="agent-b"))

            self.assertTrue(first["ok"])
            self.assertTrue(second["ok"])
            self.assertTrue(dry["clean"])
            git(repo, "merge", "--no-edit", "agent-a")
            merge_b = git(repo, "merge", "--no-edit", "agent-b", check=False)
            self.assertEqual(merge_b.returncode, 0, merge_b.stderr)

    def test_overlapping_same_file_edits_are_blocked_before_git_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            branch_with_content(repo, "agent-c", THRESHOLD)
            branch_with_content(repo, "agent-d", RATE)

            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "coord-state")}, clear=False):
                first = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:c", issue=None, base="main", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=None))
                second = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:d", issue=None, base="main", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=None))
                dry = coordctl_core.cmd_merge_dry_run(mock.Mock(repo_root=str(repo), target="agent-c", branch="agent-d"))

            self.assertTrue(first["ok"])
            self.assertFalse(second["ok"])
            self.assertEqual(second["error"], "COORD_CONFLICT")
            self.assertFalse(dry["clean"])
            git(repo, "merge", "--no-edit", "agent-c")
            merge_d = git(repo, "merge", "--no-edit", "agent-d", check=False)
            self.assertNotEqual(merge_d.returncode, 0)
            git(repo, "merge", "--abort", check=False)

    def test_legacy_lockctl_blocks_whole_file_where_coordctl_allows_non_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            lock_state = tmp_path / "lock-state"
            env = {**os.environ, "LOCKCTL_STATE_DIR": str(lock_state)}
            first_cp = subprocess.run(
                [sys.executable, str(LOCKCTL_DIR / "lockctl.py"), "acquire", "--repo-root", str(repo), "--path", "invoice.js", "--owner", "agent:a", "--lease-sec", "60", "--format", "json"],
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )
            second_cp = subprocess.run(
                [sys.executable, str(LOCKCTL_DIR / "lockctl.py"), "acquire", "--repo-root", str(repo), "--path", "invoice.js", "--owner", "agent:b", "--lease-sec", "60", "--format", "json"],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            import json

            first = json.loads(first_cp.stdout)
            second = json.loads(second_cp.stdout)

            self.assertTrue(first["ok"])
            self.assertFalse(second["ok"])
            self.assertEqual(second["error"], "LOCK_CONFLICT")

    def test_cleanup_apply_refuses_unmerged_branch_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            branch_with_content(repo, "agent-cleanup", TAX)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "coord-state")}, clear=False):
                session = coordctl_core.cmd_session_start(
                    mock.Mock(repo_root=str(repo), owner="agent:a", issue=None, branch="agent-cleanup", base="main", worktree_path=None, lease_sec=60)
                )
                result = coordctl_core.cmd_cleanup(
                    mock.Mock(session_id=session["session"]["session_id"], final_state="merged", delete_worktree=False, delete_branch=True, dry_run=False, apply=True)
                )
                status = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=True))

            self.assertFalse(result["ok"])
            self.assertEqual(result["session"]["state"], "failed-cleanup")
            self.assertIn("agent-cleanup", git_out(repo, "branch", "--list", "agent-cleanup"))
            self.assertEqual(status["sessions"][0]["cleanup_status"], "failed")


if __name__ == "__main__":
    unittest.main()
