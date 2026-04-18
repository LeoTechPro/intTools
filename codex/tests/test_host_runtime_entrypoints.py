#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTER_ROOT = REPO_ROOT / "codex" / "bin"
if str(ROUTER_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROUTER_ROOT))

import codex_host_bootstrap as host_bootstrap  # noqa: E402
import codex_host_verify as host_verify  # noqa: E402
import codex_recovery_bundle as recovery_bundle  # noqa: E402


class HostRuntimeEntrypointsTest(unittest.TestCase):
    def test_windows_dispatch_uses_powershell_adapters(self) -> None:
        command = host_bootstrap.build_repo_step_command(
            "codex/sync_runtime_from_repo.sh",
            "codex/sync_runtime_from_repo.ps1",
            binding_origin="ignored",
        )
        self.assertTrue(command[0].lower().endswith(("pwsh", "powershell", "pwsh.exe", "powershell.exe")))

        original = host_bootstrap.current_platform
        original_ps = host_bootstrap.resolve_powershell
        host_bootstrap.current_platform = lambda: "windows"
        host_bootstrap.resolve_powershell = lambda: "pwsh"
        self.addCleanup(setattr, host_bootstrap, "current_platform", original)
        self.addCleanup(setattr, host_bootstrap, "resolve_powershell", original_ps)

        sync_command = host_bootstrap.build_repo_step_command("codex/sync_runtime_from_repo.sh", "codex/sync_runtime_from_repo.ps1")
        install_command = host_bootstrap.build_repo_step_command("codex/tools/install_tools.sh", "codex/tools/install_tools.ps1")

        self.assertEqual(sync_command[:2], ["pwsh", "-File"])
        self.assertTrue(sync_command[2].endswith("codex\\sync_runtime_from_repo.ps1"))
        self.assertEqual(install_command[:2], ["pwsh", "-File"])
        self.assertTrue(install_command[2].endswith("codex\\tools\\install_tools.ps1"))

    def test_windows_openclaw_adapter_is_machine_readable(self) -> None:
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if not pwsh:
            self.skipTest("PowerShell runtime is required")

        completed = subprocess.run(
            [pwsh, "-File", str(REPO_ROOT / "openclaw" / "ops" / "install.ps1")],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("UNSUPPORTED_PLATFORM", completed.stderr)
        self.assertIn("linux-only", completed.stderr)

    def test_runtime_root_defaults_are_platform_aware(self) -> None:
        with tempfile.TemporaryDirectory(prefix="host_runtime_") as temp_root_raw:
            temp_root = Path(temp_root_raw)
            tools_root = temp_root / "sandbox" / "int" / "tools"
            codex_root = tools_root / "codex"
            codex_root.mkdir(parents=True, exist_ok=True)

            original_repo_root = host_bootstrap.REPO_ROOT
            original_root_dir = host_bootstrap.ROOT_DIR
            original_verify_repo_root = host_verify.REPO_ROOT
            original_recovery_file = recovery_bundle.__file__
            previous_env = {key: os.environ.get(key) for key in ("INT_ROOT", "CODEX_RUNTIME_ROOT", "CLOUD_ROOT", "BRAIN_ROOT")}

            try:
                host_bootstrap.REPO_ROOT = tools_root
                host_bootstrap.ROOT_DIR = codex_root
                host_verify.REPO_ROOT = tools_root
                recovery_bundle.__file__ = str(codex_root / "bin" / "codex_recovery_bundle.py")
                os.environ["INT_ROOT"] = str(temp_root / "sandbox" / "int")
                os.environ.pop("CODEX_RUNTIME_ROOT", None)
                os.environ.pop("CLOUD_ROOT", None)
                self.assertEqual(host_bootstrap.default_runtime_root(), temp_root / "sandbox" / "int" / "tools" / ".runtime")
                self.assertEqual(host_verify.default_runtime_root(), temp_root / "sandbox" / "int" / "tools" / ".runtime")
                self.assertEqual(recovery_bundle.default_runtime_root(), temp_root / "sandbox" / "int" / "tools" / ".runtime")
            finally:
                host_bootstrap.REPO_ROOT = original_repo_root
                host_bootstrap.ROOT_DIR = original_root_dir
                host_verify.REPO_ROOT = original_verify_repo_root
                recovery_bundle.__file__ = original_recovery_file
                for key, value in previous_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
