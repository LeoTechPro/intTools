#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "codex" / "int_git_sync_gate.py"


def remove_tree_force(path: Path) -> None:
    def onerror(func, target, exc_info):  # type: ignore[no-untyped-def]
        target_path = Path(target)
        os.chmod(target_path, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onerror=onerror)


def run_checked(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True)
    return completed.stdout.strip()


def git(repo: Path, *args: str, capture: bool = False) -> str:
    command = ["git", "-C", str(repo), *args]
    if capture:
        return run_checked(command, cwd=repo)
    run_checked(command, cwd=repo)
    return ""


class IntGitSyncGateTest(unittest.TestCase):
    maxDiff = None

    def _bootstrap_remote_and_local(self) -> tuple[Path, Path, Path]:
        temp_root = Path(tempfile.mkdtemp(prefix="sync_gate_test_"))
        self.addCleanup(remove_tree_force, temp_root)
        remote = temp_root / "remote.git"
        local = temp_root / "local"
        peer = temp_root / "peer"
        git(remote.parent, "init", "--bare", str(remote))
        git(temp_root, "clone", str(remote), str(local))
        git(local, "config", "user.name", "Codex Test")
        git(local, "config", "user.email", "codex@example.com")
        (local / "README.md").write_text("base\n", encoding="utf-8")
        git(local, "add", "README.md")
        git(local, "commit", "-m", "base")
        git(local, "push", "-u", "origin", "HEAD:main")
        git(local, "branch", "--set-upstream-to", "origin/main", "master")
        git(temp_root, "clone", str(remote), str(peer))
        git(peer, "config", "user.name", "Codex Peer")
        git(peer, "config", "user.email", "peer@example.com")
        git(peer, "checkout", "main")
        return remote, local, peer

    def _run_gate(self, cwd: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                shutil.which("python3") or shutil.which("python") or "python3",
                str(SCRIPT_PATH),
                *extra_args,
                "--json",
            ],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )

    def test_default_scope_targets_current_repo_only(self) -> None:
        _remote, local, _peer = self._bootstrap_remote_and_local()
        completed = self._run_gate(local, "--stage", "start", "--dry-run")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(Path(payload["repo"]).resolve(), local.resolve())

    def test_all_repos_scans_root_path(self) -> None:
        temp_root = Path(tempfile.mkdtemp(prefix="sync_gate_root_"))
        self.addCleanup(remove_tree_force, temp_root)
        repo_a = temp_root / "repo-a"
        repo_b = temp_root / "repo-b"
        for index, repo in enumerate((repo_a, repo_b), start=1):
            remote = temp_root / f"remote-{index}.git"
            git(temp_root, "init", "--bare", str(remote))
            git(temp_root, "clone", str(remote), str(repo))
            git(repo, "config", "user.name", "Codex Test")
            git(repo, "config", "user.email", "codex@example.com")
            (repo / "README.md").write_text(f"base {index}\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-m", f"base-{index}")
            git(repo, "push", "-u", "origin", "HEAD:main")
            git(repo, "branch", "--set-upstream-to", "origin/main", "master")

        completed = self._run_gate(repo_a, "--stage", "start", "--dry-run", "--all-repos", "--root-path", str(temp_root))
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(len(payload), 2)

    def test_start_blocks_dirty_tree(self) -> None:
        _remote, local, _peer = self._bootstrap_remote_and_local()
        (local / "README.md").write_text("dirty\n", encoding="utf-8")

        completed = self._run_gate(local, "--stage", "start")

        self.assertEqual(completed.returncode, 20, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("working tree is not clean", payload["error"])

    def test_start_blocks_ahead_branch(self) -> None:
        _remote, local, _peer = self._bootstrap_remote_and_local()
        (local / "README.md").write_text("ahead\n", encoding="utf-8")
        git(local, "add", "README.md")
        git(local, "commit", "-m", "ahead")

        completed = self._run_gate(local, "--stage", "start")

        self.assertEqual(completed.returncode, 20, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("unpushed commits detected", payload["error"])

    def test_start_fast_forwards_when_behind(self) -> None:
        _remote, local, peer = self._bootstrap_remote_and_local()
        git(peer, "checkout", "main")
        (peer / "README.md").write_text("peer\n", encoding="utf-8")
        git(peer, "add", "README.md")
        git(peer, "commit", "-m", "peer")
        peer_head = git(peer, "rev-parse", "HEAD", capture=True)
        git(peer, "push", "origin", "main")

        completed = self._run_gate(local, "--stage", "start")

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("git pull --ff-only origin main", payload["actions"])
        self.assertEqual(git(local, "rev-parse", "HEAD", capture=True), peer_head)

    def test_start_blocks_divergence_without_rewriting_head(self) -> None:
        _remote, local, peer = self._bootstrap_remote_and_local()
        (local / "README.md").write_text("local\n", encoding="utf-8")
        git(local, "add", "README.md")
        git(local, "commit", "-m", "local")
        local_head = git(local, "rev-parse", "HEAD", capture=True)
        git(peer, "checkout", "main")
        (peer / "README.md").write_text("peer\n", encoding="utf-8")
        git(peer, "add", "README.md")
        git(peer, "commit", "-m", "peer")
        git(peer, "push", "origin", "main")

        completed = self._run_gate(local, "--stage", "start")

        self.assertEqual(completed.returncode, 20, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("unpushed commits detected", payload["error"])
        self.assertEqual(git(local, "rev-parse", "HEAD", capture=True), local_head)

    def test_finish_blocks_when_behind(self) -> None:
        _remote, local, peer = self._bootstrap_remote_and_local()
        git(peer, "checkout", "main")
        (peer / "README.md").write_text("peer\n", encoding="utf-8")
        git(peer, "add", "README.md")
        git(peer, "commit", "-m", "peer")
        git(peer, "push", "origin", "main")

        completed = self._run_gate(local, "--stage", "finish", "--push")

        self.assertEqual(completed.returncode, 20, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("branch is behind upstream", payload["error"])

    def test_finish_pushes_ahead_and_verifies_with_post_push_fetch(self) -> None:
        remote, local, _peer = self._bootstrap_remote_and_local()
        (local / "README.md").write_text("ahead\n", encoding="utf-8")
        git(local, "add", "README.md")
        git(local, "commit", "-m", "ahead")
        local_head = git(local, "rev-parse", "HEAD", capture=True)

        completed = self._run_gate(local, "--stage", "finish", "--push")

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("git push origin master:main", payload["actions"])
        self.assertIn("git fetch --prune origin (post-push)", payload["actions"])
        self.assertEqual(git(remote, "rev-parse", "refs/heads/main", capture=True), local_head)

    def test_finish_is_noop_when_ahead_and_behind_are_zero(self) -> None:
        _remote, local, _peer = self._bootstrap_remote_and_local()

        completed = self._run_gate(local, "--stage", "finish")

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("no local commits to push", payload["actions"])

    def test_gate_blocks_merge_or_rebase_markers(self) -> None:
        _remote, local, _peer = self._bootstrap_remote_and_local()
        git_dir = Path(git(local, "rev-parse", "--git-dir", capture=True))
        if not git_dir.is_absolute():
            git_dir = (local / git_dir).resolve()
        (git_dir / "MERGE_HEAD").write_text("deadbeef\n", encoding="utf-8")

        completed = self._run_gate(local, "--stage", "finish")

        self.assertEqual(completed.returncode, 20, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("merge/rebase operation in progress", payload["error"])


if __name__ == "__main__":
    unittest.main()
