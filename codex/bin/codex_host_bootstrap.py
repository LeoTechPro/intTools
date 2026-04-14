#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_tool_routing import assert_binding  # noqa: E402


ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT_DIR.parent


class HostBootstrapError(RuntimeError):
    def __init__(self, code: str, message: str, *, step: str | None = None):
        super().__init__(message)
        self.code = code
        self.step = step


def current_platform() -> str:
    if os.name == "nt":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap Codex host runtime layout")
    parser.add_argument("--binding-origin", default="codex/bin/codex_host_bootstrap.py")
    parser.add_argument("--skip-tools", action="store_true")
    parser.add_argument("--skip-openclaw", action="store_true")
    parser.add_argument("--skip-cloud", action="store_true")
    parser.add_argument("--skip-cron", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    return parser


def run_checked(command: list[str], *, cwd: Path | None = None) -> None:
    completed = subprocess.run(command, cwd=str(cwd) if cwd else None, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(command)}")


def sync_managed_runtime(codex_home: Path) -> None:
    assets_root = Path(os.environ.get("ASSETS_ROOT", ROOT_DIR / "assets" / "codex-home")).expanduser()
    projects_root = Path(os.environ.get("PROJECTS_ROOT", ROOT_DIR / "projects")).expanduser()
    if not (assets_root / "AGENTS.md").exists():
        raise RuntimeError(f"missing managed assets root: {assets_root}")

    def copy_file(source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    def replace_dir(source: Path, destination: Path) -> None:
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

    copy_file(assets_root / "AGENTS.md", codex_home / "AGENTS.md")
    copy_file(assets_root / ".personality_migration", codex_home / ".personality_migration")
    copy_file(assets_root / "version.json", codex_home / "version.json")

    replace_dir(assets_root / "rules", codex_home / "rules")
    replace_dir(assets_root / "prompts", codex_home / "prompts")
    replace_dir(assets_root / "skills", codex_home / "skills")

    if projects_root.exists():
        replace_dir(projects_root, codex_home / "projects")


def install_tools_neutral() -> None:
    if current_platform() == "windows":
        run_checked(["npm", "ci"], cwd=ROOT_DIR / "tools" / "openspec")
        run_checked(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "lockctl" / "install_lockctl.ps1"),
            ]
        )
        return
    run_checked([str(ROOT_DIR / "tools" / "install_tools.sh")])


def ensure_supported_step(step: str) -> None:
    if current_platform() != "windows":
        return
    step_messages = {
        "openclaw": "OpenClaw install remains Linux-only because it provisions user systemd services.",
        "cloud": "Cloud access install remains Linux-only because it provisions user systemd mount units.",
        "cron": "Orphan cleaner cron remains Linux-only because it provisions crontab entries.",
    }
    if step in step_messages:
        raise HostBootstrapError("STEP_UNSUPPORTED_PLATFORM", step_messages[step], step=step)


def run_verify_engine() -> None:
    run_checked(
        [
            sys.executable,
            str(ROOT_DIR / "bin" / "codex_host_verify.py"),
            "--binding-origin",
            "codex/bin/codex_host_verify.py",
        ]
    )


def main() -> int:
    args = build_parser().parse_args()
    assert_binding("codex-host-bootstrap", args.binding_origin)

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    runtime_root = Path(os.environ.get("CODEX_RUNTIME_ROOT", "/int/.runtime")).expanduser()
    secrets_root = Path(os.environ.get("CODEX_SECRETS_ROOT", runtime_root / "codex-secrets")).expanduser()
    template_path = Path(os.environ.get("TEMPLATE_PATH", ROOT_DIR / "templates" / "config.toml.tmpl")).expanduser()

    codex_home.mkdir(parents=True, exist_ok=True)
    secrets_root.mkdir(parents=True, exist_ok=True)

    sync_managed_runtime(codex_home)

    config_text = template_path.read_text(encoding="utf-8").replace("__CODEX_HOME__", str(codex_home))
    (codex_home / "config.toml").write_text(config_text, encoding="utf-8")

    if not args.verify_only:
        if not args.skip_tools:
            install_tools_neutral()
        if not args.skip_openclaw:
            ensure_supported_step("openclaw")
            run_checked([str(REPO_ROOT / "openclaw" / "ops" / "install.sh")])
        if not args.skip_cloud:
            ensure_supported_step("cloud")
            run_checked([str(ROOT_DIR / "install_cloud_access.sh")])
        if not args.skip_cron:
            ensure_supported_step("cron")
            run_checked([str(ROOT_DIR / "install_orphan_cleaner_cron.sh")])

    run_verify_engine()

    print("codex host bootstrap: ok")
    print(f"- codex home: {codex_home}")
    print(f"- secrets root: {secrets_root}")
    print("")
    print("If auth.json is absent, run:")
    print("  codex login")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HostBootstrapError as exc:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "error_code": exc.code,
                    "step": exc.step,
                    "platform": current_platform(),
                    "message": str(exc),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)
