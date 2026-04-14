#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform publish wrapper for /int/data")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--no-deploy", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(__file__).resolve().parents[3]
    engine = root / "tools" / "delivery" / "bin" / "publish_repo.py"
    repo = root / "data"
    command = [
        sys.executable,
        str(engine),
        "--repo-path",
        str(repo),
        "--repo-name",
        "data",
        "--success-label",
        "publish_data",
        "--expected-branch",
        "main",
        "--expected-upstream",
        "origin/main",
        "--push-remote",
        "origin",
        "--push-branch",
        "main",
        "--require-clean",
        "--deploy-mode",
        "ssh-fast-forward",
        "--deploy-host",
        "vds-intdata-intdata",
        "--deploy-repo-path",
        "/int/data",
        "--deploy-fetch-ref",
        "main",
        "--deploy-pull-ref",
        "main",
    ]
    if args.no_push:
        command.append("--no-push")
    if args.no_deploy:
        command.append("--no-deploy")
    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
