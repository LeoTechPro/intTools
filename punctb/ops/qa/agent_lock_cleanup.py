#!/usr/bin/env python3
"""Compatibility wrapper: delegate legacy lock cleanup to lockctl gc."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

LOCKCTL_BIN = os.environ.get("LOCKCTL_BIN", "lockctl")


def resolve_lockctl_bin() -> str:
    candidate = LOCKCTL_BIN.strip()
    if not candidate:
        raise RuntimeError("lockctl command is empty")
    if "/" in candidate:
        path = Path(candidate).expanduser()
        if path.exists():
            return str(path)
        raise RuntimeError(f"missing lockctl: {path}")
    resolved = shutil.which(candidate)
    if resolved:
        return resolved
    raise RuntimeError(f"missing lockctl in PATH: {candidate}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete expired machine-wide locks via lockctl gc.")
    parser.add_argument("--file", default=None, help="Deprecated compatibility flag; ignored")
    parser.add_argument("--dry-run", action="store_true", help="Print compatibility summary only")
    args = parser.parse_args()

    if args.dry_run:
        print("Compatibility dry-run: use `lockctl gc --format json` for real cleanup.")
        return 0

    try:
        lockctl_bin = resolve_lockctl_bin()
    except RuntimeError as exc:
        print(f"[LOCKCTL_MISSING] {exc}", file=sys.stderr)
        return 2

    cp = subprocess.run(
        [lockctl_bin, "gc", "--format", "json"],
        text=True,
        capture_output=True,
        check=False,
    )
    if cp.returncode != 0:
        print(cp.stderr.strip() or cp.stdout.strip() or "[LOCKCTL_FAILED] gc failed", file=sys.stderr)
        return cp.returncode
    try:
        payload = json.loads(cp.stdout)
    except json.JSONDecodeError:
        print(cp.stdout.strip(), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
