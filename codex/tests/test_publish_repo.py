#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "codex" / "bin" / "publish_repo.ps1"
PWSH = shutil.which("pwsh") or shutil.which("powershell")
assert PWSH, "PowerShell executable is required for publish_repo tests"


def run_checked(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def git(repo: Path, *args: str, capture: bool = False) -> str:
    command = ["git", "-C", str(repo), *args]
    if capture:
        return run_checked(command, cwd=repo)
    run_checked(command, cwd=repo)
    return ""


def remove_tree_force(path: Path) -> None:
    def onerror(func, target, exc_info):  # type: ignore[no-untyped-def]
        target_path = Path(target)
        os.chmod(target_path, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onerror=onerror)


def make_fake_ssh(bin_dir: Path, stderr_text: str, exit_code: int = 255) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        script_path = bin_dir / "ssh.cmd"
        script_path.write_text(
            "\n".join(
                [
                    "@echo off",
                    f">&2 echo {stderr_text}",
                    f"exit /b {exit_code}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    else:
        script_path = bin_dir / "ssh"
        script_path.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    f"echo '{stderr_text}' >&2",
                    f"exit {exit_code}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)
    return script_path


class PublishRepoScriptTest(unittest.TestCase):
    maxDiff = None

    def _bootstrap_remote_and_local(self) -> tuple[Path, Path, str]:
        temp_root = Path(tempfile.mkdtemp(prefix="publish_repo_test_"))
        self.addCleanup(remove_tree_force, temp_root)
        remote = temp_root / "remote.git"
        local = temp_root / "local"
        remote.mkdir(parents=True, exist_ok=True)
        local.mkdir(parents=True, exist_ok=True)
        git(remote, "init", "--bare")
        git(local, "init")
        git(local, "config", "user.name", "Codex Test")
        git(local, "config", "user.email", "codex@example.com")
        git(local, "branch", "-M", "main")
        (local / "README.md").write_text("base\n", encoding="utf-8")
        git(local, "add", "README.md")
        git(local, "commit", "-m", "base")
        git(local, "remote", "add", "origin", str(remote))
        git(local, "push", "-u", "origin", "main")
        base_remote_head = git(remote, "rev-parse", "refs/heads/main", capture=True)
        return remote, local, base_remote_head

    def _make_local_commit(self, local: Path, content: str, message: str) -> str:
        (local / "README.md").write_text(content, encoding="utf-8")
        git(local, "add", "README.md")
        git(local, "commit", "-m", message)
        return git(local, "rev-parse", "HEAD", capture=True)

    def _run_publish(
        self,
        local: Path,
        *extra_args: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        args = [
            PWSH,
            "-NoProfile",
            "-File",
            str(SCRIPT_PATH),
            "-RepoPath",
            str(local),
            "-RepoName",
            "smoke",
            "-SuccessLabel",
            "smoke_publish",
            "-ExpectedBranch",
            "main",
            "-ExpectedUpstream",
            "origin/main",
            "-PushRemote",
            "origin",
            "-PushBranch",
            "main",
            "-RequireClean",
            *extra_args,
        ]
        return subprocess.run(
            args,
            cwd=local,
            text=True,
            capture_output=True,
            check=False,
            env=env,
            timeout=20,
        )

    def test_no_deploy_pushes_origin_and_succeeds(self) -> None:
        remote, local, _ = self._bootstrap_remote_and_local()
        local_head = self._make_local_commit(local, "ahead\n", "ahead")

        completed = self._run_publish(local, "-NoDeploy")

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("smoke_publish OK", completed.stdout)
        self.assertIn("pushed origin/main", completed.stdout)
        remote_head = git(remote, "rev-parse", "refs/heads/main", capture=True)
        self.assertEqual(remote_head, local_head)

    def test_dirty_tree_fails_before_push(self) -> None:
        remote, local, base_remote_head = self._bootstrap_remote_and_local()
        (local / "README.md").write_text("dirty\n", encoding="utf-8")

        completed = self._run_publish(local, "-NoDeploy")

        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertIn("working tree is not clean", completed.stdout)
        self.assertNotIn("pushed origin/main", completed.stdout)
        remote_head = git(remote, "rev-parse", "refs/heads/main", capture=True)
        self.assertEqual(remote_head, base_remote_head)

    def test_deploy_failure_reports_partial_state_and_ssh_stderr(self) -> None:
        remote, local, _ = self._bootstrap_remote_and_local()
        local_head = self._make_local_commit(local, "deploy\n", "deploy")
        fake_bin = local.parent / "fake-bin"
        make_fake_ssh(fake_bin, "mock ssh failure: forced deploy error")
        env = os.environ.copy()
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")

        completed = self._run_publish(
            local,
            "-DeployMode",
            "ssh-fast-forward",
            "-DeployHost",
            "no-such-host.invalid",
            "-DeployRepoPath",
            "/int/data",
            "-DeployFetchRef",
            "main",
            "-DeployPullRef",
            "main",
            env=env,
        )

        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertIn("partial_state: push in origin/main completed", completed.stdout)
        self.assertIn("ssh no-such-host.invalid failed: mock ssh failure: forced deploy error", completed.stdout)
        remote_head = git(remote, "rev-parse", "refs/heads/main", capture=True)
        self.assertEqual(remote_head, local_head)


if __name__ == "__main__":
    unittest.main()
