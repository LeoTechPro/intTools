#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import socket
import sqlite3
import sys
import textwrap
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4


STATE_DIR = Path(os.environ.get("LOCKCTL_STATE_DIR", "/home/leon/.codex/memories/lockctl")).expanduser().resolve()
DB_PATH = STATE_DIR / "locks.sqlite"
EVENTS_PATH = STATE_DIR / "events.jsonl"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DEFAULT_LEASE_SEC = 60
MAX_LEASE_SEC = 3600
EXIT_OK = 0
EXIT_COMMAND_ERROR = 2


class LockCtlError(Exception):
    def __init__(self, code: str, message: str, *, payload: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.payload = payload or {}
        super().__init__(message)


class RuHelpFormatter(argparse.RawDescriptionHelpFormatter):
    SECTION_TITLES = {
        "positional arguments": "позиционные аргументы",
        "options": "опции",
        "optional arguments": "опции",
        "subcommands": "команды",
    }

    def start_section(self, heading: str | None) -> None:
        if heading is not None:
            heading = self.SECTION_TITLES.get(heading, heading)
        super().start_section(heading)

    def _format_usage(self, usage: str | None, actions: Any, groups: Any, prefix: str | None) -> str:
        return super()._format_usage(usage, actions, groups, prefix="использование: " if prefix is None else prefix)


class RuArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        add_help = kwargs.pop("add_help", True)
        super().__init__(*args, add_help=False, **kwargs)
        self._positionals.title = "позиционные аргументы"
        self._optionals.title = "опции"
        if add_help:
            self.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help="Показать эту справку и выйти.")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime(ISO_FORMAT)


def ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def connect_db() -> sqlite3.Connection:
    ensure_state_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS locks (
          lock_id TEXT PRIMARY KEY,
          repo_root TEXT NOT NULL,
          path_rel TEXT NOT NULL,
          owner_id TEXT NOT NULL,
          issue_id TEXT,
          reason TEXT,
          lease_sec INTEGER NOT NULL,
          acquired_utc TEXT NOT NULL,
          renewed_utc TEXT NOT NULL,
          expires_utc TEXT NOT NULL,
          hostname TEXT NOT NULL,
          pid INTEGER NOT NULL,
          state TEXT NOT NULL CHECK (state IN ('active', 'released', 'expired'))
        );

        CREATE INDEX IF NOT EXISTS idx_locks_key_state
          ON locks(repo_root, path_rel, state, expires_utc);

        CREATE INDEX IF NOT EXISTS idx_locks_owner_state
          ON locks(owner_id, state, expires_utc);

        CREATE INDEX IF NOT EXISTS idx_locks_issue_state
          ON locks(repo_root, issue_id, state, expires_utc);

        CREATE TABLE IF NOT EXISTS lock_events (
          event_id INTEGER PRIMARY KEY AUTOINCREMENT,
          event_type TEXT NOT NULL,
          lock_id TEXT,
          payload_json TEXT NOT NULL,
          created_utc TEXT NOT NULL
        );
        """
    )
    return conn


def emit_event(conn: sqlite3.Connection, event_type: str, lock_id: str | None, payload: dict[str, Any]) -> None:
    created_utc = iso_utc(utc_now())
    payload_json = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    conn.execute(
        "INSERT INTO lock_events(event_type, lock_id, payload_json, created_utc) VALUES (?, ?, ?, ?)",
        (event_type, lock_id, payload_json, created_utc),
    )
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "created_utc": created_utc,
                    "event_type": event_type,
                    "lock_id": lock_id,
                    "payload": payload,
                },
                ensure_ascii=True,
                sort_keys=True,
            )
            + "\n"
        )


def normalize_repo_root(raw: str) -> str:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise LockCtlError("INVALID_REPO_ROOT", f"repo root must be absolute: {raw}")
    return str(path.resolve())


def normalize_path(repo_root: str, raw: str) -> str:
    cleaned = raw.strip().replace("\\", "/")
    if not cleaned:
        raise LockCtlError("INVALID_PATH", "path must not be empty")
    candidate = PurePosixPath(cleaned)
    if candidate.is_absolute():
        abs_target = Path(str(candidate)).resolve()
        try:
            return abs_target.relative_to(Path(repo_root)).as_posix()
        except ValueError as exc:
            raise LockCtlError("INVALID_PATH", f"path escapes repository root: {raw}") from exc
    normalized = os.path.normpath(str(candidate)).replace("\\", "/")
    if normalized in {".", ""} or normalized == ".." or normalized.startswith("../"):
        raise LockCtlError("INVALID_PATH", f"path escapes repository root: {raw}")
    abs_target = (Path(repo_root) / normalized).resolve()
    try:
        abs_target.relative_to(Path(repo_root))
    except ValueError as exc:
        raise LockCtlError("INVALID_PATH", f"path escapes repository root: {raw}") from exc
    return normalized


def normalize_issue(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    if not value.isdigit() or value.startswith("0"):
        raise LockCtlError("INVALID_ISSUE_ID", f"issue must be numeric: {raw}")
    return value


def require_owner(raw: str) -> str:
    owner_id = raw.strip()
    if not owner_id:
        raise LockCtlError("INVALID_OWNER", "owner must not be empty")
    return owner_id


def require_positive_int(name: str, value: int) -> int:
    if value <= 0:
        raise LockCtlError("INVALID_ARGUMENT", f"{name} must be positive, got {value}")
    return value


def require_lease_seconds(value: int) -> int:
    lease_sec = require_positive_int("lease-sec", value)
    if lease_sec > MAX_LEASE_SEC:
        raise LockCtlError("INVALID_ARGUMENT", f"lease-sec must be <= {MAX_LEASE_SEC}, got {lease_sec}")
    return lease_sec


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "acquired_utc": row["acquired_utc"],
        "expires_utc": row["expires_utc"],
        "hostname": row["hostname"],
        "issue_id": row["issue_id"],
        "lease_sec": row["lease_sec"],
        "lock_id": row["lock_id"],
        "owner_id": row["owner_id"],
        "path_rel": row["path_rel"],
        "pid": row["pid"],
        "reason": row["reason"],
        "renewed_utc": row["renewed_utc"],
        "repo_root": row["repo_root"],
        "state": row["state"],
    }


def expire_active_locks(conn: sqlite3.Connection) -> list[str]:
    now = iso_utc(utc_now())
    rows = conn.execute(
        "SELECT lock_id FROM locks WHERE state = 'active' AND expires_utc <= ?",
        (now,),
    ).fetchall()
    if not rows:
        return []
    expired_ids = [str(row["lock_id"]) for row in rows]
    conn.executemany(
        "UPDATE locks SET state = 'expired' WHERE lock_id = ?",
        [(lock_id,) for lock_id in expired_ids],
    )
    for lock_id in expired_ids:
        emit_event(conn, "expire", lock_id, {"lock_id": lock_id})
    return expired_ids


def fetch_active_lock(
    conn: sqlite3.Connection,
    *,
    repo_root: str,
    path_rel: str,
) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT *
        FROM locks
        WHERE repo_root = ? AND path_rel = ? AND state = 'active'
        ORDER BY renewed_utc DESC
        LIMIT 1
        """,
        (repo_root, path_rel),
    ).fetchone()


def status_query(
    conn: sqlite3.Connection,
    *,
    repo_root: str,
    path_rel: str | None,
    owner_id: str | None,
    issue_id: str | None,
    state: str,
) -> list[dict[str, Any]]:
    query = [
        "SELECT * FROM locks WHERE repo_root = ? AND state = ?",
    ]
    params: list[Any] = [repo_root, state]
    if path_rel is not None:
        query.append("AND path_rel = ?")
        params.append(path_rel)
    if owner_id is not None:
        query.append("AND owner_id = ?")
        params.append(owner_id)
    if issue_id is not None:
        query.append("AND issue_id = ?")
        params.append(issue_id)
    query.append("ORDER BY path_rel ASC, renewed_utc DESC")
    rows = conn.execute(" ".join(query), params).fetchall()
    return [row_to_dict(row) for row in rows]


def json_out(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def text_out(payload: dict[str, Any]) -> None:
    if payload.get("ok") is False:
        print(f"[{payload.get('error', 'ERROR')}] {payload.get('message', '')}", file=sys.stderr)
        return
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def render(payload: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        json_out(payload)
    else:
        text_out(payload)


def cmd_acquire(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = normalize_repo_root(args.repo_root)
    path_rel = normalize_path(repo_root, args.path)
    owner_id = require_owner(args.owner)
    lease_sec = require_lease_seconds(args.lease_sec)
    issue_id = normalize_issue(args.issue)
    reason = args.reason.strip() if args.reason else None
    now = utc_now()
    expires = now + timedelta(seconds=lease_sec)

    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        expire_active_locks(conn)
        existing = fetch_active_lock(conn, repo_root=repo_root, path_rel=path_rel)
        if existing is not None and existing["owner_id"] != owner_id:
            conflict = row_to_dict(existing)
            payload = {
                "conflict": conflict,
                "error": "LOCK_CONFLICT",
                "message": f"active lock already exists for {path_rel}",
                "ok": False,
                "path_rel": path_rel,
                "repo_root": repo_root,
            }
            conn.rollback()
            return payload

        if existing is not None:
            conn.execute(
                """
                UPDATE locks
                SET issue_id = ?, reason = ?, lease_sec = ?, renewed_utc = ?, expires_utc = ?, hostname = ?, pid = ?
                WHERE lock_id = ?
                """,
                (
                    issue_id,
                    reason,
                    lease_sec,
                    iso_utc(now),
                    iso_utc(expires),
                    socket.gethostname(),
                    os.getpid(),
                    existing["lock_id"],
                ),
            )
            lock_id = str(existing["lock_id"])
            action = "renewed_existing"
        else:
            lock_id = str(uuid4())
            conn.execute(
                """
                INSERT INTO locks(
                  lock_id, repo_root, path_rel, owner_id, issue_id, reason, lease_sec,
                  acquired_utc, renewed_utc, expires_utc, hostname, pid, state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
                """,
                (
                    lock_id,
                    repo_root,
                    path_rel,
                    owner_id,
                    issue_id,
                    reason,
                    lease_sec,
                    iso_utc(now),
                    iso_utc(now),
                    iso_utc(expires),
                    socket.gethostname(),
                    os.getpid(),
                ),
            )
            action = "acquired"

        row = conn.execute("SELECT * FROM locks WHERE lock_id = ?", (lock_id,)).fetchone()
        assert row is not None
        payload = {
            "action": action,
            "changed": True,
            "lock": row_to_dict(row),
            "ok": True,
        }
        emit_event(conn, "acquire", lock_id, payload)
        conn.commit()
        return payload


def cmd_renew(args: argparse.Namespace) -> dict[str, Any]:
    lease_sec = require_lease_seconds(args.lease_sec)
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        expire_active_locks(conn)
        row = conn.execute("SELECT * FROM locks WHERE lock_id = ?", (args.lock_id,)).fetchone()
        if row is None:
            conn.rollback()
            return {
                "error": "LOCK_NOT_FOUND",
                "message": f"lock not found: {args.lock_id}",
                "ok": False,
            }
        if row["state"] != "active":
            conn.rollback()
            return {
                "error": "LOCK_NOT_ACTIVE",
                "lock": row_to_dict(row),
                "message": f"lock is not active: {args.lock_id}",
                "ok": False,
            }
        now = utc_now()
        expires = now + timedelta(seconds=lease_sec)
        conn.execute(
            "UPDATE locks SET lease_sec = ?, renewed_utc = ?, expires_utc = ?, hostname = ?, pid = ? WHERE lock_id = ?",
            (lease_sec, iso_utc(now), iso_utc(expires), socket.gethostname(), os.getpid(), args.lock_id),
        )
        updated = conn.execute("SELECT * FROM locks WHERE lock_id = ?", (args.lock_id,)).fetchone()
        assert updated is not None
        payload = {"action": "renewed", "changed": True, "lock": row_to_dict(updated), "ok": True}
        emit_event(conn, "renew", args.lock_id, payload)
        conn.commit()
        return payload


def cmd_release_path(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = normalize_repo_root(args.repo_root)
    path_rel = normalize_path(repo_root, args.path)
    owner_id = require_owner(args.owner)

    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        expire_active_locks(conn)
        row = fetch_active_lock(conn, repo_root=repo_root, path_rel=path_rel)
        if row is None:
            conn.rollback()
            return {
                "changed": False,
                "ok": True,
                "path_rel": path_rel,
                "reason": "not_found",
                "repo_root": repo_root,
            }
        if row["owner_id"] != owner_id:
            conn.rollback()
            return {
                "error": "LOCK_OWNER_MISMATCH",
                "lock": row_to_dict(row),
                "message": f"active lock belongs to {row['owner_id']}, not {owner_id}",
                "ok": False,
            }
        conn.execute("UPDATE locks SET state = 'released' WHERE lock_id = ?", (row["lock_id"],))
        released = conn.execute("SELECT * FROM locks WHERE lock_id = ?", (row["lock_id"],)).fetchone()
        assert released is not None
        payload = {"action": "released_path", "changed": True, "lock": row_to_dict(released), "ok": True}
        emit_event(conn, "release_path", str(row["lock_id"]), payload)
        conn.commit()
        return payload


def cmd_release_issue(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = normalize_repo_root(args.repo_root)
    issue_id = normalize_issue(args.issue)
    if issue_id is None:
        raise LockCtlError("INVALID_ISSUE_ID", "issue must not be empty")

    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        expire_active_locks(conn)
        rows = conn.execute(
            """
            SELECT *
            FROM locks
            WHERE repo_root = ? AND issue_id = ? AND state = 'active'
            ORDER BY path_rel ASC, renewed_utc DESC
            """,
            (repo_root, issue_id),
        ).fetchall()
        if not rows:
            conn.rollback()
            return {
                "changed": False,
                "issue_id": issue_id,
                "ok": True,
                "released_paths": [],
                "released_entries": 0,
                "repo_root": repo_root,
            }

        lock_ids = [str(row["lock_id"]) for row in rows]
        conn.executemany("UPDATE locks SET state = 'released' WHERE lock_id = ?", [(lock_id,) for lock_id in lock_ids])
        released_rows = conn.execute(
            f"""
            SELECT *
            FROM locks
            WHERE lock_id IN ({",".join("?" for _ in lock_ids)})
            ORDER BY path_rel ASC, renewed_utc DESC
            """,
            lock_ids,
        ).fetchall()
        payload = {
            "action": "released_issue",
            "changed": True,
            "issue_id": issue_id,
            "locks": [row_to_dict(row) for row in released_rows],
            "ok": True,
            "released_entries": len(released_rows),
            "released_paths": [str(row["path_rel"]) for row in released_rows],
            "repo_root": repo_root,
        }
        for row in released_rows:
            emit_event(conn, "release_issue", str(row["lock_id"]), {"issue_id": issue_id, "repo_root": repo_root})
        conn.commit()
        return payload


def cmd_status(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = normalize_repo_root(args.repo_root)
    path_rel = normalize_path(repo_root, args.path) if args.path else None
    owner_id = require_owner(args.owner) if args.owner else None
    issue_id = normalize_issue(args.issue) if args.issue else None
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        expired_ids = expire_active_locks(conn)
        active = status_query(
            conn,
            repo_root=repo_root,
            path_rel=path_rel,
            owner_id=owner_id,
            issue_id=issue_id,
            state="active",
        )
        expired = status_query(
            conn,
            repo_root=repo_root,
            path_rel=path_rel,
            owner_id=owner_id,
            issue_id=issue_id,
            state="expired",
        )
        conn.commit()
    return {
        "active": active,
        "counts": {"active": len(active), "expired": len(expired)},
        "expired": expired,
        "expired_now": expired_ids,
        "filters": {"issue_id": issue_id, "owner_id": owner_id, "path_rel": path_rel},
        "ok": True,
        "repo_root": repo_root,
    }


def cmd_gc(args: argparse.Namespace) -> dict[str, Any]:
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        expire_active_locks(conn)
        rows = conn.execute("SELECT lock_id FROM locks WHERE state = 'expired'").fetchall()
        expired_ids = [str(row["lock_id"]) for row in rows]
        if expired_ids:
            conn.executemany("DELETE FROM locks WHERE lock_id = ?", [(lock_id,) for lock_id in expired_ids])
            for lock_id in expired_ids:
                emit_event(conn, "gc_delete", lock_id, {"lock_id": lock_id})
        conn.commit()
    return {
        "changed": bool(expired_ids),
        "deleted": len(expired_ids),
        "expired_deleted": len(expired_ids),
        "lock_ids": expired_ids,
        "ok": True,
    }


def build_top_level_epilog() -> str:
    return textwrap.dedent(
        f"""
        Модель lease-локов с одним писателем:
          - один активный лок записи на каждый путь файла относительно репозитория
          - действующий лок определяется активной записью в SQLite с expires_utc > now
          - lease короткие и должны продлеваться, пока запись активна
          - не редактируйте SQLite и events.jsonl напрямую

        Ключевые аргументы:
          --repo-root  абсолютный корень репозитория, например /git/punctb
          --path       путь к файлу относительно --repo-root
          --owner      стабильный id агента/сессии, например codex:session-1
          --issue      числовой id GitHub issue, если проект требует issue-bound локи
          --lease-sec  длительность lease в секундах (по умолчанию {DEFAULT_LEASE_SEC}, максимум {MAX_LEASE_SEC})

        Файлы рантайма:
          LOCKCTL_STATE_DIR={STATE_DIR}
          sqlite={DB_PATH}
          events={EVENTS_PATH}

        Примеры:
          lockctl acquire --repo-root /git/punctb --path AGENTS.md --owner codex:session-1 --issue 1217 --lease-sec 60
          lockctl status --repo-root /git/punctb --issue 1217 --format json
          lockctl release-path --repo-root /git/punctb --path AGENTS.md --owner codex:session-1
          lockctl release-issue --repo-root /git/punctb --issue 1217

        Коды выхода:
          {EXIT_OK}  успех
          {EXIT_COMMAND_ERROR}  ошибка команды или валидации
        """
    ).strip()


def build_parser() -> tuple[argparse.ArgumentParser, dict[str, argparse.ArgumentParser]]:
    parser = RuArgumentParser(
        prog="lockctl",
        description="Локальные lease-локи машины для записи файлов из Codex/OpenClaw.",
        epilog=build_top_level_epilog(),
        formatter_class=RuHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="КОМАНДА", title="команды")
    commands: dict[str, argparse.ArgumentParser] = {}

    def add_command(name: str, **kwargs: Any) -> argparse.ArgumentParser:
        command = sub.add_parser(name, formatter_class=RuHelpFormatter, **kwargs)
        commands[name] = command
        return command

    def add_format_argument(command: argparse.ArgumentParser) -> None:
        command.add_argument("--format", choices=("json", "text"), default="text", help="Формат вывода.")

    acquire = add_command(
        "acquire",
        help="Взять или продлить lease-лок для одного файла относительно репозитория.",
        description=textwrap.dedent(
            f"""
            Взять lease-лок записи для одного файла относительно репозитория.

            Пример:
              lockctl acquire --repo-root /git/punctb --path README.md --owner codex:session-1 --issue 1217 --lease-sec {DEFAULT_LEASE_SEC}
            """
        ).strip(),
    )
    acquire.add_argument("--repo-root", required=True, help="Абсолютный корень репозитория.")
    acquire.add_argument("--path", required=True, help="Путь к файлу относительно репозитория.")
    acquire.add_argument("--owner", required=True, help="Стабильный id владельца/сессии.")
    acquire.add_argument("--issue", help="Числовой id GitHub issue для проектов с issue-bound локами.")
    acquire.add_argument("--reason", help="Необязательная краткая причина для lease.")
    acquire.add_argument("--lease-sec", type=int, default=DEFAULT_LEASE_SEC, help="Длительность lease в секундах.")
    add_format_argument(acquire)

    renew = add_command(
        "renew",
        help="Продлить активный лок по id лока.",
        description=textwrap.dedent(
            f"""
            Продлить существующий активный lease-лок.

            Пример:
              lockctl renew --lock-id <lock-id> --lease-sec {DEFAULT_LEASE_SEC}
            """
        ).strip(),
    )
    renew.add_argument("--lock-id", required=True, help="Идентификатор лока из acquire/status.")
    renew.add_argument("--lease-sec", type=int, default=DEFAULT_LEASE_SEC, help="Новая длительность lease в секундах.")
    add_format_argument(renew)

    release_path = add_command(
        "release-path",
        help="Освободить один активный лок файла для текущего владельца.",
        description=textwrap.dedent(
            """
            Освободить активный лок по repo/path для того же владельца, который его взял.

            Пример:
              lockctl release-path --repo-root /git/punctb --path README.md --owner codex:session-1
            """
        ).strip(),
    )
    release_path.add_argument("--repo-root", required=True, help="Абсолютный корень репозитория.")
    release_path.add_argument("--path", required=True, help="Путь к файлу относительно репозитория.")
    release_path.add_argument("--owner", required=True, help="Стабильный id владельца/сессии.")
    add_format_argument(release_path)

    release_issue = add_command(
        "release-issue",
        help="Освободить все активные локи для одного issue в пределах репозитория.",
        description=textwrap.dedent(
            """
            Освободить все активные локи в одном корне репозитория для указанного issue id.

            Пример:
              lockctl release-issue --repo-root /git/punctb --issue 1217
            """
        ).strip(),
    )
    release_issue.add_argument("--repo-root", required=True, help="Абсолютный корень репозитория.")
    release_issue.add_argument("--issue", required=True, help="Числовой id GitHub issue.")
    add_format_argument(release_issue)

    status = add_command(
        "status",
        help="Показать активные и истёкшие локи с фильтром по repo/path/owner/issue.",
        description=textwrap.dedent(
            """
            Показать активные и истёкшие lease-записи для одного репозитория.

            Примеры:
              lockctl status --repo-root /git/punctb
              lockctl status --repo-root /git/punctb --path README.md --format json
              lockctl status --repo-root /git/punctb --issue 1217 --format json
            """
        ).strip(),
    )
    status.add_argument("--repo-root", required=True, help="Абсолютный корень репозитория.")
    status.add_argument("--path", help="Фильтр по пути к файлу относительно репозитория.")
    status.add_argument("--owner", help="Фильтр по id владельца/сессии.")
    status.add_argument("--issue", help="Фильтр по числовому id GitHub issue.")
    add_format_argument(status)

    gc = add_command(
        "gc",
        help="Удалить истёкшие локи из runtime-хранилища.",
        description=textwrap.dedent(
            """
            Удалить только истёкшие lease-записи.

            Пример:
              lockctl gc --format json
            """
        ).strip(),
    )
    add_format_argument(gc)

    help_cmd = add_command(
        "help",
        help="Показать общую справку или справку по одной команде.",
        description="Показать общую справку или справку по одной команде.",
    )
    help_cmd.add_argument("topic", nargs="?", help="Необязательное имя команды.")

    return parser, commands


def print_help(parser: argparse.ArgumentParser, commands: dict[str, argparse.ArgumentParser], topic: str | None) -> int:
    if topic is None:
        parser.print_help()
        return EXIT_OK
    target = commands.get(topic)
    if target is None:
        print(f"[UNKNOWN_COMMAND] неизвестная тема справки: {topic}", file=sys.stderr)
        return EXIT_COMMAND_ERROR
    target.print_help()
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser, commands = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        parser.print_help()
        return EXIT_OK
    if argv[0] in {"-h", "--help"}:
        parser.print_help()
        return EXIT_OK
    if argv[0] == "help":
        topic = argv[1] if len(argv) > 1 else None
        return print_help(parser, commands, topic)

    args = parser.parse_args(argv)
    try:
        if args.command == "acquire":
            payload = cmd_acquire(args)
        elif args.command == "renew":
            payload = cmd_renew(args)
        elif args.command == "release-path":
            payload = cmd_release_path(args)
        elif args.command == "release-issue":
            payload = cmd_release_issue(args)
        elif args.command == "status":
            payload = cmd_status(args)
        elif args.command == "gc":
            payload = cmd_gc(args)
        else:
            raise LockCtlError("UNKNOWN_COMMAND", f"unknown command: {args.command}")
    except LockCtlError as exc:
        payload = {"error": exc.code, "message": exc.message, "ok": False, **exc.payload}
    render(payload, args.format)
    return EXIT_OK if payload.get("ok") else EXIT_COMMAND_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
