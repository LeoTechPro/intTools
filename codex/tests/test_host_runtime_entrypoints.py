#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import tomllib
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
                self.assertEqual(host_bootstrap.default_runtime_root(), temp_root / "sandbox" / "int" / ".runtime")
                self.assertEqual(host_verify.default_runtime_root(), temp_root / "sandbox" / "int" / ".runtime")
                self.assertEqual(recovery_bundle.default_runtime_root(), temp_root / "sandbox" / "int" / ".runtime")
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

    def test_windows_rendered_config_uses_repo_owned_cmd_launchers(self) -> None:
        original_platform = host_bootstrap.current_platform
        host_bootstrap.current_platform = lambda: "windows"
        self.addCleanup(setattr, host_bootstrap, "current_platform", original_platform)

        rendered = host_bootstrap.render_config_template(
            (REPO_ROOT / "codex" / "templates" / "config.toml.tmpl").read_text(encoding="utf-8"),
            codex_home=Path("D:/Users/test/.codex"),
        )
        config = tomllib.loads(rendered)
        mcp_servers = config["mcp_servers"]
        expected_commands = {
            "github": "mcp-github-from-gh.cmd",
            "postgres": "mcp-postgres-from-backend-env.cmd",
            "obsidian_memory": "mcp-obsidian-memory.cmd",
            "timeweb": "mcp-timeweb.cmd",
            "timeweb_readonly": "mcp-timeweb-readonly.cmd",
            "bitrix24": "mcp-bitrix24.cmd",
            "lockctl": "mcp-lockctl.cmd",
        }

        for server_name, expected_command in expected_commands.items():
            server = mcp_servers[server_name]
            self.assertEqual(server["command"], expected_command)
            self.assertEqual(server.get("args", []), [])

        self.assertNotIn('"command = "bash"', rendered)
        self.assertNotIn('"command = "python"', rendered)
        self.assertNotIn(".sh", rendered)
        self.assertNotIn("mcp-lockctl.py", rendered)

    def test_windows_verify_accepts_repo_owned_cmd_launchers(self) -> None:
        original_platform = host_verify.current_platform
        original_home = host_verify.CODEX_HOME
        original_int_root = host_verify.resolve_int_root
        original_cloud_root = host_verify.default_cloud_root
        original_runtime_root = host_verify.default_runtime_root
        original_bootstrap_platform = host_bootstrap.current_platform
        original_bootstrap_int_root = host_bootstrap.resolve_int_root
        original_bootstrap_cloud_root = host_bootstrap.default_cloud_root

        with tempfile.TemporaryDirectory(prefix="host_verify_") as temp_root_raw:
            temp_root = Path(temp_root_raw)
            codex_home = temp_root / ".codex"
            codex_home.mkdir(parents=True, exist_ok=True)

            host_bootstrap.current_platform = lambda: "windows"
            host_bootstrap.resolve_int_root = lambda: temp_root
            host_bootstrap.default_cloud_root = lambda: temp_root / "cloud"

            rendered = host_bootstrap.render_config_template(
                (REPO_ROOT / "codex" / "templates" / "config.toml.tmpl").read_text(encoding="utf-8"),
                codex_home=codex_home,
            )
            (codex_home / "config.toml").write_text(rendered, encoding="utf-8")

            host_verify.current_platform = lambda: "windows"
            host_verify.CODEX_HOME = codex_home
            host_verify.resolve_int_root = lambda: temp_root
            host_verify.default_cloud_root = lambda: temp_root / "cloud"
            host_verify.default_runtime_root = lambda: temp_root / ".runtime"

            self.addCleanup(setattr, host_verify, "current_platform", original_platform)
            self.addCleanup(setattr, host_verify, "CODEX_HOME", original_home)
            self.addCleanup(setattr, host_verify, "resolve_int_root", original_int_root)
            self.addCleanup(setattr, host_verify, "default_cloud_root", original_cloud_root)
            self.addCleanup(setattr, host_verify, "default_runtime_root", original_runtime_root)
            self.addCleanup(setattr, host_bootstrap, "current_platform", original_bootstrap_platform)
            self.addCleanup(setattr, host_bootstrap, "resolve_int_root", original_bootstrap_int_root)
            self.addCleanup(setattr, host_bootstrap, "default_cloud_root", original_bootstrap_cloud_root)

            issues: list[str] = []
            host_verify.verify_config(issues)
            self.assertEqual(issues, [])
