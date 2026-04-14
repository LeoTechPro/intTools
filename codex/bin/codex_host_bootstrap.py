#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_tool_routing import assert_binding  # noqa: E402


ROOT_DIR = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap Codex host runtime layout")
    parser.add_argument("--binding-origin", default="codex/bin/codex_host_bootstrap.py")
    parser.add_argument("--skip-tools", action="store_true")
    parser.add_argument("--skip-openclaw", action="store_true")
    parser.add_argument("--skip-cloud", action="store_true")
    parser.add_argument("--skip-cron", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    return parser


def run_checked(command: list[str]) -> None:
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(command)}")


def main() -> int:
    args = build_parser().parse_args()
    assert_binding("codex-host-bootstrap", args.binding_origin)

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    runtime_root = Path(os.environ.get("CODEX_RUNTIME_ROOT", "/int/.runtime")).expanduser()
    secrets_root = Path(os.environ.get("CODEX_SECRETS_ROOT", runtime_root / "codex-secrets")).expanduser()
    template_path = Path(os.environ.get("TEMPLATE_PATH", ROOT_DIR / "templates" / "config.toml.tmpl")).expanduser()

    codex_home.mkdir(parents=True, exist_ok=True)
    secrets_root.mkdir(parents=True, exist_ok=True)

    run_checked([str(ROOT_DIR / "sync_runtime_from_repo.sh")])

    config_text = template_path.read_text(encoding="utf-8").replace("__CODEX_HOME__", str(codex_home))
    (codex_home / "config.toml").write_text(config_text, encoding="utf-8")

    if not args.verify_only:
        if not args.skip_tools:
            run_checked([str(ROOT_DIR / "tools" / "install_tools.sh")])
        if not args.skip_openclaw:
            run_checked(["/int/tools/openclaw/ops/install.sh"])
        if not args.skip_cloud:
            run_checked([str(ROOT_DIR / "install_cloud_access.sh")])
        if not args.skip_cron:
            run_checked([str(ROOT_DIR / "install_orphan_cleaner_cron.sh")])

    run_checked([str(ROOT_DIR / "bin" / "codex-host-verify")])

    print("codex host bootstrap: ok")
    print(f"- codex home: {codex_home}")
    print(f"- secrets root: {secrets_root}")
    print("")
    print("If auth.json is absent, run:")
    print("  codex login")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
