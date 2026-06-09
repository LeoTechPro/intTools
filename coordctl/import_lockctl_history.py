#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_LINE = 2_147_483_647


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_tools_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    tools_root = default_tools_root()
    parser = argparse.ArgumentParser(description="Import legacy lockctl history into coordctl runtime history.")
    parser.add_argument("--lockctl-db", type=Path, default=tools_root / ".runtime" / "lockctl" / "locks.sqlite")
    parser.add_argument("--lockctl-events", type=Path, default=tools_root / ".runtime" / "lockctl" / "events.jsonl")
    parser.add_argument("--coord-db", type=Path, default=tools_root / ".runtime" / "coordctl" / "coord.sqlite")
    parser.add_argument("--coord-events", type=Path, default=tools_root / ".runtime" / "coordctl" / "events.jsonl")
    parser.add_argument("--backup-dir", type=Path, default=Path("/int/.tmp/tools/lockctl-history-migration"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser.parse_args()


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def table_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0])


def ensure_coord_schema(conn: sqlite3.Connection) -> None:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required = {"leases", "coord_events"}
    missing = required - tables
    if missing:
        raise RuntimeError(f"coordctl DB missing tables: {', '.join(sorted(missing))}")


def normalize_state(state: str, expires_utc: str) -> str:
    if state == "released":
        return "released"
    try:
        expires = datetime.strptime(expires_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return "expired"
    if expires <= datetime.now(timezone.utc):
        return "expired"
    return "active"


def load_json_text(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def legacy_event_exists(conn: sqlite3.Connection, lockctl_event_id: int) -> bool:
    needle = f'"lockctl_event_id": {lockctl_event_id}'
    row = conn.execute(
        """
        SELECT 1 FROM coord_events
        WHERE event_type LIKE 'legacy_lockctl_%'
          AND instr(payload_json, ?) > 0
        LIMIT 1
        """,
        (needle,),
    ).fetchone()
    return row is not None


def backup_runtime(args: argparse.Namespace) -> dict[str, str]:
    stamp = iso_now().replace(":", "").replace("-", "")
    target = args.backup_dir / stamp
    target.mkdir(parents=True, exist_ok=False)
    backups: dict[str, str] = {}
    for label, path in {
        "lockctl_db": args.lockctl_db,
        "lockctl_events": args.lockctl_events,
        "coord_db": args.coord_db,
        "coord_events": args.coord_events,
    }.items():
        if path.exists():
            dest = target / f"{label}-{path.name}"
            shutil.copy2(path, dest)
            backups[label] = str(dest)
    return backups


def append_coord_event_file(coord_events: Path, event: dict[str, Any]) -> None:
    coord_events.parent.mkdir(parents=True, exist_ok=True)
    with coord_events.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def import_history(args: argparse.Namespace) -> dict[str, Any]:
    if not args.lockctl_db.exists():
        raise RuntimeError(f"missing lockctl DB: {args.lockctl_db}")
    if not args.coord_db.exists():
        raise RuntimeError(f"missing coordctl DB: {args.coord_db}")

    with connect(args.lockctl_db) as source, connect(args.coord_db) as target:
        ensure_coord_schema(target)
        lock_rows = source.execute("SELECT * FROM locks ORDER BY acquired_utc, lock_id").fetchall()
        event_rows = source.execute("SELECT * FROM lock_events ORDER BY event_id").fetchall()
        active_rows = [
            row for row in lock_rows
            if normalize_state(str(row["state"]), str(row["expires_utc"])) == "active"
        ]
        existing_leases = table_count(target, "leases")
        existing_events = table_count(target, "coord_events")

        summary: dict[str, Any] = {
            "lockctl_locks": len(lock_rows),
            "lockctl_events": len(event_rows),
            "lockctl_active_after_normalization": len(active_rows),
            "coordctl_leases_before": existing_leases,
            "coordctl_events_before": existing_events,
            "dry_run": bool(args.dry_run),
        }
        if args.dry_run:
            return summary

        backups = backup_runtime(args)
        inserted_leases = 0
        inserted_events = 0
        imported_at = iso_now()

        with target:
            for row in lock_rows:
                lease_id = f"legacy-lockctl:{row['lock_id']}"
                before = target.total_changes
                target.execute(
                    """
                    INSERT OR IGNORE INTO leases (
                      lease_id, session_id, repo_root, path_rel, owner_id, issue_id,
                      base_ref, base_commit, base_blob, region_kind, region_id,
                      start_line, end_line, lease_sec, acquired_utc, renewed_utc,
                      expires_utc, hostname, pid, state
                    ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, NULL, 'file', 'full',
                      1, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lease_id,
                        row["repo_root"],
                        row["path_rel"],
                        row["owner_id"],
                        row["issue_id"],
                        "legacy-lockctl",
                        "legacy-lockctl",
                        MAX_LINE,
                        row["lease_sec"],
                        row["acquired_utc"],
                        row["renewed_utc"],
                        row["expires_utc"],
                        row["hostname"],
                        row["pid"],
                        normalize_state(str(row["state"]), str(row["expires_utc"])),
                    ),
                )
                inserted_leases += int(target.total_changes > before)

            for row in event_rows:
                if legacy_event_exists(target, int(row["event_id"])):
                    continue
                payload = {
                    "source": "lockctl",
                    "imported_at": imported_at,
                    "lockctl_event_id": row["event_id"],
                    "payload": load_json_text(row["payload_json"]),
                }
                before = target.total_changes
                target.execute(
                    """
                    INSERT OR IGNORE INTO coord_events (
                      event_type, object_id, payload_json, created_utc
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        f"legacy_lockctl_{row['event_type']}",
                        row["lock_id"],
                        json.dumps(payload, ensure_ascii=False, sort_keys=True),
                        row["created_utc"],
                    ),
                )
                inserted_events += int(target.total_changes > before)
                append_coord_event_file(
                    args.coord_events,
                    {
                        "created_utc": row["created_utc"],
                        "event_type": f"legacy_lockctl_{row['event_type']}",
                        "object_id": row["lock_id"],
                        "payload": payload,
                    },
                )

        summary.update({
            "backups": backups,
            "inserted_leases": inserted_leases,
            "inserted_events": inserted_events,
            "coordctl_leases_after": table_count(target, "leases"),
            "coordctl_events_after": table_count(target, "coord_events"),
        })
        return summary


def main() -> int:
    args = parse_args()
    print(json.dumps(import_history(args), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
