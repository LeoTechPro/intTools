#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "delivery" / "bin" / "publish_repo.py"
POWERSHELL_ADAPTER = REPO_ROOT / "codex" / "bin" / "publish_repo.ps1"
SSH_RESOLVER = REPO_ROOT / "codex" / "bin" / "int_ssh_resolve.py"
PUBLISH_DATA_SHIM = REPO_ROOT / "codex" / "bin" / "publish_data.ps1"
DELIVERY_PUBLISH_DATA = REPO_ROOT / "delivery" / "bin" / "publish_data.ps1"
DELIVERY_PUBLISH_ASSESS = REPO_ROOT / "delivery" / "bin" / "publish_assess.ps1"


def load_publish_repo_module():
    spec = importlib.util.spec_from_file_location("publish_repo_under_test", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load publish_repo module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def make_fake_ssh_probe_fail_deploy_ok(bin_dir: Path) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        script_path = bin_dir / "ssh.cmd"
        script_path.write_text(
            "\n".join(
                [
                    "@echo off",
                    "setlocal",
                    "set ARGS=%*",
                    "echo %ARGS% | findstr /C:\" true\" >nul",
                    "if not errorlevel 1 (",
                    "  >&2 echo mock ssh probe failure",
                    "  exit /b 255",
                    ")",
                    ">&2 echo mock ssh deploy success",
                    "exit /b 0",
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
                    "set -euo pipefail",
                    "args=\"$*\"",
                    "if [[ \"$args\" == *\" true\" ]]; then",
                    "  echo 'mock ssh probe failure' >&2",
                    "  exit 255",
                    "fi",
                    "echo 'mock ssh deploy success' >&2",
                    "exit 0",
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
            shutil.which("python3") or shutil.which("python") or "python3",
            str(SCRIPT_PATH),
            "--repo-path",
            str(local),
            "--repo-name",
            "smoke",
            "--success-label",
            "smoke_publish",
            "--expected-branch",
            "main",
            "--expected-upstream",
            "origin/main",
            "--push-remote",
            "origin",
            "--push-branch",
            "main",
            "--require-clean",
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

        completed = self._run_publish(local, "--no-deploy")

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("smoke_publish OK", completed.stdout)
        self.assertIn("pushed origin/main", completed.stdout)
        remote_head = git(remote, "rev-parse", "refs/heads/main", capture=True)
        self.assertEqual(remote_head, local_head)

    def test_dirty_tree_fails_before_push(self) -> None:
        remote, local, base_remote_head = self._bootstrap_remote_and_local()
        (local / "README.md").write_text("dirty\n", encoding="utf-8")

        completed = self._run_publish(local, "--no-deploy")

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
            "--deploy-mode",
            "ssh-fast-forward",
            "--deploy-host",
            "no-such-host.invalid",
            "--deploy-repo-path",
            "/int/data",
            "--deploy-fetch-ref",
            "main",
            "--deploy-pull-ref",
            "main",
            env=env,
        )

        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertIn("partial_state: push in origin/main completed", completed.stdout)
        self.assertIn("ssh no-such-host.invalid failed: mock ssh failure: forced deploy error", completed.stdout)
        remote_head = git(remote, "rev-parse", "refs/heads/main", capture=True)
        self.assertEqual(remote_head, local_head)

    def test_deploy_auto_mode_falls_back_to_public_when_tailnet_probe_fails(self) -> None:
        _remote, local, _ = self._bootstrap_remote_and_local()
        fake_bin = local.parent / "fake-bin"
        make_fake_ssh_probe_fail_deploy_ok(fake_bin)
        env = os.environ.copy()
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
        env["INT_SSH_MODE"] = "auto"

        completed = self._run_publish(
            local,
            "-NoPush",
            "-DeployMode",
            "ssh-fast-forward",
            "-DeployHost",
            "vds-intdata-intdata",
            "-DeployRepoPath",
            "/int/data",
            "-DeployFetchRef",
            "main",
            "-DeployPullRef",
            "main",
            env=env,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("transport=public, fallback=public", completed.stdout)

    def test_run_ssh_checked_uses_resolved_ssh_args(self) -> None:
        module = load_publish_repo_module()
        captured: dict[str, object] = {}

        class DummyCompleted:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
            captured["args"] = list(args)
            captured["kwargs"] = kwargs
            return DummyCompleted()

        with mock.patch.object(module, "resolve_ssh_executable", return_value="ssh"):
            with mock.patch.object(module.subprocess, "run", side_effect=fake_run):
                module.run_ssh_checked(
                    "ignored-host",
                    "git pull --ff-only origin main",
                    ssh_args=["-F", "C:/int/tools/codex/config/int_ssh_config", "int-dev-intdata-public"],
                    timeout_sec=7,
                )

        self.assertEqual(
            captured["args"],
            ["ssh", "-F", "C:/int/tools/codex/config/int_ssh_config", "int-dev-intdata-public", "git pull --ff-only origin main"],
        )
        self.assertEqual(captured["kwargs"]["capture_output"], True)
        self.assertEqual(captured["kwargs"]["text"], True)
        self.assertNotIn("ignored-host", captured["args"])
        self.assertNotIn("-o", captured["args"])

    def test_shared_ssh_resolver_returns_canonical_metadata_shape(self) -> None:
        fake_root = Path(tempfile.mkdtemp(prefix="ssh_resolver_test_"))
        self.addCleanup(remove_tree_force, fake_root)
        fake_bin = fake_root / "fake-bin"
        make_fake_ssh_probe_fail_deploy_ok(fake_bin)
        env = os.environ.copy()
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")

        completed = subprocess.run(
            [
                shutil.which("python3") or shutil.which("python") or "python3",
                str(SSH_RESOLVER),
                "--requested-host",
                "vds-intdata-intdata",
                "--mode",
                "auto",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
            env=env,
            timeout=20,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["logical_host"], "dev-intdata")
        self.assertEqual(payload["transport"], "public")
        self.assertFalse(payload["probe_succeeded"])
        self.assertTrue(payload["fallback_used"])
        self.assertIn("destination", payload)
        self.assertIn("tailnet_host", payload)
        self.assertIn("public_host", payload)
        self.assertIn("ssh_args", payload)

    def test_codex_publish_shims_delegate_to_delivery_wrappers(self) -> None:
        shim_text = PUBLISH_DATA_SHIM.read_text(encoding="utf-8")
        self.assertIn("..\\..\\delivery\\bin\\publish_data.ps1", shim_text)
        self.assertNotIn("-RepoPath", shim_text)
        self.assertTrue(DELIVERY_PUBLISH_DATA.exists())
        self.assertTrue(DELIVERY_PUBLISH_ASSESS.exists())

    @unittest.skipUnless(shutil.which("pwsh"), "pwsh is required for adapter verification")
    def test_powershell_adapter_passes_through_to_python_engine(self) -> None:
        remote, local, _ = self._bootstrap_remote_and_local()
        local_head = self._make_local_commit(local, "adapter\n", "adapter")

        completed = subprocess.run(
            [
                "pwsh",
                "-File",
                str(POWERSHELL_ADAPTER),
                "-RepoPath",
                str(local),
                "-RepoName",
                "smoke",
                "-SuccessLabel",
                "smoke_adapter",
                "-ExpectedBranch",
                "main",
                "-ExpectedUpstream",
                "origin/main",
                "-PushRemote",
                "origin",
                "-PushBranch",
                "main",
                "-RequireClean",
                "-NoDeploy",
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("smoke_adapter OK", completed.stdout)
        self.assertIn("pushed origin/main", completed.stdout)
        remote_head = git(remote, "rev-parse", "refs/heads/main", capture=True)
        self.assertEqual(remote_head, local_head)


if __name__ == "__main__":
    unittest.main()
