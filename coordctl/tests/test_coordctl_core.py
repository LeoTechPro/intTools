from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import coordctl_core  # noqa: E402


CONTENT = "a\nb\nc\nd\ne\nf\ng\nh\ni\n"


def git(repo: Path, *args: str, input_text: str | None = None) -> str:
    completed = subprocess.run(["git", *args], cwd=repo, input=input_text, text=True, capture_output=True, check=True)
    return completed.stdout.strip()


def commit_content(repo: Path, content: str, message: str, parent: str | None = None) -> str:
    blob = git(repo, "hash-object", "-w", "--stdin", input_text=content)
    git(repo, "update-index", "--add", "--cacheinfo", "100644", blob, "invoice.js")
    tree = git(repo, "write-tree")
    args = ["commit-tree", tree, "-m", message]
    if parent:
        args.extend(["-p", parent])
    return git(repo, *args)


def make_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "--initial-branch=main")
    git(repo, "config", "user.name", "Coord Test")
    git(repo, "config", "user.email", "coord@example.invalid")
    commit = commit_content(repo, CONTENT, "initial")
    git(repo, "reset", "--hard", commit)
    return repo


class CoordCtlCoreTest(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows drive-letter path semantics; backslash is only a separator on Windows")
    def test_resolve_state_dir_uses_env_override(self):
        with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": r"D:\\tmp\\coordctl-state"}, clear=False):
            self.assertEqual(coordctl_core.resolve_state_dir(), Path(r"D:\tmp\coordctl-state").resolve())

    def test_normalize_path_rejects_escape(self):
        repo_root = str(Path(r"D:\int\tools").resolve())
        with self.assertRaises(coordctl_core.CoordCtlError):
            coordctl_core.normalize_path(repo_root, "..\\outside.txt")

    def test_reserved_symbol_region_is_rejected_in_v1(self):
        with self.assertRaises(coordctl_core.CoordCtlError) as ctx:
            coordctl_core.normalize_region("symbol", "calculateInvoice")
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_REGION_KIND")

    def test_session_lifecycle_and_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state"), coordctl_core.RECLAIM_DEAD_LOCAL_PIDS_ENV: ""}, clear=False):
                session = coordctl_core.cmd_session_start(mock.Mock(repo_root=str(repo), owner="agent:a", issue="INT-1", branch="agent/a", base="main", worktree_path=None, lease_sec=60))
                session_id = session["session"]["session_id"]
                status = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None))
                self.assertEqual(status["counts"]["sessions"], 1)
                self.assertTrue(coordctl_core.cmd_heartbeat(mock.Mock(session_id=session_id, lease_sec=60))["ok"])
                self.assertTrue(coordctl_core.cmd_release(mock.Mock(session_id=session_id, repo_root=None, issue=None, lease_id=None, owner=None, path=None))["changed"])
                status_after = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None))
                self.assertEqual(status_after["counts"]["sessions"], 0)

    def test_dead_local_pid_reclaim_is_env_gated(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state"), coordctl_core.RECLAIM_DEAD_LOCAL_PIDS_ENV: ""}, clear=False):
                session = coordctl_core.cmd_session_start(mock.Mock(repo_root=str(repo), owner="agent:a", issue=None, branch="agent/a", base="main", worktree_path=None, lease_sec=60))
                session_id = session["session"]["session_id"]
                coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=session_id))

                with mock.patch.object(coordctl_core, "pid_alive", return_value=False):
                    status = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=False))

                self.assertEqual(status["counts"], {"sessions": 1, "leases": 1})
                self.assertEqual(status["expired_now"], {"sessions": [], "leases": []})

    def test_dead_local_pid_reclaim_expires_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state"), coordctl_core.RECLAIM_DEAD_LOCAL_PIDS_ENV: ""}, clear=False):
                session = coordctl_core.cmd_session_start(mock.Mock(repo_root=str(repo), owner="agent:a", issue=None, branch="agent/a", base="main", worktree_path=None, lease_sec=60))
                session_id = session["session"]["session_id"]
                lease = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=session_id))

                with mock.patch.dict(os.environ, {coordctl_core.RECLAIM_DEAD_LOCAL_PIDS_ENV: "1"}, clear=False), mock.patch.object(coordctl_core, "pid_alive", return_value=False):
                    status = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=False))
                    status_all = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=True))

                self.assertEqual(status["counts"], {"sessions": 0, "leases": 0})
                self.assertIn(session_id, status["expired_now"]["sessions"])
                self.assertIn(lease["lease"]["lease_id"], status["expired_now"]["leases"])
                self.assertEqual(status_all["sessions"][0]["state"], "expired")
                self.assertEqual(status_all["leases"][0]["state"], "expired")

    def test_dead_local_pid_reclaim_keeps_live_process_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                session = coordctl_core.cmd_session_start(mock.Mock(repo_root=str(repo), owner="agent:a", issue=None, branch="agent/a", base="main", worktree_path=None, lease_sec=60))
                session_id = session["session"]["session_id"]
                coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=session_id))

                with mock.patch.dict(os.environ, {coordctl_core.RECLAIM_DEAD_LOCAL_PIDS_ENV: "1"}, clear=False), mock.patch.object(coordctl_core, "pid_alive", return_value=True):
                    status = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=False))

                self.assertEqual(status["counts"], {"sessions": 1, "leases": 1})
                self.assertEqual(status["expired_now"], {"sessions": [], "leases": []})

    def test_non_overlapping_hunks_same_file_are_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                first = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="hunk", region_id="3:3", lease_sec=60, session_id=None))
                second = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:b", issue=None, base="main", region_kind="hunk", region_id="9:9", lease_sec=60, session_id=None))
                self.assertTrue(first["ok"])
                self.assertTrue(second["ok"])

    def test_overlapping_hunks_same_file_record_overlap_warning(self):
        # Supervisory model: the second overlapping intent is still recorded
        # (ok:true); the overlap surfaces as a COORD_OVERLAP warning, not a refusal.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                first = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=None))
                second = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:b", issue=None, base="main", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=None))
                self.assertTrue(first["ok"])
                self.assertTrue(second["ok"])
                self.assertIn("COORD_OVERLAP", {w["code"] for w in second["warnings"]})
                self.assertTrue(second["overlaps"])

    def test_same_owner_same_hunk_renews(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                first = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=None))
                second = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=None))
                self.assertEqual(first["lease"]["lease_id"], second["lease"]["lease_id"])
                self.assertEqual(second["action"], "renewed_existing")

    def test_stale_base_is_rejected_when_base_cannot_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                with self.assertRaises(coordctl_core.CoordCtlError) as ctx:
                    coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="missing-ref", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=None))
                self.assertEqual(ctx.exception.code, "STALE_BASE")

    def test_overlapping_different_base_records_stale_base_observation(self):
        # Different-base overlap is recorded (ok:true) with a STALE_BASE_OBSERVED
        # warning instead of blocking the write.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            parent = git(repo, "rev-parse", "main")
            newer = commit_content(repo, "a\nb\nc\nnew\ne\nf\ng\nh\ni\n", "newer", parent=parent)
            git(repo, "branch", "newer", newer)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                first = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=None))
                second = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:b", issue=None, base="newer", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=None))
                self.assertTrue(first["ok"])
                self.assertTrue(second["ok"])
                self.assertIn("STALE_BASE_OBSERVED", {w["code"] for w in second["warnings"]})

    def test_intent_session_owner_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                session = coordctl_core.cmd_session_start(mock.Mock(repo_root=str(repo), owner="agent:a", issue=None, branch="agent/a", base="main", worktree_path=None, lease_sec=60))
                result = coordctl_core.cmd_intent_acquire(
                    mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:b", issue=None, base="main", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=session["session"]["session_id"])
                )
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"], "SESSION_MISMATCH")

    def test_intent_session_rejects_moved_base_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            old_main = git(repo, "rev-parse", "main")
            newer = commit_content(repo, "a\nb\nc\nnew\ne\nf\ng\nh\ni\n", "newer", parent=old_main)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                session = coordctl_core.cmd_session_start(mock.Mock(repo_root=str(repo), owner="agent:a", issue=None, branch="agent/a", base="main", worktree_path=None, lease_sec=60))
                git(repo, "reset", "--hard", newer)
                result = coordctl_core.cmd_intent_acquire(
                    mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base=old_main, region_kind="hunk", region_id="4:4", lease_sec=60, session_id=session["session"]["session_id"])
                )
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"], "STALE_BASE")
                self.assertEqual(result["current_base_commit"], newer)

    def test_commit_scope_check_allows_fully_staged_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            (repo / "invoice.js").write_text(CONTENT.replace("c", "C"), encoding="utf-8")
            git(repo, "add", "invoice.js")

            result = coordctl_core.cmd_commit_scope_check(mock.Mock(repo_root=str(repo)))

            self.assertTrue(result["ok"])
            self.assertTrue(result["ready_to_commit"])
            self.assertEqual(result["counts"]["staged"], 1)
            self.assertEqual(result["counts"]["unstaged"], 0)
            self.assertEqual(result["counts"]["untracked"], 0)

    def test_commit_scope_check_allows_selected_complete_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            (repo / "invoice.js").write_text(CONTENT.replace("c", "C"), encoding="utf-8")
            git(repo, "add", "invoice.js")
            (repo / "other.txt").write_text("left out\n", encoding="utf-8")

            result = coordctl_core.cmd_commit_scope_check(mock.Mock(repo_root=str(repo)))

            self.assertTrue(result["ok"])
            self.assertTrue(result["ready_to_commit"])
            self.assertFalse(result["owner_action_required"])
            self.assertEqual(result["counts"]["staged"], 1)
            self.assertEqual(result["counts"]["partial_files"], 0)
            self.assertEqual(result["counts"]["untracked"], 1)
            self.assertIn("other.txt", result["paths"]["untracked"])
            self.assertEqual(result["warnings"][0]["code"], "UNCOMMITTED_OWNER_STATE_VISIBLE")

    def test_commit_scope_check_allows_staged_gitlink_with_visible_submodule_dirt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            sub_src = tmp_path / "sub-src"
            sub_src.mkdir()
            git(sub_src, "init", "--initial-branch=main")
            git(sub_src, "config", "user.name", "Coord Test")
            git(sub_src, "config", "user.email", "coord@example.invalid")
            (sub_src / "module.txt").write_text("v1\n", encoding="utf-8")
            git(sub_src, "add", "module.txt")
            git(sub_src, "commit", "-m", "initial")
            git(repo, "-c", "protocol.file.allow=always", "submodule", "add", str(sub_src), "vendor/sub")
            git(repo, "commit", "-am", "add submodule")

            sub = repo / "vendor" / "sub"
            git(sub, "config", "user.name", "Coord Test")
            git(sub, "config", "user.email", "coord@example.invalid")
            (sub / "module.txt").write_text("v2\n", encoding="utf-8")
            git(sub, "add", "module.txt")
            git(sub, "commit", "-m", "advance submodule")
            git(repo, "add", "vendor/sub")
            (sub / "scratch.txt").write_text("left visible\n", encoding="utf-8")

            result = coordctl_core.cmd_commit_scope_check(mock.Mock(repo_root=str(repo)))

            self.assertTrue(result["ok"])
            self.assertTrue(result["ready_to_commit"])
            self.assertFalse(result["owner_action_required"])
            self.assertEqual(result["counts"]["staged"], 1)
            self.assertEqual(result["counts"]["partial_files"], 0)
            self.assertIn("vendor/sub", result["paths"]["staged"])
            self.assertIn("vendor/sub", result["warnings"][0]["paths"])

    def test_commit_scope_check_blocks_staged_gitlink_when_submodule_head_moves_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            sub_src = tmp_path / "sub-src"
            sub_src.mkdir()
            git(sub_src, "init", "--initial-branch=main")
            git(sub_src, "config", "user.name", "Coord Test")
            git(sub_src, "config", "user.email", "coord@example.invalid")
            (sub_src / "module.txt").write_text("v1\n", encoding="utf-8")
            git(sub_src, "add", "module.txt")
            git(sub_src, "commit", "-m", "initial")
            git(repo, "-c", "protocol.file.allow=always", "submodule", "add", str(sub_src), "vendor/sub")
            git(repo, "commit", "-am", "add submodule")

            sub = repo / "vendor" / "sub"
            git(sub, "config", "user.name", "Coord Test")
            git(sub, "config", "user.email", "coord@example.invalid")
            (sub / "module.txt").write_text("v2\n", encoding="utf-8")
            git(sub, "add", "module.txt")
            git(sub, "commit", "-m", "advance submodule")
            git(repo, "add", "vendor/sub")
            (sub / "module.txt").write_text("v3\n", encoding="utf-8")
            git(sub, "add", "module.txt")
            git(sub, "commit", "-m", "advance again")

            result = coordctl_core.cmd_commit_scope_check(mock.Mock(repo_root=str(repo)))

            self.assertFalse(result["ok"])
            self.assertFalse(result["ready_to_commit"])
            self.assertTrue(result["owner_action_required"])
            self.assertEqual(result["error"], "PARTIAL_FILE_STAGED")
            self.assertIn("vendor/sub", result["paths"]["partial_files"])

    def test_commit_scope_check_blocks_partial_file_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            (repo / "invoice.js").write_text(CONTENT.replace("c", "C"), encoding="utf-8")
            git(repo, "add", "invoice.js")
            (repo / "invoice.js").write_text(CONTENT.replace("c", "C").replace("g", "G"), encoding="utf-8")
            (repo / "diagnostics.txt").write_text("left out\n", encoding="utf-8")

            result = coordctl_core.cmd_commit_scope_check(mock.Mock(repo_root=str(repo)))

            self.assertFalse(result["ok"])
            self.assertFalse(result["ready_to_commit"])
            self.assertTrue(result["owner_action_required"])
            self.assertEqual(result["error"], "PARTIAL_FILE_STAGED")
            self.assertEqual(result["counts"]["staged"], 1)
            self.assertEqual(result["counts"]["unstaged"], 1)
            self.assertEqual(result["counts"]["partial_files"], 1)
            self.assertEqual(result["counts"]["untracked"], 1)
            self.assertIn("invoice.js", result["paths"]["partial_files"])
            self.assertIn("diagnostics.txt", result["paths"]["untracked"])

    def test_cleanup_dry_run_does_not_finalize_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                session = coordctl_core.cmd_session_start(mock.Mock(repo_root=str(repo), owner="agent:a", issue=None, branch="agent/a", base="main", worktree_path=None, lease_sec=60))
                session_id = session["session"]["session_id"]
                dry = coordctl_core.cmd_cleanup(mock.Mock(session_id=session_id, final_state="released", delete_worktree=False, delete_branch=False, dry_run=True, apply=False))
                status = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=False))
                self.assertTrue(dry["ok"])
                self.assertEqual(dry["action"], "cleanup_dry_run")
                self.assertEqual(status["counts"]["sessions"], 1)

    def test_cleanup_apply_marks_final_and_releases_leases(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                session = coordctl_core.cmd_session_start(mock.Mock(repo_root=str(repo), owner="agent:a", issue=None, branch="agent/a", base="main", worktree_path=None, lease_sec=60))
                session_id = session["session"]["session_id"]
                coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="hunk", region_id="4:4", lease_sec=60, session_id=session_id))
                applied = coordctl_core.cmd_cleanup(mock.Mock(session_id=session_id, final_state="merged", delete_worktree=False, delete_branch=False, dry_run=False, apply=True))
                status_active = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=False))
                status_all = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=True))
                self.assertTrue(applied["ok"])
                self.assertEqual(applied["session"]["state"], "merged")
                self.assertEqual(status_active["counts"], {"sessions": 0, "leases": 0})
                self.assertEqual(status_all["counts"]["sessions"], 1)

    def test_gc_requires_apply_to_delete_final_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                session = coordctl_core.cmd_session_start(mock.Mock(repo_root=str(repo), owner="agent:a", issue=None, branch="agent/a", base="main", worktree_path=None, lease_sec=60))
                session_id = session["session"]["session_id"]
                coordctl_core.cmd_cleanup(mock.Mock(session_id=session_id, final_state="released", delete_worktree=False, delete_branch=False, dry_run=False, apply=True))
                dry = coordctl_core.cmd_gc(mock.Mock(dry_run=True, apply=False))
                still_there = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=True))
                applied = coordctl_core.cmd_gc(mock.Mock(dry_run=False, apply=True))
                gone = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=True))
                self.assertEqual(dry["action"], "gc_dry_run")
                self.assertEqual(still_there["counts"]["sessions"], 1)
                self.assertEqual(applied["deleted"]["sessions"], 1)
                self.assertEqual(gone["counts"]["sessions"], 0)

    def test_release_by_lease_id_releases_single_orphan_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                acquired = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="file", region_id="invoice.js", lease_sec=60, session_id=None))
                lease_id = acquired["lease"]["lease_id"]
                released = coordctl_core.cmd_release(mock.Mock(session_id=None, repo_root=None, issue=None, lease_id=lease_id, owner=None, path=None))
                self.assertTrue(released["changed"])
                self.assertEqual(len(released["released_leases"]), 1)
                self.assertEqual(released["selector"], {"lease_id": lease_id})
                status = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=False))
                self.assertEqual(status["counts"]["leases"], 0)

    def test_release_by_owner_repo_releases_only_that_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="hunk", region_id="3:3", lease_sec=60, session_id=None))
                coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:b", issue=None, base="main", region_kind="hunk", region_id="9:9", lease_sec=60, session_id=None))
                released = coordctl_core.cmd_release(mock.Mock(session_id=None, repo_root=str(repo), issue=None, lease_id=None, owner="agent:a", path=None))
                self.assertEqual(len(released["released_leases"]), 1)
                self.assertEqual(released["released_leases"][0]["owner_id"], "agent:a")
                left_a = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner="agent:a", issue=None, all=False))
                left_b = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner="agent:b", issue=None, all=False))
                self.assertEqual(left_a["counts"]["leases"], 0)
                self.assertEqual(left_b["counts"]["leases"], 1)

    def test_release_by_owner_without_repo_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                with self.assertRaises(coordctl_core.CoordCtlError) as ctx:
                    coordctl_core.cmd_release(mock.Mock(session_id=None, repo_root=None, issue=None, lease_id=None, owner="agent:a", path=None))
                self.assertEqual(ctx.exception.code, "INVALID_ARGUMENT")

    def test_release_path_without_owner_or_confirmation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="file", region_id="invoice.js", lease_sec=60, session_id=None))
                coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:b", issue=None, base="main", region_kind="file", region_id="invoice.js", lease_sec=60, session_id=None))
                with self.assertRaises(coordctl_core.CoordCtlError) as ctx:
                    coordctl_core.cmd_release(mock.Mock(session_id=None, repo_root=str(repo), issue=None, lease_id=None, owner=None, path="invoice.js", all_owners=False))
                self.assertEqual(ctx.exception.code, "INVALID_ARGUMENT")
                # --all-owners confirms the multi-owner release.
                released = coordctl_core.cmd_release(mock.Mock(session_id=None, repo_root=str(repo), issue=None, lease_id=None, owner=None, path="invoice.js", all_owners=True))
                self.assertEqual(len(released["released_leases"]), 2)

    def test_release_path_with_owner_scopes_to_one_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="file", region_id="invoice.js", lease_sec=60, session_id=None))
                coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:b", issue=None, base="main", region_kind="file", region_id="invoice.js", lease_sec=60, session_id=None))
                released = coordctl_core.cmd_release(mock.Mock(session_id=None, repo_root=str(repo), issue=None, lease_id=None, owner="agent:a", path="invoice.js", all_owners=False))
                self.assertEqual(len(released["released_leases"]), 1)
                self.assertEqual(released["released_leases"][0]["owner_id"], "agent:a")

    def test_release_ambiguous_selector_groups_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                session = coordctl_core.cmd_session_start(mock.Mock(repo_root=str(repo), owner="agent:a", issue=None, branch="agent/a", base="main", worktree_path=None, lease_sec=60))
                with self.assertRaises(coordctl_core.CoordCtlError) as ctx:
                    coordctl_core.cmd_release(mock.Mock(session_id=session["session"]["session_id"], repo_root=str(repo), issue=None, lease_id="x", owner=None, path=None, all_owners=False))
                self.assertEqual(ctx.exception.code, "INVALID_ARGUMENT")

    def test_commit_scope_report_never_hard_fails_on_no_staged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            report = coordctl_core.cmd_commit_scope_report(mock.Mock(repo_root=str(repo)))
            self.assertTrue(report["ok"])
            self.assertFalse(report["ready_to_commit"])
            self.assertIn("NO_STAGED_CHANGES", {o["code"] for o in report["observations"]})

    def test_commit_scope_check_warns_not_fails_on_no_staged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            result = coordctl_core.cmd_commit_scope_check(mock.Mock(repo_root=str(repo)))
            self.assertTrue(result["ok"])
            self.assertFalse(result["ready_to_commit"])
            self.assertIn("NO_STAGED_CHANGES", {w["code"] for w in result["warnings"]})

    def test_commit_scope_check_fails_on_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            (repo / "invoice.js").write_text("a\nb\nc\nSTAGED\ne\nf\ng\nh\ni\n", encoding="utf-8")
            git(repo, "add", "invoice.js")
            (repo / "invoice.js").write_text("a\nb\nc\nSTAGED\ne\nf\ng\nh\nUNSTAGED\n", encoding="utf-8")
            check = coordctl_core.cmd_commit_scope_check(mock.Mock(repo_root=str(repo)))
            report = coordctl_core.cmd_commit_scope_report(mock.Mock(repo_root=str(repo)))
            self.assertFalse(check["ok"])
            self.assertEqual(check["error"], "PARTIAL_FILE_STAGED")
            self.assertTrue(check["owner_action_required"])
            self.assertTrue(report["ok"])  # report never blocks
            self.assertIn("PARTIAL_FILE_STAGED", {o["code"] for o in report["observations"]})

    def test_begin_autodetects_repo_and_records_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                begun = coordctl_core.cmd_begin(mock.Mock(repo_root=str(repo), owner="agent:a", issue=None, branch=None, base=None, path=None, worktree_path=None, lease_sec=60))
                self.assertTrue(begun["ok"])
                self.assertEqual(begun["session"]["state"], "active")
                self.assertEqual(begun["session"]["branch_name"], "main")
                status = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=False))
                self.assertEqual(status["counts"]["sessions"], 1)

    def test_begin_with_path_records_coarse_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                begun = coordctl_core.cmd_begin(mock.Mock(repo_root=str(repo), owner="agent:a", issue=None, branch=None, base=None, path="invoice.js", worktree_path=None, lease_sec=60))
                self.assertTrue(begun["ok"])
                self.assertEqual(begun["intent"]["lease"]["path_rel"], "invoice.js")
                self.assertEqual(begun["overlaps"], [])

    def test_intent_without_session_auto_creates_and_reuses_session(self):
        # Orphan-lease prevention: an intent without --session-id gets attached
        # to an auto-created (or reused same-base) session so heartbeat can renew it.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                first = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="hunk", region_id="3:3", lease_sec=60, session_id=None))
                self.assertIsNotNone(first["lease"]["session_id"])
                second = coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="hunk", region_id="9:9", lease_sec=60, session_id=None))
                # Same owner+repo+base → session is reused, not duplicated.
                self.assertEqual(first["lease"]["session_id"], second["lease"]["session_id"])
                status = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=False))
                self.assertEqual(status["counts"]["sessions"], 1)

    def test_status_brief_returns_compact_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                coordctl_core.cmd_intent_acquire(mock.Mock(repo_root=str(repo), path="invoice.js", owner="agent:a", issue=None, base="main", region_kind="file", region_id="invoice.js", lease_sec=60, session_id=None))
                brief = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=False, brief=True))
                self.assertTrue(brief["ok"])
                self.assertNotIn("leases", brief)
                self.assertNotIn("sessions", brief)
                self.assertEqual(brief["active"]["paths"], ["invoice.js"])
                self.assertIn("agent:a", brief["active"]["owners"])
                self.assertEqual(brief["counts"]["active_leases"], 1)

    def test_gc_rotate_events_archives_journal_and_preserves_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = make_repo(tmp_path)
            with mock.patch.dict(os.environ, {"COORDCTL_STATE_DIR": str(tmp_path / "state")}, clear=False):
                coordctl_core.cmd_session_start(mock.Mock(repo_root=str(repo), owner="agent:a", issue=None, branch="agent/a", base="main", worktree_path=None, lease_sec=60))
                events = coordctl_core.events_path()
                self.assertTrue(events.exists() and events.stat().st_size > 0)
                dry = coordctl_core.cmd_gc(mock.Mock(dry_run=True, apply=False, rotate_events=True))
                self.assertFalse(dry["events_rotation"]["rotated"])
                self.assertGreater(dry["events_rotation"]["bytes"], 0)
                self.assertTrue(events.exists())  # dry-run must not move it
                applied = coordctl_core.cmd_gc(mock.Mock(dry_run=False, apply=True, rotate_events=True))
                self.assertTrue(applied["events_rotation"]["rotated"])
                archive_dir = coordctl_core.resolve_state_dir() / "archive"
                self.assertTrue(any(archive_dir.glob("events-*.jsonl")))
                # coord_events (permanent audit) is preserved: status still works.
                status = coordctl_core.cmd_status(mock.Mock(repo_root=str(repo), path=None, owner=None, issue=None, all=True))
                self.assertTrue(status["ok"])


if __name__ == "__main__":
    unittest.main()
