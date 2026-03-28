#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil


UTC = timezone.utc


def now_stamp() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive and clean intbrain runtime/vault generated artifacts."
    )
    parser.add_argument("--brain-root", default=r"D:\int\brain", help="int/brain root (or /int/brain on VDS).")
    parser.add_argument(
        "--archive-root",
        default="",
        help="Archive base directory. Default: <brain-root parent>/.tmp",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes only.")
    parser.add_argument("--apply", action="store_true", help="Apply archive + cleanup.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.apply and args.dry_run:
        raise SystemExit("Use either --dry-run or --apply, not both.")
    if not args.apply and not args.dry_run:
        args.dry_run = True

    brain_root = Path(args.brain_root).expanduser().resolve()
    if not brain_root.exists():
        raise SystemExit(f"brain_root_not_found: {brain_root}")

    runtime_root = brain_root / "runtime" / "vault"
    archive_base = (
        Path(args.archive_root).expanduser().resolve()
        if args.archive_root
        else (brain_root.parent / ".tmp").resolve()
    )

    stamp = now_stamp()
    archive_dir = archive_base / stamp / "brain-runtime-vault"
    preserve_dirs = [
        runtime_root / "artifacts",
        runtime_root / "manifests",
        runtime_root / "non_whitelist",
    ]

    entries: list[str] = []
    if runtime_root.exists():
        for item in sorted(runtime_root.rglob("*")):
            entries.append(str(item))

    report: dict[str, object] = {
        "mode": "apply" if args.apply else "dry-run",
        "brain_root": str(brain_root),
        "runtime_root": str(runtime_root),
        "archive_root": str(archive_base),
        "archive_dir": str(archive_dir),
        "runtime_exists": runtime_root.exists(),
        "entries_count": len(entries),
        "preserve_dirs": [str(p) for p in preserve_dirs],
    }

    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    archived_path = ""
    if runtime_root.exists():
        if archive_dir.exists():
            raise SystemExit(f"archive_dir_already_exists: {archive_dir}")
        archive_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(runtime_root), str(archive_dir))
        archived_path = str(archive_dir)

    runtime_root.mkdir(parents=True, exist_ok=True)
    for path in preserve_dirs:
        path.mkdir(parents=True, exist_ok=True)

    report["archived_path"] = archived_path
    report["recreated"] = [str(p) for p in preserve_dirs]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
