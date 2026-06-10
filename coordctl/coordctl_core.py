#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import subprocess
import sys
import textwrap
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4


ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DEFAULT_LEASE_SEC = 60
# `begin` is the cheap default entrypoint for a whole work stint, so its default
# lease must survive real thinking/editing time without a heartbeat loop.
DEFAULT_BEGIN_LEASE_SEC = 600
MAX_LEASE_SEC = 3600
RECLAIM_DEAD_LOCAL_PIDS_ENV = "COORDCTL_RECLAIM_DEAD_LOCAL_PIDS"
EXIT_OK = 0
EXIT_COMMAND_ERROR = 2
SUPPORTED_REGION_KINDS = {"file", "hunk"}
RESERVED_REGION_KINDS = {"symbol", "json_path", "section"}
MAX_LINE = 2_147_483_647
FINAL_SESSION_STATES = {"merged", "released", "abandoned", "blocked-owner", "failed-cleanup"}
GC_SESSION_STATES = {"expired", *FINAL_SESSION_STATES}


class CoordCtlError(Exception):
    def __init__(self, code: str, message: str, *, payload: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.payload = payload or {}
        super().__init__(message)


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        result = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return result


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime(ISO_FORMAT)


def env_flag(name: str) -> bool:
    return str(os.environ.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        # os.kill(pid, 0) is a signal-style probe on Unix, but on Windows it can
        # terminate the target process. Query the process status without sending
        # any signal so coordctl cleanup cannot kill Codex/MCP processes.
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        process_query_limited_information = 0x1000
        still_active = 259
        error_access_denied = 5

        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return ctypes.get_last_error() == error_access_denied
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return True
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _resolve_tools_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _windows_drive_candidates() -> list[str]:
    raw_candidates = [
        Path(__file__).resolve().drive,
        Path.cwd().drive,
        os.environ.get("SystemDrive", ""),
    ]
    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in raw_candidates:
        value = str(candidate or "").strip()
        if not value:
            continue
        if not value.endswith(":"):
            value = f"{value}:"
        key = value.upper()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(value)
    return normalized


def _resolve_windows_posix_absolute(cleaned: str) -> Path:
    for drive in _windows_drive_candidates():
        candidate = Path(f"{drive}{cleaned}").expanduser()
        if candidate.exists():
            return candidate
    for drive in _windows_drive_candidates():
        return Path(f"{drive}{cleaned}").expanduser()
    return Path(cleaned).expanduser()


def resolve_state_dir() -> Path:
    explicit = os.environ.get("COORDCTL_STATE_DIR", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (_resolve_tools_root() / ".runtime" / "coordctl").resolve()


def ensure_state_dir() -> Path:
    state_dir = resolve_state_dir()
    state_dir.parent.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "tmp").mkdir(parents=True, exist_ok=True)
    return state_dir


def db_path() -> Path:
    return ensure_state_dir() / "coord.sqlite"


def events_path() -> Path:
    return ensure_state_dir() / "events.jsonl"


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
          session_id TEXT PRIMARY KEY,
          repo_root TEXT NOT NULL,
          owner_id TEXT NOT NULL,
          issue_id TEXT,
          branch_name TEXT NOT NULL,
          base_ref TEXT NOT NULL,
          base_commit TEXT NOT NULL,
          acquired_utc TEXT NOT NULL,
          heartbeat_utc TEXT NOT NULL,
          expires_utc TEXT NOT NULL,
          worktree_path TEXT,
          cleanup_status TEXT,
          cleanup_utc TEXT,
          hostname TEXT NOT NULL,
          pid INTEGER NOT NULL,
          state TEXT NOT NULL CHECK (state IN ('active', 'released', 'expired', 'merged', 'abandoned', 'blocked-owner', 'failed-cleanup'))
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_repo_state
          ON sessions(repo_root, state, expires_utc);

        CREATE INDEX IF NOT EXISTS idx_sessions_issue_state
          ON sessions(repo_root, issue_id, state, expires_utc);

        CREATE TABLE IF NOT EXISTS leases (
          lease_id TEXT PRIMARY KEY,
          session_id TEXT,
          repo_root TEXT NOT NULL,
          path_rel TEXT NOT NULL,
          owner_id TEXT NOT NULL,
          issue_id TEXT,
          base_ref TEXT NOT NULL,
          base_commit TEXT NOT NULL,
          base_blob TEXT,
          region_kind TEXT NOT NULL,
          region_id TEXT NOT NULL,
          start_line INTEGER NOT NULL,
          end_line INTEGER NOT NULL,
          lease_sec INTEGER NOT NULL,
          acquired_utc TEXT NOT NULL,
          renewed_utc TEXT NOT NULL,
          expires_utc TEXT NOT NULL,
          hostname TEXT NOT NULL,
          pid INTEGER NOT NULL,
          state TEXT NOT NULL CHECK (state IN ('active', 'released', 'expired')),
          FOREIGN KEY(session_id) REFERENCES sessions(session_id)
        );

        CREATE INDEX IF NOT EXISTS idx_leases_key_state
          ON leases(repo_root, path_rel, state, expires_utc);

        CREATE INDEX IF NOT EXISTS idx_leases_owner_state
          ON leases(owner_id, state, expires_utc);

        CREATE INDEX IF NOT EXISTS idx_leases_issue_state
          ON leases(repo_root, issue_id, state, expires_utc);

        CREATE INDEX IF NOT EXISTS idx_leases_state_hostname
          ON leases(state, hostname, expires_utc);

        CREATE INDEX IF NOT EXISTS idx_leases_session_state
          ON leases(session_id, state, expires_utc);

        CREATE INDEX IF NOT EXISTS idx_leases_repo_owner_state
          ON leases(repo_root, owner_id, state, expires_utc);

        CREATE INDEX IF NOT EXISTS idx_sessions_state_hostname
          ON sessions(state, hostname, expires_utc);

        CREATE TABLE IF NOT EXISTS coord_events (
          event_id INTEGER PRIMARY KEY AUTOINCREMENT,
          event_type TEXT NOT NULL,
          object_id TEXT,
          payload_json TEXT NOT NULL,
          created_utc TEXT NOT NULL
        );
        """
    )
    ensure_column(conn, "sessions", "worktree_path", "TEXT")
    ensure_column(conn, "sessions", "cleanup_status", "TEXT")
    ensure_column(conn, "sessions", "cleanup_utc", "TEXT")
    return conn


def ensure_column(conn: sqlite3.Connection, table: str, name: str, ddl: str) -> None:
    columns = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if name not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def emit_event(conn: sqlite3.Connection, event_type: str, object_id: str | None, payload: dict[str, Any]) -> None:
    created_utc = iso_utc(utc_now())
    payload_json = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    conn.execute(
        "INSERT INTO coord_events(event_type, object_id, payload_json, created_utc) VALUES (?, ?, ?, ?)",
        (event_type, object_id, payload_json, created_utc),
    )
    # events.jsonl is a best-effort mirror; the transactional coord_events table
    # is the source of truth. A failing journal write must never roll back the
    # transaction (e.g. disk full, permissions, stale NFS).
    try:
        with events_path().open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "created_utc": created_utc,
                        "event_type": event_type,
                        "object_id": object_id,
                        "payload": payload,
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                )
                + "\n"
            )
    except OSError as exc:
        print(f"coordctl: events.jsonl mirror write failed ({exc}); coord_events row preserved", file=sys.stderr)


def normalize_repo_root(raw: str) -> str:
    cleaned = raw.strip()
    path = Path(cleaned).expanduser()
    if os.name == "nt" and not path.is_absolute() and cleaned.startswith("/") and not cleaned.startswith("//"):
        path = _resolve_windows_posix_absolute(cleaned)
    if not path.is_absolute():
        raise CoordCtlError("INVALID_REPO_ROOT", f"repo root must be absolute: {raw}")
    return str(path.resolve())


def _is_absolute_input_path(raw: str) -> bool:
    cleaned = raw.strip()
    if not cleaned:
        return False
    if cleaned.startswith(("\\\\", "/")):
        return True
    return bool(re.match(r"^[A-Za-z]:[\\/]", cleaned))


def normalize_path(repo_root: str, raw: str) -> str:
    cleaned = raw.strip()
    if not cleaned:
        raise CoordCtlError("INVALID_PATH", "path must not be empty")
    repo_root_path = Path(repo_root).resolve()
    if _is_absolute_input_path(cleaned):
        abs_candidate = Path(cleaned).expanduser()
        if os.name == "nt" and not abs_candidate.is_absolute() and cleaned.startswith("/") and not cleaned.startswith("//"):
            abs_candidate = _resolve_windows_posix_absolute(cleaned)
        abs_target = abs_candidate.resolve()
        try:
            return abs_target.relative_to(repo_root_path).as_posix()
        except ValueError as exc:
            raise CoordCtlError("INVALID_PATH", f"path escapes repository root: {raw}") from exc

    normalized = os.path.normpath(cleaned.replace("\\", "/")).replace("\\", "/")
    if normalized in {".", ""} or normalized == ".." or normalized.startswith("../"):
        raise CoordCtlError("INVALID_PATH", f"path escapes repository root: {raw}")
    if re.match(r"^[A-Za-z]:", normalized):
        raise CoordCtlError("INVALID_PATH", f"path must be relative or absolute under repo root: {raw}")
    abs_target = (repo_root_path / normalized).resolve()
    try:
        return abs_target.relative_to(repo_root_path).as_posix()
    except ValueError as exc:
        raise CoordCtlError("INVALID_PATH", f"path escapes repository root: {raw}") from exc


def normalize_worktree_path(repo_root: str, raw: str | None) -> str | None:
    if raw is None or not isinstance(raw, str) or not raw.strip():
        return None
    cleaned = raw.strip()
    candidate = Path(cleaned).expanduser()
    if os.name == "nt" and not candidate.is_absolute() and cleaned.startswith("/") and not cleaned.startswith("//"):
        candidate = _resolve_windows_posix_absolute(cleaned)
    if not candidate.is_absolute():
        candidate = Path(repo_root).resolve().parent / candidate
    return str(candidate.resolve())


def normalize_issue(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    if value.isdigit():
        if value.startswith("0"):
            raise CoordCtlError("INVALID_ISSUE_ID", f"issue must be a positive integer or INT-* id: {raw}")
        return value
    normalized = value.upper()
    if re.fullmatch(r"INT-[1-9][0-9]*", normalized):
        return normalized
    raise CoordCtlError("INVALID_ISSUE_ID", f"issue must be a positive integer or INT-* id: {raw}")


def require_owner(raw: str) -> str:
    owner_id = raw.strip()
    if not owner_id:
        raise CoordCtlError("INVALID_OWNER", "owner must not be empty")
    return owner_id


def require_lease_seconds(value: int) -> int:
    if value <= 0:
        raise CoordCtlError("INVALID_ARGUMENT", f"lease-sec must be positive, got {value}")
    if value > MAX_LEASE_SEC:
        raise CoordCtlError("INVALID_ARGUMENT", f"lease-sec must be <= {MAX_LEASE_SEC}, got {value}")
    return value


def git(repo_root: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        shell=False,
    )
    if check and cp.returncode != 0:
        raise CoordCtlError(
            "GIT_ERROR",
            cp.stderr.strip() or cp.stdout.strip() or f"git {' '.join(args)} failed",
            payload={"argv": ["git", *args], "returncode": cp.returncode},
        )
    return cp


def resolve_commit(repo_root: str, ref: str) -> str:
    value = ref.strip()
    if not value:
        raise CoordCtlError("INVALID_BASE", "base must not be empty")
    cp = git(repo_root, "rev-parse", "--verify", f"{value}^{{commit}}", check=False)
    if cp.returncode != 0:
        raise CoordCtlError("STALE_BASE", f"base commit cannot be resolved: {ref}")
    return cp.stdout.strip()


def resolve_base_blob(repo_root: str, base_commit: str, path_rel: str) -> str | None:
    cp = git(repo_root, "rev-parse", "--verify", f"{base_commit}:{path_rel}", check=False)
    if cp.returncode != 0:
        return None
    return cp.stdout.strip()


def normalize_region(region_kind: str, region_id: str) -> tuple[str, str, int, int]:
    kind = region_kind.strip().lower()
    rid = region_id.strip()
    if kind in RESERVED_REGION_KINDS:
        raise CoordCtlError("UNSUPPORTED_REGION_KIND", f"{kind} requires a semantic extractor not available in v1")
    if kind not in SUPPORTED_REGION_KINDS:
        raise CoordCtlError("INVALID_REGION_KIND", f"unsupported region kind: {region_kind}")
    if kind == "file":
        return kind, rid or "*", 1, MAX_LINE
    if not rid:
        raise CoordCtlError("INVALID_REGION", "hunk region-id must not be empty")
    numbers = [int(value) for value in re.findall(r"\d+", rid)]
    if not numbers:
        raise CoordCtlError("INVALID_REGION", f"hunk region-id must include line numbers: {region_id}")
    if len(numbers) == 1:
        start = end = numbers[0]
    else:
        start, end = numbers[0], numbers[1]
    if start <= 0 or end <= 0:
        raise CoordCtlError("INVALID_REGION", f"hunk region lines must be positive: {region_id}")
    if end < start:
        start, end = end, start
    return kind, rid, start, end


def ranges_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start <= b_end and b_start <= a_end


def session_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "session_id": row["session_id"],
        "repo_root": row["repo_root"],
        "owner_id": row["owner_id"],
        "issue_id": row["issue_id"],
        "branch_name": row["branch_name"],
        "base_ref": row["base_ref"],
        "base_commit": row["base_commit"],
        "acquired_utc": row["acquired_utc"],
        "heartbeat_utc": row["heartbeat_utc"],
        "expires_utc": row["expires_utc"],
        "worktree_path": row["worktree_path"],
        "cleanup_status": row["cleanup_status"],
        "cleanup_utc": row["cleanup_utc"],
        "hostname": row["hostname"],
        "pid": row["pid"],
        "state": row["state"],
    }


def lease_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "lease_id": row["lease_id"],
        "session_id": row["session_id"],
        "repo_root": row["repo_root"],
        "path_rel": row["path_rel"],
        "owner_id": row["owner_id"],
        "issue_id": row["issue_id"],
        "base_ref": row["base_ref"],
        "base_commit": row["base_commit"],
        "base_blob": row["base_blob"],
        "region_kind": row["region_kind"],
        "region_id": row["region_id"],
        "start_line": row["start_line"],
        "end_line": row["end_line"],
        "lease_sec": row["lease_sec"],
        "acquired_utc": row["acquired_utc"],
        "renewed_utc": row["renewed_utc"],
        "expires_utc": row["expires_utc"],
        "hostname": row["hostname"],
        "pid": row["pid"],
        "state": row["state"],
    }


def expire_stale_local_process_rows(conn: sqlite3.Connection) -> dict[str, list[str]]:
    if not env_flag(RECLAIM_DEAD_LOCAL_PIDS_ENV):
        return {"sessions": [], "leases": []}

    hostname = socket.gethostname()
    stale_sessions = [
        str(row["session_id"])
        for row in conn.execute("SELECT session_id, pid FROM sessions WHERE state = 'active' AND hostname = ?", (hostname,)).fetchall()
        if not pid_alive(int(row["pid"]))
    ]
    stale_leases = [
        str(row["lease_id"])
        for row in conn.execute("SELECT lease_id, pid FROM leases WHERE state = 'active' AND hostname = ?", (hostname,)).fetchall()
        if not pid_alive(int(row["pid"]))
    ]
    if stale_sessions:
        conn.executemany("UPDATE sessions SET state = 'expired' WHERE session_id = ?", [(sid,) for sid in stale_sessions])
    if stale_leases:
        conn.executemany("UPDATE leases SET state = 'expired' WHERE lease_id = ?", [(lid,) for lid in stale_leases])
    for sid in stale_sessions:
        emit_event(conn, "session_expire", sid, {"reason": "dead_local_pid", "session_id": sid})
    for lid in stale_leases:
        emit_event(conn, "lease_expire", lid, {"lease_id": lid, "reason": "dead_local_pid"})
    return {"sessions": stale_sessions, "leases": stale_leases}


def expire_active(conn: sqlite3.Connection) -> dict[str, list[str]]:
    stale = expire_stale_local_process_rows(conn)
    now = iso_utc(utc_now())
    expired_sessions = [str(row["session_id"]) for row in conn.execute("SELECT session_id FROM sessions WHERE state = 'active' AND expires_utc <= ?", (now,)).fetchall()]
    expired_leases = [str(row["lease_id"]) for row in conn.execute("SELECT lease_id FROM leases WHERE state = 'active' AND expires_utc <= ?", (now,)).fetchall()]
    if expired_sessions:
        conn.executemany("UPDATE sessions SET state = 'expired' WHERE session_id = ?", [(sid,) for sid in expired_sessions])
    if expired_leases:
        conn.executemany("UPDATE leases SET state = 'expired' WHERE lease_id = ?", [(lid,) for lid in expired_leases])
    for sid in expired_sessions:
        emit_event(conn, "session_expire", sid, {"session_id": sid})
    for lid in expired_leases:
        emit_event(conn, "lease_expire", lid, {"lease_id": lid})
    return {"sessions": stale["sessions"] + expired_sessions, "leases": stale["leases"] + expired_leases}


def _optional_session_id(args: argparse.Namespace) -> str | None:
    value = getattr(args, "session_id", None)
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def cmd_session_start(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = normalize_repo_root(args.repo_root)
    owner_id = require_owner(args.owner)
    issue_id = normalize_issue(args.issue)
    branch = args.branch.strip()
    if not branch:
        raise CoordCtlError("INVALID_BRANCH", "branch must not be empty")
    base_ref = args.base.strip()
    base_commit = resolve_commit(repo_root, base_ref)
    lease_sec = require_lease_seconds(args.lease_sec)
    worktree_path = normalize_worktree_path(repo_root, getattr(args, "worktree_path", None))
    now = utc_now()
    expires = now + timedelta(seconds=lease_sec)
    session_id = str(uuid4())

    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        expire_active(conn)
        conn.execute(
            """
            INSERT INTO sessions(
              session_id, repo_root, owner_id, issue_id, branch_name, base_ref, base_commit,
              acquired_utc, heartbeat_utc, expires_utc, worktree_path, cleanup_status, cleanup_utc,
              hostname, pid, state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, 'active')
            """,
            (
                session_id,
                repo_root,
                owner_id,
                issue_id,
                branch,
                base_ref,
                base_commit,
                iso_utc(now),
                iso_utc(now),
                iso_utc(expires),
                worktree_path,
                socket.gethostname(),
                os.getpid(),
            ),
        )
        row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            raise CoordCtlError("INTERNAL_ERROR", f"session {session_id} not found after insert")
        payload = {"action": "session_started", "changed": True, "ok": True, "session": session_to_dict(row)}
        emit_event(conn, "session_start", session_id, payload)
        conn.commit()
        return payload


def _git_toplevel(start: str) -> str:
    cp = git(start, "rev-parse", "--show-toplevel", check=False)
    if cp.returncode != 0:
        raise CoordCtlError("NOT_A_GIT_REPO", f"not inside a git repository: {start}")
    return cp.stdout.strip()


def cmd_begin(args: argparse.Namespace) -> dict[str, Any]:
    # Cheap, non-blocking default entrypoint. Autodetects repo/branch/base so a
    # session (and optional coarse intent) is a single command. Never fails on
    # overlaps; overlaps surface only as warnings on the intent.
    start = str(getattr(args, "repo_root", None) or os.getcwd())
    repo_root = normalize_repo_root(_git_toplevel(start))
    owner_id = require_owner(str(getattr(args, "owner", None) or os.environ.get("COORDCTL_OWNER", "")))
    issue_id = normalize_issue(getattr(args, "issue", None))
    branch = str(getattr(args, "branch", None) or "").strip() or git(repo_root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    base_ref = str(getattr(args, "base", None) or "").strip() or "HEAD"
    lease_sec = require_lease_seconds(int(getattr(args, "lease_sec", None) or DEFAULT_BEGIN_LEASE_SEC))
    raw_path = getattr(args, "path", None)
    raw_path = raw_path.strip() if isinstance(raw_path, str) and raw_path.strip() else None

    session = cmd_session_start(argparse.Namespace(
        repo_root=repo_root, owner=owner_id, issue=issue_id, branch=branch,
        base=base_ref, worktree_path=getattr(args, "worktree_path", None), lease_sec=lease_sec,
    ))
    payload: dict[str, Any] = {"action": "begin", "ok": True, "session": session["session"]}
    if raw_path:
        intent = cmd_intent_acquire(argparse.Namespace(
            repo_root=repo_root, path=raw_path, owner=owner_id, issue=issue_id, base=base_ref,
            region_kind="file", region_id=raw_path, lease_sec=lease_sec,
            session_id=session["session"]["session_id"],
        ))
        payload["intent"] = intent
        payload["overlaps"] = intent.get("overlaps", [])
        payload["warnings"] = intent.get("warnings", [])
    return payload


def find_active_session(conn: sqlite3.Connection, session_id: str | None) -> sqlite3.Row | None:
    if not session_id:
        return None
    return conn.execute("SELECT * FROM sessions WHERE session_id = ? AND state = 'active'", (session_id,)).fetchone()


def cmd_intent_acquire(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = normalize_repo_root(args.repo_root)
    path_rel = normalize_path(repo_root, args.path)
    owner_id = require_owner(args.owner)
    issue_id = normalize_issue(args.issue)
    base_ref = args.base.strip()
    base_commit = resolve_commit(repo_root, base_ref)
    base_blob = resolve_base_blob(repo_root, base_commit, path_rel)
    region_kind, region_id, start_line, end_line = normalize_region(args.region_kind, args.region_id)
    lease_sec = require_lease_seconds(args.lease_sec)
    session_id = _optional_session_id(args)
    now = utc_now()
    expires = now + timedelta(seconds=lease_sec)

    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        expire_active(conn)
        session = find_active_session(conn, session_id)
        if session_id and session is None:
            conn.rollback()
            return {"error": "SESSION_NOT_ACTIVE", "message": f"session is not active: {session_id}", "ok": False}
        if session is not None:
            if session["repo_root"] != repo_root or session["owner_id"] != owner_id:
                conn.rollback()
                return {
                    "error": "SESSION_MISMATCH",
                    "message": f"session {session_id} does not match repo/owner",
                    "ok": False,
                    "session": session_to_dict(session),
                }
            current_session_base = resolve_commit(repo_root, str(session["base_ref"]))
            if current_session_base != session["base_commit"]:
                conn.rollback()
                return {
                    "current_base_commit": current_session_base,
                    "error": "STALE_BASE",
                    "message": f"session base ref moved for {session_id}",
                    "ok": False,
                    "session": session_to_dict(session),
                }
            if session["base_commit"] != base_commit:
                conn.rollback()
                return {
                    "error": "STALE_BASE",
                    "message": f"intent base does not match session base for {session_id}",
                    "ok": False,
                    "session": session_to_dict(session),
                }
            if issue_id is None:
                issue_id = session["issue_id"]

        auto_session = False
        if session is None and not session_id:
            # Orphan-lease prevention: a lease without a session cannot be
            # renewed by heartbeat and silently expires mid-work. Reuse the
            # caller's active same-base session for this repo, else create one.
            reuse = conn.execute(
                """
                SELECT * FROM sessions
                WHERE repo_root = ? AND owner_id = ? AND base_commit = ? AND state = 'active'
                ORDER BY heartbeat_utc DESC LIMIT 1
                """,
                (repo_root, owner_id, base_commit),
            ).fetchone()
            if reuse is not None:
                session_id = str(reuse["session_id"])
                if issue_id is None:
                    issue_id = reuse["issue_id"]
            else:
                branch_cp = git(repo_root, "rev-parse", "--abbrev-ref", "HEAD", check=False)
                branch = branch_cp.stdout.strip() if branch_cp.returncode == 0 and branch_cp.stdout.strip() else "HEAD"
                session_id = str(uuid4())
                auto_session = True
                conn.execute(
                    """
                    INSERT INTO sessions(
                      session_id, repo_root, owner_id, issue_id, branch_name, base_ref, base_commit,
                      acquired_utc, heartbeat_utc, expires_utc, worktree_path, cleanup_status, cleanup_utc,
                      hostname, pid, state
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, 'active')
                    """,
                    (
                        session_id,
                        repo_root,
                        owner_id,
                        issue_id,
                        branch,
                        base_ref,
                        base_commit,
                        iso_utc(now),
                        iso_utc(now),
                        iso_utc(expires),
                        socket.gethostname(),
                        os.getpid(),
                    ),
                )

        active_rows = conn.execute(
            """
            SELECT *
            FROM leases
            WHERE repo_root = ? AND path_rel = ? AND state = 'active'
            ORDER BY renewed_utc DESC
            """,
            (repo_root, path_rel),
        ).fetchall()
        # Supervisory model: an overlap with another owner is recorded as an
        # observation/warning, never a refusal to write. The tool always records
        # intent; the deciding agent is the one that stops on a real overlap.
        overlaps: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        for row in active_rows:
            if row["owner_id"] == owner_id:
                continue
            same_base = row["base_blob"] == base_blob or row["base_commit"] == base_commit
            overlaps_region = row["region_kind"] == "file" or region_kind == "file" or ranges_overlap(int(row["start_line"]), int(row["end_line"]), start_line, end_line)
            if not overlaps_region:
                continue
            overlaps.append(lease_to_dict(row))
            if same_base:
                warnings.append({
                    "code": "COORD_OVERLAP",
                    "message": f"active overlapping lease exists for {path_rel}",
                    "owner_id": row["owner_id"],
                    "lease_id": str(row["lease_id"]),
                    "region_id": row["region_id"],
                })
            else:
                warnings.append({
                    "code": "STALE_BASE_OBSERVED",
                    "message": f"overlapping lease for {path_rel} was recorded against a different base",
                    "owner_id": row["owner_id"],
                    "lease_id": str(row["lease_id"]),
                    "base_commit": row["base_commit"],
                })

        existing = conn.execute(
            """
            SELECT *
            FROM leases
            WHERE repo_root = ? AND path_rel = ? AND owner_id = ? AND region_kind = ?
              AND start_line = ? AND end_line = ? AND state = 'active'
            ORDER BY renewed_utc DESC
            LIMIT 1
            """,
            (repo_root, path_rel, owner_id, region_kind, start_line, end_line),
        ).fetchone()
        if existing is not None:
            conn.execute(
                """
                UPDATE leases
                SET session_id = ?, issue_id = ?, base_ref = ?, base_commit = ?, base_blob = ?,
                    region_id = ?, lease_sec = ?, renewed_utc = ?, expires_utc = ?, hostname = ?, pid = ?
                WHERE lease_id = ?
                """,
                (
                    session_id,
                    issue_id,
                    base_ref,
                    base_commit,
                    base_blob,
                    region_id,
                    lease_sec,
                    iso_utc(now),
                    iso_utc(expires),
                    socket.gethostname(),
                    os.getpid(),
                    existing["lease_id"],
                ),
            )
            lease_id = str(existing["lease_id"])
            action = "renewed_existing"
        else:
            lease_id = str(uuid4())
            conn.execute(
                """
                INSERT INTO leases(
                  lease_id, session_id, repo_root, path_rel, owner_id, issue_id, base_ref, base_commit,
                  base_blob, region_kind, region_id, start_line, end_line, lease_sec,
                  acquired_utc, renewed_utc, expires_utc, hostname, pid, state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
                """,
                (
                    lease_id,
                    session_id,
                    repo_root,
                    path_rel,
                    owner_id,
                    issue_id,
                    base_ref,
                    base_commit,
                    base_blob,
                    region_kind,
                    region_id,
                    start_line,
                    end_line,
                    lease_sec,
                    iso_utc(now),
                    iso_utc(now),
                    iso_utc(expires),
                    socket.gethostname(),
                    os.getpid(),
                ),
            )
            action = "acquired"

        row = conn.execute("SELECT * FROM leases WHERE lease_id = ?", (lease_id,)).fetchone()
        if row is None:
            raise CoordCtlError("INTERNAL_ERROR", f"lease {lease_id} not found after write")
        payload = {"action": action, "changed": True, "lease": lease_to_dict(row), "ok": True, "overlaps": overlaps, "warnings": warnings}
        emit_event(conn, "intent_acquire", lease_id, {"action": action, "lease_id": lease_id, "ok": True, "overlap_count": len(overlaps), "warning_codes": [str(w["code"]) for w in warnings]})
        conn.commit()
        return payload


def _status_query(conn: sqlite3.Connection, table: str, repo_root: str, path_rel: str | None, owner_id: str | None, issue_id: str | None, include_all: bool) -> list[dict[str, Any]]:
    query = [f"SELECT * FROM {table} WHERE repo_root = ?"]
    params: list[Any] = [repo_root]
    if not include_all:
        query.append("AND state = 'active'")
    if table == "leases" and path_rel is not None:
        query.append("AND path_rel = ?")
        params.append(path_rel)
    if owner_id is not None:
        query.append("AND owner_id = ?")
        params.append(owner_id)
    if issue_id is not None:
        query.append("AND issue_id = ?")
        params.append(issue_id)
    query.append("ORDER BY repo_root ASC")
    rows = conn.execute(" ".join(query), params).fetchall()
    mapper = lease_to_dict if table == "leases" else session_to_dict
    return [mapper(row) for row in rows]


def cmd_status(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = normalize_repo_root(args.repo_root)
    path_rel = normalize_path(repo_root, args.path) if args.path else None
    owner_id = require_owner(args.owner) if args.owner else None
    issue_id = normalize_issue(args.issue) if args.issue else None
    include_all = getattr(args, "all", False) is True
    brief = getattr(args, "brief", False) is True
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        expired_now = expire_active(conn)
        sessions = _status_query(conn, "sessions", repo_root, None, owner_id, issue_id, include_all)
        leases = _status_query(conn, "leases", repo_root, path_rel, owner_id, issue_id, include_all)
        conn.commit()
    if brief:
        # Compact supervisory view: enough to answer "is anyone here?" without
        # dumping thousands of rows.
        active_leases = [l for l in leases if l["state"] == "active"]
        active_sessions = [s for s in sessions if s["state"] == "active"]
        return {
            "active": {
                "owners": sorted({str(l["owner_id"]) for l in active_leases} | {str(s["owner_id"]) for s in active_sessions}),
                "paths": sorted({str(l["path_rel"]) for l in active_leases}),
            },
            "counts": {"sessions": len(sessions), "leases": len(leases), "active_sessions": len(active_sessions), "active_leases": len(active_leases)},
            "filters": {"all": include_all, "issue_id": issue_id, "owner_id": owner_id, "path_rel": path_rel},
            "ok": True,
            "repo_root": repo_root,
        }
    return {
        "counts": {"sessions": len(sessions), "leases": len(leases)},
        "expired_now": expired_now,
        "filters": {"all": include_all, "issue_id": issue_id, "owner_id": owner_id, "path_rel": path_rel},
        "leases": leases,
        "ok": True,
        "repo_root": repo_root,
        "sessions": sessions,
    }


def cmd_heartbeat(args: argparse.Namespace) -> dict[str, Any]:
    lease_sec = require_lease_seconds(args.lease_sec)
    now = utc_now()
    expires = now + timedelta(seconds=lease_sec)
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        expire_active(conn)
        row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (args.session_id,)).fetchone()
        if row is None:
            conn.rollback()
            return {"error": "SESSION_NOT_FOUND", "message": f"session not found: {args.session_id}", "ok": False}
        if row["state"] != "active":
            conn.rollback()
            return {"error": "SESSION_NOT_ACTIVE", "message": f"session is not active: {args.session_id}", "ok": False, "session": session_to_dict(row)}
        conn.execute(
            "UPDATE sessions SET heartbeat_utc = ?, expires_utc = ?, hostname = ?, pid = ? WHERE session_id = ?",
            (iso_utc(now), iso_utc(expires), socket.gethostname(), os.getpid(), args.session_id),
        )
        conn.execute(
            "UPDATE leases SET renewed_utc = ?, expires_utc = ?, hostname = ?, pid = ? WHERE session_id = ? AND state = 'active'",
            (iso_utc(now), iso_utc(expires), socket.gethostname(), os.getpid(), args.session_id),
        )
        updated = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (args.session_id,)).fetchone()
        if updated is None:
            raise CoordCtlError("INTERNAL_ERROR", f"session {args.session_id} not found after update")
        payload = {"action": "heartbeat", "changed": True, "ok": True, "session": session_to_dict(updated)}
        emit_event(conn, "heartbeat", args.session_id, payload)
        conn.commit()
        return payload


def cmd_release(args: argparse.Namespace) -> dict[str, Any]:
    session_id = _optional_session_id(args)
    issue_id = normalize_issue(getattr(args, "issue", None))
    lease_id = (str(getattr(args, "lease_id", None) or "").strip()) or None
    owner_id = (str(getattr(args, "owner", None) or "").strip()) or None
    all_owners = _bool_arg(args, "all_owners", False)
    repo_root = normalize_repo_root(args.repo_root) if getattr(args, "repo_root", None) else None
    raw_path = getattr(args, "path", None)
    raw_path = raw_path.strip() if isinstance(raw_path, str) and raw_path.strip() else None

    # Exactly one selector group: session XOR issue XOR lease-target
    # (lease_id/owner/path). Mixed groups would silently pick one and ignore the
    # rest, which is bad UX for a coordination tool.
    lease_target = bool(lease_id or owner_id or raw_path)
    group_count = sum([bool(session_id), bool(issue_id), lease_target])
    if group_count == 0:
        raise CoordCtlError("INVALID_ARGUMENT", "release requires --session-id, --issue, --lease-id, --owner or --path")
    if group_count > 1:
        raise CoordCtlError("INVALID_ARGUMENT", "ambiguous release selectors: use exactly one of --session-id, --issue, or a lease-target (--lease-id/--owner/--path)")
    # Broad lease-target selectors must be scoped to a repo to stay safe.
    if (issue_id or owner_id or raw_path) and repo_root is None:
        raise CoordCtlError("INVALID_ARGUMENT", "release by --issue/--owner/--path requires --repo-root")
    # --path without --owner would release every owner's lease on that path.
    if raw_path and not (owner_id or lease_id or all_owners):
        raise CoordCtlError("INVALID_ARGUMENT", "release --path affects all owners on the path; add --owner to scope it or --all-owners to confirm")
    path_rel = normalize_path(repo_root, raw_path) if raw_path else None

    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        expire_active(conn)
        sessions: list[sqlite3.Row] = []
        leases: list[sqlite3.Row] = []
        selector: dict[str, Any] = {}
        if session_id:
            selector["session_id"] = session_id
            sessions = conn.execute("SELECT * FROM sessions WHERE session_id = ? AND state = 'active'", (session_id,)).fetchall()
            leases = conn.execute("SELECT * FROM leases WHERE session_id = ? AND state = 'active'", (session_id,)).fetchall()
            conn.execute("UPDATE sessions SET state = 'released' WHERE session_id = ? AND state = 'active'", (session_id,))
            conn.execute("UPDATE leases SET state = 'released' WHERE session_id = ? AND state = 'active'", (session_id,))
        elif issue_id:
            selector["issue_id"] = issue_id
            selector["repo_root"] = repo_root
            sessions = conn.execute("SELECT * FROM sessions WHERE repo_root = ? AND issue_id = ? AND state = 'active'", (repo_root, issue_id)).fetchall()
            leases = conn.execute("SELECT * FROM leases WHERE repo_root = ? AND issue_id = ? AND state = 'active'", (repo_root, issue_id)).fetchall()
            conn.execute("UPDATE sessions SET state = 'released' WHERE repo_root = ? AND issue_id = ? AND state = 'active'", (repo_root, issue_id))
            conn.execute("UPDATE leases SET state = 'released' WHERE repo_root = ? AND issue_id = ? AND state = 'active'", (repo_root, issue_id))
        else:
            # lease-target selectors release leases only (fixes orphan/legacy
            # rows that have no session_id and no issue_id).
            conds = ["state = 'active'"]
            params: list[Any] = []
            if lease_id:
                conds.append("lease_id = ?")
                params.append(lease_id)
                selector["lease_id"] = lease_id
            if repo_root:
                conds.append("repo_root = ?")
                params.append(repo_root)
                selector["repo_root"] = repo_root
            if owner_id:
                conds.append("owner_id = ?")
                params.append(owner_id)
                selector["owner_id"] = owner_id
            if path_rel:
                conds.append("path_rel = ?")
                params.append(path_rel)
                selector["path_rel"] = path_rel
            where = " AND ".join(conds)
            leases = conn.execute(f"SELECT * FROM leases WHERE {where}", params).fetchall()
            conn.execute(f"UPDATE leases SET state = 'released' WHERE {where}", params)
        payload = {
            "action": "released",
            "changed": bool(sessions or leases),
            "ok": True,
            "selector": selector,
            "released_sessions": [session_to_dict(row) for row in sessions],
            "released_leases": [lease_to_dict(row) for row in leases],
        }
        emit_event(conn, "release", session_id or issue_id or lease_id or owner_id or path_rel, {"action": "released", "selector": selector, "released": {"sessions": len(sessions), "leases": len(leases)}, "ok": True})
        conn.commit()
        return payload


def _bool_arg(args: argparse.Namespace, name: str, default: bool = False) -> bool:
    return bool(getattr(args, name, default))


def _apply_requested(args: argparse.Namespace) -> bool:
    apply = _bool_arg(args, "apply", False)
    dry_run = _bool_arg(args, "dry_run", False)
    if apply and dry_run:
        raise CoordCtlError("INVALID_ARGUMENT", "--apply and --dry-run are mutually exclusive")
    return apply


def _git_optional(repo_root: str, *args: str) -> dict[str, Any]:
    cp = git(repo_root, *args, check=False)
    return {
        "argv": ["git", *args],
        "ok": cp.returncode == 0,
        "returncode": cp.returncode,
        "stdout": cp.stdout,
        "stderr": cp.stderr,
    }


def _parse_git_status_porcelain_z(raw: str) -> list[dict[str, Any]]:
    records = raw.split("\0")
    entries: list[dict[str, Any]] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise CoordCtlError("GIT_STATUS_PARSE_ERROR", f"unexpected git status record: {record!r}")
        xy = record[:2]
        path = record[3:]
        original_path = None
        if "R" in xy or "C" in xy:
            if index >= len(records) or not records[index]:
                raise CoordCtlError("GIT_STATUS_PARSE_ERROR", f"missing source path for git status record: {record!r}")
            original_path = records[index]
            index += 1
        untracked = xy == "??"
        unmerged = xy in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"} or "U" in xy
        entries.append(
            {
                "index_status": xy[0],
                "original_path": original_path,
                "path": path,
                "staged": xy[0] not in {" ", "?", "!"},
                "unstaged": xy[1] not in {" ", "?", "!"},
                "unmerged": unmerged,
                "untracked": untracked,
                "worktree_status": xy[1],
                "xy": xy,
            }
        )
    return entries


def _status_paths(entries: list[dict[str, Any]]) -> list[str]:
    return sorted(str(entry["path"]) for entry in entries)


def _parse_git_status_porcelain_v2_submodules(raw: str) -> dict[str, str]:
    records = raw.split("\0")
    states: dict[str, str] = {}
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        kind = record[0]
        if kind == "1":
            parts = record.split(" ", 8)
            if len(parts) >= 9 and parts[2].startswith("S"):
                states[parts[8]] = parts[2]
        elif kind == "2":
            parts = record.split(" ", 9)
            if len(parts) >= 10 and parts[2].startswith("S"):
                states[parts[9]] = parts[2]
            if index < len(records):
                index += 1
    return states


def _staged_gitlink_with_visible_submodule_dirt(entry: dict[str, Any], submodule_states: dict[str, str]) -> bool:
    if not (entry["staged"] and entry["unstaged"]):
        return False
    submodule_state = submodule_states.get(str(entry["path"]))
    if not submodule_state or len(submodule_state) < 4:
        return False
    commit_changed, tracked_dirty, untracked_dirty = submodule_state[1], submodule_state[2], submodule_state[3]
    return commit_changed == "." and (tracked_dirty != "." or untracked_dirty != ".")


def _commit_scope_analysis(repo_root: str) -> dict[str, Any]:
    cp = git(repo_root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    entries = _parse_git_status_porcelain_z(cp.stdout)
    submodule_states = _parse_git_status_porcelain_v2_submodules(
        git(repo_root, "status", "--porcelain=v2", "-z", "--untracked-files=all").stdout
    )
    unmerged_entries = [entry for entry in entries if entry["unmerged"]]
    staged_entries = [entry for entry in entries if entry["staged"] and not entry["unmerged"]]
    unstaged_entries = [entry for entry in entries if entry["unstaged"] and not entry["unmerged"]]
    staged_submodule_dirty_entries = [
        entry for entry in staged_entries if _staged_gitlink_with_visible_submodule_dirt(entry, submodule_states)
    ]
    partial_file_entries = [
        entry
        for entry in staged_entries
        if entry["unstaged"] and not _staged_gitlink_with_visible_submodule_dirt(entry, submodule_states)
    ]
    untracked_entries = [entry for entry in entries if entry["untracked"]]
    visible_uncommitted_entries = [
        entry for entry in unstaged_entries if not entry["staged"]
    ] + staged_submodule_dirty_entries + untracked_entries
    return {
        "entries": entries,
        "unmerged": unmerged_entries,
        "staged": staged_entries,
        "unstaged": unstaged_entries,
        "partial_files": partial_file_entries,
        "untracked": untracked_entries,
        "visible_uncommitted": visible_uncommitted_entries,
        "counts": {
            "entries": len(entries),
            "partial_files": len(partial_file_entries),
            "staged": len(staged_entries),
            "unmerged": len(unmerged_entries),
            "unstaged": len(unstaged_entries),
            "untracked": len(untracked_entries),
        },
        "paths": {
            "partial_files": _status_paths(partial_file_entries),
            "staged": _status_paths(staged_entries),
            "unmerged": _status_paths(unmerged_entries),
            "unstaged": _status_paths([entry for entry in unstaged_entries if not entry["staged"]]),
            "untracked": _status_paths(untracked_entries),
        },
    }


def _uncommitted_owner_state_warning(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    if not analysis["visible_uncommitted"]:
        return []
    return [
        {
            "code": "UNCOMMITTED_OWNER_STATE_VISIBLE",
            "message": "uncommitted file-level owner state is present but not part of this commit",
            "paths": _status_paths(analysis["visible_uncommitted"]),
        }
    ]


def cmd_commit_scope_report(args: argparse.Namespace) -> dict[str, Any]:
    # Supervisory: never hard-fails. Reports staged/unstaged/untracked/unmerged/
    # partial state plus warnings so the owner can decide.
    repo_root = normalize_repo_root(args.repo_root)
    analysis = _commit_scope_analysis(repo_root)
    warnings = _uncommitted_owner_state_warning(analysis)
    observations: list[dict[str, Any]] = []
    if analysis["unmerged"]:
        observations.append({"code": "UNMERGED_STATE", "paths": analysis["paths"]["unmerged"]})
    if analysis["partial_files"]:
        observations.append({"code": "PARTIAL_FILE_STAGED", "paths": analysis["paths"]["partial_files"]})
    if not analysis["staged"]:
        observations.append({"code": "NO_STAGED_CHANGES", "paths": []})
    return {
        "action": "commit_scope_report",
        "counts": analysis["counts"],
        "entries": analysis["entries"],
        "observations": observations,
        "ok": True,
        "paths": analysis["paths"],
        "policy": "Report is advisory and never blocks. File-level subset commits are allowed.",
        "ready_to_commit": not analysis["unmerged"] and not analysis["partial_files"] and bool(analysis["staged"]),
        "repo_root": repo_root,
        "warnings": warnings,
    }


def cmd_commit_scope_check(args: argparse.Namespace) -> dict[str, Any]:
    # Gate: hard-fails ONLY for genuinely dangerous states (unmerged paths,
    # partial-file staging). "No staged changes" is a warning, not a blocker.
    repo_root = normalize_repo_root(args.repo_root)
    analysis = _commit_scope_analysis(repo_root)
    warnings = _uncommitted_owner_state_warning(analysis)
    problems: list[dict[str, Any]] = []
    if analysis["unmerged"]:
        problems.append(
            {
                "code": "UNMERGED_STATE",
                "message": "repository has unmerged paths; commit scope cannot be verified",
                "paths": analysis["paths"]["unmerged"],
            }
        )
    if analysis["partial_files"]:
        problems.append(
            {
                "code": "PARTIAL_FILE_STAGED",
                "message": "a staged file also has unstaged changes; stage the complete file only if it pulls in no foreign changes, otherwise stop and ask the owner",
                "paths": analysis["paths"]["partial_files"],
            }
        )
    if not analysis["staged"]:
        warnings.append(
            {
                "code": "NO_STAGED_CHANGES",
                "message": "no staged changes are ready for commit",
                "paths": [],
            }
        )
    ok = not problems
    payload: dict[str, Any] = {
        "action": "commit_scope_check",
        "counts": analysis["counts"],
        "entries": analysis["entries"],
        "errors": problems,
        "ok": ok,
        "owner_action_required": bool(problems),
        "paths": analysis["paths"],
        "policy": "File-level subset commits are allowed. Only unmerged paths and partial-file staging require an explicit owner decision; nothing else blocks.",
        "ready_to_commit": ok and bool(analysis["staged"]),
        "repo_root": repo_root,
        "warnings": warnings,
    }
    if not ok:
        payload["error"] = problems[0]["code"]
        payload["message"] = problems[0]["message"]
    return payload


def _branch_exists(repo_root: str, branch: str) -> bool:
    return git(repo_root, "rev-parse", "--verify", f"{branch}^{{commit}}", check=False).returncode == 0


def _worktree_registered(repo_root: str, worktree_path: str | None) -> bool:
    if not worktree_path:
        return False
    cp = git(repo_root, "worktree", "list", "--porcelain", check=False)
    if cp.returncode != 0:
        return False
    target = str(Path(worktree_path).resolve())
    for line in cp.stdout.splitlines():
        if line.startswith("worktree "):
            candidate = str(Path(line.removeprefix("worktree ").strip()).resolve())
            if candidate == target:
                return True
    return False


def _cleanup_plan(session: sqlite3.Row, *, delete_worktree: bool, delete_branch: bool) -> dict[str, Any]:
    repo_root = str(session["repo_root"])
    branch = str(session["branch_name"])
    worktree_path = session["worktree_path"]
    return {
        "branch": {"delete": delete_branch, "exists": _branch_exists(repo_root, branch), "name": branch},
        "leases": {"release_active": True},
        "session": session_to_dict(session),
        "worktree": {
            "delete": delete_worktree,
            "path": worktree_path,
            "registered": _worktree_registered(repo_root, worktree_path),
        },
    }


def cmd_cleanup(args: argparse.Namespace) -> dict[str, Any]:
    session_id = str(args.session_id).strip()
    if not session_id:
        raise CoordCtlError("INVALID_ARGUMENT", "cleanup requires --session-id")
    final_state = str(args.final_state or "released").strip()
    if final_state not in FINAL_SESSION_STATES:
        raise CoordCtlError("INVALID_ARGUMENT", f"final-state must be one of: {', '.join(sorted(FINAL_SESSION_STATES))}")
    apply = _apply_requested(args)
    delete_worktree = _bool_arg(args, "delete_worktree", False)
    delete_branch = _bool_arg(args, "delete_branch", False)
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        expire_active(conn)
        session = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if session is None:
            conn.rollback()
            return {"error": "SESSION_NOT_FOUND", "message": f"session not found: {session_id}", "ok": False}
        plan = _cleanup_plan(session, delete_worktree=delete_worktree, delete_branch=delete_branch)
        if not apply:
            conn.rollback()
            return {"action": "cleanup_dry_run", "changed": False, "ok": True, "plan": plan}

        repo_root = str(session["repo_root"])
        failures: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        if delete_worktree:
            worktree = session["worktree_path"]
            if not worktree:
                failures.append({"target": "worktree", "error": "WORKTREE_NOT_RECORDED"})
            elif not _worktree_registered(repo_root, str(worktree)):
                actions.append({"target": "worktree", "changed": False, "reason": "not_registered", "path": worktree})
            else:
                result = _git_optional(repo_root, "worktree", "remove", str(worktree))
                actions.append({"target": "worktree", "path": worktree, **result})
                if not result["ok"]:
                    failures.append({"target": "worktree", "error": "WORKTREE_REMOVE_FAILED", "result": result})
        if delete_branch:
            branch = str(session["branch_name"])
            if not _branch_exists(repo_root, branch):
                actions.append({"target": "branch", "changed": False, "reason": "not_found", "branch": branch})
            else:
                result = _git_optional(repo_root, "branch", "-d", branch)
                actions.append({"target": "branch", "branch": branch, **result})
                if not result["ok"]:
                    failures.append({"target": "branch", "error": "BRANCH_DELETE_FAILED", "result": result})

        cleanup_state = "failed-cleanup" if failures else final_state
        now = iso_utc(utc_now())
        conn.execute("UPDATE leases SET state = 'released' WHERE session_id = ? AND state = 'active'", (session_id,))
        conn.execute(
            "UPDATE sessions SET state = ?, cleanup_status = ?, cleanup_utc = ? WHERE session_id = ?",
            (cleanup_state, "failed" if failures else "clean", now, session_id),
        )
        updated = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if updated is None:
            raise CoordCtlError("INTERNAL_ERROR", f"session {session_id} not found after cleanup")
        payload = {
            "action": "cleanup_apply",
            "actions": actions,
            "changed": True,
            "failures": failures,
            "ok": not failures,
            "plan": plan,
            "session": session_to_dict(updated),
        }
        emit_event(conn, "cleanup", session_id, payload)
        conn.commit()
        return payload


def _runtime_sizes() -> dict[str, int]:
    sizes: dict[str, int] = {}
    for name, path in (("events_jsonl", events_path()), ("sqlite", db_path())):
        try:
            sizes[name] = path.stat().st_size
        except OSError:
            sizes[name] = 0
    return sizes


def _rotate_events(apply: bool) -> dict[str, Any]:
    # Append-only journal rotation: archive events.jsonl into the state-dir
    # archive/ folder. The transactional coord_events table is the source of
    # truth and is intentionally left untouched (permanent audit).
    src = events_path()
    try:
        size = src.stat().st_size
    except OSError:
        size = 0
    if size == 0:
        return {"rotated": False, "reason": "empty", "bytes": 0}
    stamp = iso_utc(utc_now()).replace(":", "").replace("-", "")
    target = resolve_state_dir() / "archive" / f"events-{stamp}-{uuid4().hex[:8]}.jsonl"
    plan: dict[str, Any] = {"rotated": False, "bytes": size, "from": str(src), "to": str(target)}
    if not apply:
        return plan
    target.parent.mkdir(parents=True, exist_ok=True)
    src.rename(target)
    plan["rotated"] = True
    return plan


def cmd_gc(args: argparse.Namespace) -> dict[str, Any]:
    apply = _apply_requested(args)
    rotate_events = _bool_arg(args, "rotate_events", False)
    sizes_before = _runtime_sizes()
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        expire_active(conn)
        placeholders = ",".join("?" for _ in sorted(GC_SESSION_STATES))
        session_ids = [
            str(row["session_id"])
            for row in conn.execute(f"SELECT session_id FROM sessions WHERE state IN ({placeholders})", sorted(GC_SESSION_STATES)).fetchall()
        ]
        lease_ids = [str(row["lease_id"]) for row in conn.execute("SELECT lease_id FROM leases WHERE state IN ('expired', 'released')").fetchall()]
        if not apply:
            conn.rollback()
            payload: dict[str, Any] = {
                "action": "gc_dry_run",
                "changed": False,
                "delete_candidates": {"sessions": session_ids, "leases": lease_ids},
                "runtime_sizes": sizes_before,
                "ok": True,
            }
            if rotate_events:
                payload["events_rotation"] = _rotate_events(apply=False)
            return payload
        if lease_ids:
            conn.executemany("DELETE FROM leases WHERE lease_id = ?", [(lid,) for lid in lease_ids])
        if session_ids:
            conn.executemany("DELETE FROM sessions WHERE session_id = ?", [(sid,) for sid in session_ids])
        payload = {"action": "gc_apply", "changed": bool(session_ids or lease_ids), "deleted": {"sessions": len(session_ids), "leases": len(lease_ids)}, "runtime_sizes": sizes_before, "ok": True}
        emit_event(conn, "gc", None, payload)
        conn.commit()
    if rotate_events:
        payload["events_rotation"] = _rotate_events(apply=True)
        payload["runtime_sizes_after"] = _runtime_sizes()
    return payload


def cmd_merge_dry_run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = normalize_repo_root(args.repo_root)
    target = args.target.strip()
    branch = args.branch.strip()
    if not target or not branch:
        raise CoordCtlError("INVALID_ARGUMENT", "target and branch must not be empty")
    target_commit = resolve_commit(repo_root, target)
    branch_commit = resolve_commit(repo_root, branch)
    base_cp = git(repo_root, "merge-base", target_commit, branch_commit)
    merge_base = base_cp.stdout.strip()
    cp = git(repo_root, "merge-tree", "--write-tree", target_commit, branch_commit, check=False)
    text = f"{cp.stdout}\n{cp.stderr}".strip()
    clean = cp.returncode == 0
    payload = {
        "base_commit": merge_base,
        "branch": branch,
        "branch_commit": branch_commit,
        "clean": clean,
        "ok": clean,
        "output": text,
        "returncode": cp.returncode,
        "target": target,
        "target_commit": target_commit,
    }
    if not clean:
        payload["error"] = "MERGE_CONFLICT"
        payload["message"] = "merge dry-run found conflicts"
    return payload


def render(payload: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    elif payload.get("ok") is False:
        print(f"[{payload.get('error', 'ERROR')}] {payload.get('message', '')}", file=sys.stderr)
    else:
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coordctl",
        description="Git-aware advisory coordination for multi-agent edits.",
        epilog=textwrap.dedent(
            """
            v1 supports file and hunk leases. Semantic symbol/json_path/section regions are reserved
            and rejected until extractors are implemented.
            """
        ).strip(),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_format(command: argparse.ArgumentParser) -> None:
        command.add_argument("--format", choices=("json", "text"), default="text")

    session = sub.add_parser("session-start", help="Start an agent coordination session.")
    session.add_argument("--repo-root", required=True)
    session.add_argument("--owner", required=True)
    session.add_argument("--issue")
    session.add_argument("--branch", required=True)
    session.add_argument("--base", required=True)
    session.add_argument("--worktree-path")
    session.add_argument("--lease-sec", type=int, default=DEFAULT_LEASE_SEC)
    add_format(session)

    begin = sub.add_parser("begin", help="Cheap non-blocking entrypoint: open a session (and optional coarse intent) with autodetected repo/branch/base.")
    begin.add_argument("--repo-root", help="Defaults to the git toplevel of the current directory.")
    begin.add_argument("--owner", help="Defaults to $COORDCTL_OWNER.")
    begin.add_argument("--issue")
    begin.add_argument("--branch", help="Defaults to the current branch.")
    begin.add_argument("--base", help="Defaults to HEAD.")
    begin.add_argument("--path", help="Optional: also record a coarse file intent for this path.")
    begin.add_argument("--worktree-path")
    begin.add_argument("--lease-sec", type=int, default=DEFAULT_BEGIN_LEASE_SEC)
    add_format(begin)

    acquire = sub.add_parser("intent-acquire", help="Acquire or renew an advisory edit intent.")
    acquire.add_argument("--repo-root", required=True)
    acquire.add_argument("--path", required=True)
    acquire.add_argument("--owner", required=True)
    acquire.add_argument("--issue")
    acquire.add_argument("--base", required=True)
    acquire.add_argument("--region-kind", required=True)
    acquire.add_argument("--region-id", required=True)
    acquire.add_argument("--lease-sec", type=int, default=DEFAULT_LEASE_SEC)
    acquire.add_argument("--session-id")
    add_format(acquire)

    status = sub.add_parser("status", help="Show active sessions and leases.")
    status.add_argument("--repo-root", required=True)
    status.add_argument("--path")
    status.add_argument("--owner")
    status.add_argument("--issue")
    status.add_argument("--all", action="store_true")
    status.add_argument("--brief", action="store_true", help="Compact summary: counts plus active owners/paths, no row dumps.")
    add_format(status)

    commit_scope = sub.add_parser("commit-scope-check", help="Gate: hard-fail only on unmerged paths or partial-file staging.")
    commit_scope.add_argument("--repo-root", required=True)
    add_format(commit_scope)

    commit_scope_report = sub.add_parser("commit-scope-report", help="Advisory report of staged/unstaged/untracked/unmerged/partial state; never fails.")
    commit_scope_report.add_argument("--repo-root", required=True)
    add_format(commit_scope_report)

    heartbeat = sub.add_parser("heartbeat", help="Renew a session and its active leases.")
    heartbeat.add_argument("--session-id", required=True)
    heartbeat.add_argument("--lease-sec", type=int, default=DEFAULT_LEASE_SEC)
    add_format(heartbeat)

    release = sub.add_parser("release", help="Release active sessions and leases by session, issue, lease-id, owner or path.")
    release.add_argument("--session-id")
    release.add_argument("--repo-root")
    release.add_argument("--issue")
    release.add_argument("--lease-id")
    release.add_argument("--owner")
    release.add_argument("--path")
    release.add_argument("--all-owners", action="store_true", help="Confirm a --path release that affects every owner on the path.")
    add_format(release)

    cleanup = sub.add_parser("cleanup", help="Dry-run or apply required session cleanup.")
    cleanup.add_argument("--session-id", required=True)
    cleanup.add_argument("--final-state", choices=sorted(FINAL_SESSION_STATES), default="released")
    cleanup.add_argument("--delete-worktree", action="store_true")
    cleanup.add_argument("--delete-branch", action="store_true")
    cleanup.add_argument("--dry-run", action="store_true")
    cleanup.add_argument("--apply", action="store_true")
    add_format(cleanup)

    gc = sub.add_parser("gc", help="Dry-run or delete expired/final coordination state; optionally rotate the events journal.")
    gc.add_argument("--dry-run", action="store_true")
    gc.add_argument("--apply", action="store_true")
    gc.add_argument("--rotate-events", action="store_true", help="Archive events.jsonl into the state-dir archive/ folder (coord_events table is preserved).")
    add_format(gc)

    merge = sub.add_parser("merge-dry-run", help="Check whether target and branch can merge cleanly.")
    merge.add_argument("--repo-root", required=True)
    merge.add_argument("--target", required=True)
    merge.add_argument("--branch", required=True)
    add_format(merge)

    return parser


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "session-start":
        return cmd_session_start(args)
    if args.command == "begin":
        return cmd_begin(args)
    if args.command == "intent-acquire":
        return cmd_intent_acquire(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "commit-scope-check":
        return cmd_commit_scope_check(args)
    if args.command == "commit-scope-report":
        return cmd_commit_scope_report(args)
    if args.command == "heartbeat":
        return cmd_heartbeat(args)
    if args.command == "release":
        return cmd_release(args)
    if args.command == "cleanup":
        return cmd_cleanup(args)
    if args.command == "gc":
        return cmd_gc(args)
    if args.command == "merge-dry-run":
        return cmd_merge_dry_run(args)
    raise CoordCtlError("UNKNOWN_COMMAND", f"unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    fmt = getattr(args, "format", "text")
    try:
        payload = dispatch(args)
        render(payload, fmt)
        return EXIT_OK if payload.get("ok", True) is not False else EXIT_COMMAND_ERROR
    except CoordCtlError as exc:
        payload = {"ok": False, "error": exc.code, "message": exc.message, **exc.payload}
        render(payload, fmt)
        return EXIT_COMMAND_ERROR
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error": "UNEXPECTED_ERROR", "message": str(exc)}
        render(payload, fmt)
        return EXIT_COMMAND_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
