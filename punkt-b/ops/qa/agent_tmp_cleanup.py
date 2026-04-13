#!/usr/bin/env python3
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove files older than N days from the PunktB ops runtime temp directory."
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Target directory (default: ~/.codex/tmp/punkt-b)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Delete files older than N days (default: 1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files to delete without removing them",
    )
    return parser.parse_args()


def main() -> int:
    default_dir = Path.home() / ".codex" / "tmp" / "punkt-b"

    args = parse_args()
    target_dir = (args.dir or default_dir).resolve()
    expected_dir = default_dir.resolve()

    if target_dir != expected_dir:
        print(
            f"Refusing to operate on non-default directory: {target_dir}",
            file=sys.stderr,
        )
        return 2

    if not target_dir.exists():
        print(f"Directory does not exist: {target_dir}", file=sys.stderr)
        return 1

    if args.days < 0:
        print("--days must be non-negative", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=args.days)

    deleted = 0
    skipped = 0

    for entry in target_dir.iterdir():
        try:
            stat = entry.lstat()
        except FileNotFoundError:
            continue

        if entry.is_symlink():
            skipped += 1
            continue

        if not entry.is_file():
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
        print(f"Candidates: {deleted}")
    else:
        print(f"Deleted: {deleted}, skipped: {skipped}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
