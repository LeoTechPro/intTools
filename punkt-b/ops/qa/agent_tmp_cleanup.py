#!/usr/bin/env python3
"""Compatibility wrapper for the neutral repo-ops temp cleanup command."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    target = repo_root / "repo-ops" / "bin" / "agent_tmp_cleanup.py"
    default_dir = repo_root / ".runtime" / "punkt-b" / "tmp"
    args = sys.argv[1:]
    if "--dir" not in args:
        args = ["--dir", str(default_dir), *args]
    return subprocess.call([sys.executable, str(target), *args])


if __name__ == "__main__":
    raise SystemExit(main())
