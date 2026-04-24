#!/usr/bin/env python3
"""Compatibility wrapper for the neutral repo-ops lock cleanup command."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    target = repo_root / "repo-ops" / "bin" / "agent_lock_cleanup.py"
    args: list[str] = []
    skip_next = False
    for arg in sys.argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if arg == "--file":
            skip_next = True
            continue
        if arg.startswith("--file="):
            continue
        args.append(arg)
    return subprocess.call([sys.executable, str(target), *args])


if __name__ == "__main__":
    raise SystemExit(main())
