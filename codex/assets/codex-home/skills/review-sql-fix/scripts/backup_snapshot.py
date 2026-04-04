#!/usr/bin/env python3
"""Backup helpers for review-sql-fix pipeline."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class BackupError(Exception):
    """Raised when backup phase cannot be completed."""


@dataclass
class BackupResult:
    backup_root: Path
    runtime_metadata_path: Path
    repo_snapshot_paths: list[Path]
    notes: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "backup_root": str(self.backup_root),
            "runtime_metadata_path": str(self.runtime_metadata_path),
            "repo_snapshot_paths": [str(p) for p in self.repo_snapshot_paths],
            "notes": list(self.notes),
        }


def _now_utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _allowed_roots() -> list[Path]:
    roots: list[Path] = []
    for raw in ("/int", "/home/leon", "D:/int", "D:/home/leon", "C:/int", "C:/home/leon"):
        root = Path(raw).resolve()
        if root not in roots:
            roots.append(root)
    return roots


def _default_backup_base() -> Path:
    # Use explicit drive-qualified roots first on Windows to avoid resolving "/int"
    # against an unintended current drive.
    candidates = [Path("D:/int/.tmp"), Path("C:/int/.tmp"), Path("/int/.tmp")]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0]


def _ensure_allowed_target(path: Path) -> None:
    resolved = path.resolve()
    for root in _allowed_roots():
        try:
            resolved.relative_to(root)
            return
        except ValueError:
            continue

    raise BackupError(f"repo target is outside allowed roots: {resolved}")


def _copy_target(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _resolve_optional(path_value: Any) -> Path | None:
    if path_value in (None, ""):
        return None
    return Path(str(path_value)).resolve()


def create_snapshot(payload: dict[str, Any]) -> BackupResult:
    backup_base_raw = payload.get("backup_base")
    backup_base = (
        Path(str(backup_base_raw)).resolve()
        if backup_base_raw not in (None, "")
        else _default_backup_base()
    )
    _ensure_allowed_target(backup_base)
    timestamp = _now_utc_stamp()
    backup_root = backup_base / timestamp / "review-sql-fix"
    runtime_dir = backup_root / "runtime"
    repo_dir = backup_root / "repo"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    repo_dir.mkdir(parents=True, exist_ok=True)

    notes: list[str] = []

    runtime_metadata = {
        "timestamp_utc": timestamp,
        "environment": payload.get("environment"),
        "scope": payload.get("scope"),
        "source": payload.get("source"),
        "fix_mode": payload.get("fix_mode", "apply"),
        "server": payload.get("server"),
        "role_snapshot": payload.get("role_snapshot") or payload.get("runtime_role_snapshot"),
        "settings_snapshot": payload.get("settings_snapshot") or payload.get("runtime_settings_snapshot"),
        "ddl_snapshot": payload.get("ddl_snapshot") or payload.get("runtime_ddl_snapshot"),
        "runtime_executor": payload.get("runtime_executor"),
    }

    runtime_metadata_path = runtime_dir / "runtime-metadata.json"
    runtime_metadata_path.write_text(json.dumps(runtime_metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    pg_dump_source = _resolve_optional(payload.get("pg_dump_path"))
    if pg_dump_source and pg_dump_source.exists():
        _ensure_allowed_target(pg_dump_source)
        pg_dump_destination = runtime_dir / pg_dump_source.name
        _copy_target(pg_dump_source, pg_dump_destination)
        notes.append(f"pg_dump snapshot copied: {pg_dump_destination}")
    elif pg_dump_source:
        notes.append(f"pg_dump path does not exist: {pg_dump_source}")

    repo_snapshot_paths: list[Path] = []
    repo_targets = payload.get("repo_targets") or []
    for raw_target in repo_targets:
        target = Path(str(raw_target)).resolve()
        if not target.exists():
            notes.append(f"repo target does not exist: {target}")
            continue

        _ensure_allowed_target(target)

        safe_name = str(target).replace(":", "").replace("\\", "_").replace("/", "_").strip("_")
        destination = repo_dir / safe_name
        _copy_target(target, destination)
        repo_snapshot_paths.append(destination)

    if not repo_snapshot_paths:
        notes.append("no repo targets were snapshot-copied")

    return BackupResult(
        backup_root=backup_root,
        runtime_metadata_path=runtime_metadata_path,
        repo_snapshot_paths=repo_snapshot_paths,
        notes=notes,
    )
