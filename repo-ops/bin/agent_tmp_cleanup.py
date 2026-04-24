#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove old files from an explicitly selected repo operations temp directory."
    )
    parser.add_argument(
        "--dir",
        type=Path,
        required=True,
        help="Target directory. Must be provided explicitly.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Delete files older than N days (default: 1).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files to delete without removing them.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_dir = args.dir.expanduser().resolve()

    if not target_dir.exists():
        print(f"Directory does not exist: {target_dir}", file=sys.stderr)
        return 1
    if not target_dir.is_dir():
        print(f"Not a directory: {target_dir}", file=sys.stderr)
        return 2
    if args.days < 0:
        print("--days must be non-negative", file=sys.stderr)
        return 2

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    deleted = 0
    skipped = 0

    for entry in target_dir.iterdir():
        try:
            stat = entry.lstat()
        except FileNotFoundError:
            continue

        if entry.is_symlink() or not entry.is_file():
            skipped += 1
            continue

        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        if mtime > cutoff:
            skipped += 1
            continue

        if args.dry_run:
            print(str(entry))
            deleted += 1
            continue

        try:
            entry.unlink()
            deleted += 1
        except OSError as exc:
            print(f"Failed to delete {entry}: {exc}", file=sys.stderr)

    if args.dry_run:
        print(f"Candidates: {deleted}, skipped: {skipped}")
    else:
        print(f"Deleted: {deleted}, skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
