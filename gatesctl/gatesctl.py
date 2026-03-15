#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import subprocess
import sys
import textwrap
from datetime import datetime, timedelta, timezone
from typing import Any

import yaml


STATE_DIR = Path(os.environ.get("GATESCTL_STATE_DIR", "/home/leon/.codex/memories/gatesctl")).expanduser().resolve()
DB_PATH = STATE_DIR / "gates.sqlite"
EVENTS_PATH = STATE_DIR / "events.jsonl"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
EXIT_OK = 0
EXIT_COMMAND_ERROR = 2
RECEIPT_RE = re.compile(r"(?im)^\s*Gate-Receipt:\s*(?P<value>[A-Za-z0-9._:-]+)\s*$")
POLICY_RE = re.compile(r"(?im)^\s*Gate-Policy:\s*(?P<value>[A-Za-z0-9._:-]+)\s*$")
REFS_RE = re.compile(r"(?im)^\s*Refs\s+#(?P<value>[1-9][0-9]*)\b")
ISSUE_ID_RE = re.compile(r"^[1-9][0-9]*$")
APPROVAL_MARKER = "<!-- gatesctl:approval:v1 -->"
RECEIPT_MARKER = "<!-- gatesctl:receipt:v1 -->"
LOCKCTL_BIN = os.environ.get("LOCKCTL_BIN", "lockctl")


class GatesCtlError(Exception):
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
        CREATE TABLE IF NOT EXISTS scopes (
          scope_id TEXT PRIMARY KEY,
          repo_root TEXT NOT NULL,
          issue_id TEXT NOT NULL,
          scope_fingerprint TEXT NOT NULL,
          policy_version TEXT NOT NULL,
          files_json TEXT NOT NULL,
          scope_kind_json TEXT NOT NULL,
          created_utc TEXT NOT NULL,
          UNIQUE(repo_root, issue_id, scope_fingerprint, policy_version)
        );

        CREATE TABLE IF NOT EXISTS gates (
          policy_version TEXT NOT NULL,
          stage TEXT NOT NULL,
          name TEXT NOT NULL,
          kind TEXT NOT NULL,
          role_required TEXT NOT NULL,
          scope_selector_json TEXT NOT NULL,
          stale_on_fingerprint_change INTEGER NOT NULL,
          allow_waive INTEGER NOT NULL,
          PRIMARY KEY(policy_version, stage, name)
        );

        CREATE TABLE IF NOT EXISTS approval_events (
          event_id TEXT PRIMARY KEY,
          repo_root TEXT NOT NULL,
          issue_id TEXT NOT NULL,
          scope_fingerprint TEXT NOT NULL,
          gate_name TEXT NOT NULL,
          decision TEXT NOT NULL,
          actor TEXT NOT NULL,
          role TEXT NOT NULL,
          evidence_ref TEXT NOT NULL,
          source TEXT NOT NULL,
          issued_utc TEXT NOT NULL,
          raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS receipts (
          receipt_id TEXT PRIMARY KEY,
          repo_root TEXT NOT NULL,
          issue_id TEXT NOT NULL,
          scope_fingerprint TEXT NOT NULL,
          stage TEXT NOT NULL,
          policy_version TEXT NOT NULL,
          status TEXT NOT NULL,
          gates_json TEXT NOT NULL,
          created_utc TEXT NOT NULL,
          updated_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS commit_bindings (
          commit_sha TEXT PRIMARY KEY,
          receipt_id TEXT NOT NULL,
          issue_id TEXT NOT NULL,
          repo_root TEXT NOT NULL,
          bound_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS issue_sync (
          repo_root TEXT NOT NULL,
          issue_id TEXT NOT NULL,
          scope_fingerprint TEXT NOT NULL,
          issue_state TEXT NOT NULL,
          labels_json TEXT NOT NULL,
          body_hash TEXT NOT NULL,
          synced_utc TEXT NOT NULL,
          raw_json TEXT NOT NULL,
          PRIMARY KEY(repo_root, issue_id, scope_fingerprint)
        );

        CREATE TABLE IF NOT EXISTS events (
          event_seq INTEGER PRIMARY KEY AUTOINCREMENT,
          event_type TEXT NOT NULL,
          created_utc TEXT NOT NULL,
          payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_scopes_repo_issue ON scopes(repo_root, issue_id, created_utc);
        CREATE INDEX IF NOT EXISTS idx_approval_events_lookup ON approval_events(repo_root, issue_id, scope_fingerprint, gate_name, issued_utc);
        CREATE INDEX IF NOT EXISTS idx_receipts_lookup ON receipts(repo_root, issue_id, stage, updated_utc);
        CREATE INDEX IF NOT EXISTS idx_commit_bindings_receipt ON commit_bindings(receipt_id);
        CREATE INDEX IF NOT EXISTS idx_issue_sync_lookup ON issue_sync(repo_root, issue_id, synced_utc);
        """
    )
    return conn


def emit_event(conn: sqlite3.Connection, event_type: str, payload: dict[str, Any]) -> None:
    created_utc = iso_utc(utc_now())
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    conn.execute(
        "INSERT INTO events (event_type, created_utc, payload_json) VALUES (?, ?, ?)",
        (event_type, created_utc, encoded),
    )
    with EVENTS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"event_type": event_type, "created_utc": created_utc, "payload": payload}, ensure_ascii=False))
        fh.write("\n")


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def resolve_repo_root(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    probe = _run(["git", "rev-parse", "--show-toplevel"], cwd=Path.cwd())
    if probe.returncode == 0 and probe.stdout.strip():
        return Path(probe.stdout.strip()).resolve()
    raise GatesCtlError("REPO_ROOT_REQUIRED", "не удалось определить корень репозитория; передайте --repo-root явно")


def normalize_path(path_value: str, repo_root: Path) -> str:
    cleaned = path_value.strip().replace("\\", "/")
    p = PurePosixPath(cleaned)
    if p.is_absolute():
        abs_target = Path(str(p)).resolve()
        try:
            return abs_target.relative_to(repo_root.resolve()).as_posix()
        except ValueError as exc:
            raise GatesCtlError("INVALID_PATH", f"path escapes repository root: {path_value}") from exc

    normalized = os.path.normpath(str(p)).replace("\\", "/")
    if normalized in {".", ""}:
        raise GatesCtlError("INVALID_PATH", f"empty path is not allowed: {path_value}")
    if normalized == ".." or normalized.startswith("../"):
        raise GatesCtlError("INVALID_PATH", f"path escapes repository root: {path_value}")
    abs_target = (repo_root / normalized).resolve()
    try:
        abs_target.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise GatesCtlError("INVALID_PATH", f"path escapes repository root: {path_value}") from exc
    return normalized


def collect_files(repo_root: Path, args: argparse.Namespace, *, allow_empty: bool = False) -> list[str]:
    collected: list[str] = []
    for item in getattr(args, "files", []) or []:
        if str(item).strip():
            collected.append(str(item).strip())
    files_csv = getattr(args, "files_csv", None)
    if files_csv:
        for chunk in files_csv.split(","):
            token = chunk.strip()
            if token:
                collected.append(token)
    if getattr(args, "staged", False):
        cp = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRD", "-z"], cwd=repo_root)
        if cp.returncode != 0:
            raise GatesCtlError("GIT_FAILED", cp.stderr.strip() or "cannot read staged files")
        collected.extend([item for item in cp.stdout.split("\0") if item])
    range_value = getattr(args, "range", None)
    if range_value:
        cp = _run(["git", "diff", "--name-only", range_value], cwd=repo_root)
        if cp.returncode != 0:
            raise GatesCtlError("GIT_FAILED", cp.stderr.strip() or f"invalid range: {range_value}")
        collected.extend([line.strip() for line in cp.stdout.splitlines() if line.strip()])

    normalized = [normalize_path(item, repo_root) for item in collected]
    seen: set[str] = set()
    unique: list[str] = []
    for item in normalized:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)

    if not unique and not allow_empty:
        raise GatesCtlError("NO_FILES", "не удалось определить scope файлов; передайте --files/--files-csv/--staged/--range")
    return unique


def digest_text(prefix: str, values: list[str]) -> str:
    digest = hashlib.sha256()
    digest.update(prefix.encode("utf-8"))
    for value in values:
        digest.update(b"\0")
        digest.update(value.encode("utf-8"))
    return digest.hexdigest()


def current_file_hash(repo_root: Path, path_rel: str) -> str:
    abs_path = (repo_root / path_rel).resolve()
    if abs_path.is_file():
        cp = _run(["git", "hash-object", "--", str(abs_path)], cwd=repo_root)
        if cp.returncode == 0 and cp.stdout.strip():
            return cp.stdout.strip()
        return digest_text("fallback-file", [path_rel, abs_path.read_text(encoding="utf-8", errors="ignore")])

    cp = _run(["git", "rev-parse", f"HEAD:{path_rel}"], cwd=repo_root)
    if cp.returncode == 0 and cp.stdout.strip():
        return f"deleted:{cp.stdout.strip()}"
    return "__missing__"


def compute_scope_fingerprint(repo_root: Path, issue_id: str, files: list[str]) -> str:
    parts = [str(repo_root.resolve()), issue_id]
    for path_rel in sorted(files):
        parts.append(f"{path_rel}:{current_file_hash(repo_root, path_rel)}")
    return digest_text("scope", parts)


def scope_id_for(repo_root: Path, issue_id: str, scope_fingerprint: str, policy_version: str) -> str:
    return digest_text("scope-id", [str(repo_root.resolve()), issue_id, scope_fingerprint, policy_version])[:24]


def receipt_id_for(issue_id: str, stage: str, scope_fingerprint: str, policy_version: str) -> str:
    return f"gr_v1_{digest_text('receipt', [issue_id, stage, scope_fingerprint, policy_version])[:16]}"


def event_id_for(prefix: str, values: list[str]) -> str:
    return f"{prefix}_{digest_text(prefix, values)[:20]}"


def resolve_policy_path(repo_root: Path, explicit_path: str | None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    return (repo_root / ".agents" / "policy" / "gates.v1.yaml").resolve()


def load_policy(policy_path: Path) -> dict[str, Any]:
    if not policy_path.exists():
        raise GatesCtlError("POLICY_INVALID", f"policy file not found: {policy_path}")
    payload = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise GatesCtlError("POLICY_INVALID", "policy root must be an object")
    for key in ("policy_version", "scope_rules", "stages", "gate_definitions"):
        if key not in payload:
            raise GatesCtlError("POLICY_INVALID", f"missing policy key: {key}")
    if not isinstance(payload["scope_rules"], list):
        raise GatesCtlError("POLICY_INVALID", "scope_rules must be a list")
    if not isinstance(payload["stages"], dict) or not payload["stages"]:
        raise GatesCtlError("POLICY_INVALID", "stages must be a non-empty object")
    if not isinstance(payload["gate_definitions"], dict) or not payload["gate_definitions"]:
        raise GatesCtlError("POLICY_INVALID", "gate_definitions must be a non-empty object")
    return payload


def match_pattern(path_rel: str, pattern: str) -> bool:
    return fnmatch.fnmatch(path_rel, pattern)


def classify_scope_kinds(files: list[str], policy: dict[str, Any]) -> list[str]:
    matched: list[str] = []
    for rule in policy.get("scope_rules", []):
        if not isinstance(rule, dict):
            continue
        kind = str(rule.get("kind", "")).strip()
        patterns = rule.get("patterns", [])
        if not kind or not isinstance(patterns, list):
            continue
        if any(isinstance(pattern, str) and pattern and match_pattern(path_rel, pattern) for pattern in patterns for path_rel in files):
            matched.append(kind)
    if not matched:
        matched.append("unclassified")
    seen: set[str] = set()
    result: list[str] = []
    for item in matched:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def required_gates_for_stage(stage: str, scope_kinds: list[str], policy: dict[str, Any]) -> list[str]:
    stage_cfg = policy.get("stages", {}).get(stage)
    if not isinstance(stage_cfg, dict):
        raise GatesCtlError("POLICY_INVALID", f"stage `{stage}` is not defined in policy")
    ordered: list[str] = []
    for item in stage_cfg.get("always", []) or []:
        if isinstance(item, str) and item.strip():
            ordered.append(item.strip())
    by_kind = stage_cfg.get("by_kind", {}) or {}
    if isinstance(by_kind, dict):
        for kind in scope_kinds:
            values = by_kind.get(kind, []) or []
            if isinstance(values, list):
                for item in values:
                    if isinstance(item, str) and item.strip():
                        ordered.append(item.strip())
    seen: set[str] = set()
    result: list[str] = []
    for gate_name in ordered:
        if gate_name in seen:
            continue
        seen.add(gate_name)
        result.append(gate_name)
    return result


def sync_policy_to_db(conn: sqlite3.Connection, policy: dict[str, Any]) -> None:
    policy_version = str(policy["policy_version"])
    gate_defs = policy.get("gate_definitions", {})
    for stage, stage_cfg in (policy.get("stages", {}) or {}).items():
        if not isinstance(stage_cfg, dict):
            continue
        for gate_name in required_gates_for_stage(str(stage), list(policy.get("role_aliases", {}).keys()) + ["migration", "backend-runtime", "web-ui", "docs-boundary", "major-change", "release-main", "unclassified"], policy):
            gate_def = gate_defs.get(gate_name, {})
            if not isinstance(gate_def, dict):
                gate_def = {}
            role_required = gate_def.get("role_required", [])
            if not isinstance(role_required, list):
                role_required = []
            scope_selector = gate_def.get("scope_selector", {})
            conn.execute(
                """
                INSERT INTO gates (policy_version, stage, name, kind, role_required, scope_selector_json, stale_on_fingerprint_change, allow_waive)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(policy_version, stage, name) DO UPDATE SET
                  kind = excluded.kind,
                  role_required = excluded.role_required,
                  scope_selector_json = excluded.scope_selector_json,
                  stale_on_fingerprint_change = excluded.stale_on_fingerprint_change,
                  allow_waive = excluded.allow_waive
                """,
                (
                    policy_version,
                    str(stage),
                    gate_name,
                    str(gate_def.get("kind", "auto")),
                    json.dumps(role_required, ensure_ascii=False),
                    json.dumps(scope_selector, ensure_ascii=False, sort_keys=True),
                    1 if gate_def.get("stale_on_fingerprint_change", True) else 0,
                    1 if gate_def.get("allow_waive", False) else 0,
                ),
            )


def plan_scope_payload(repo_root: Path, issue_id: str, files: list[str], policy: dict[str, Any]) -> dict[str, Any]:
    if not ISSUE_ID_RE.match(issue_id):
        raise GatesCtlError("INVALID_ISSUE_ID", f"`{issue_id}` is not numeric issue id")
    scope_kinds = classify_scope_kinds(files, policy)
    policy_version = str(policy["policy_version"])
    scope_fingerprint = compute_scope_fingerprint(repo_root, issue_id, files)
    return {
        "repo_root": str(repo_root),
        "issue_id": issue_id,
        "files": files,
        "scope_kinds": scope_kinds,
        "scope_fingerprint": scope_fingerprint,
        "policy_version": policy_version,
        "scope_id": scope_id_for(repo_root, issue_id, scope_fingerprint, policy_version),
    }


def upsert_scope(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO scopes (scope_id, repo_root, issue_id, scope_fingerprint, policy_version, files_json, scope_kind_json, created_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(repo_root, issue_id, scope_fingerprint, policy_version) DO NOTHING
        """,
        (
            payload["scope_id"],
            payload["repo_root"],
            payload["issue_id"],
            payload["scope_fingerprint"],
            payload["policy_version"],
            json.dumps(payload["files"], ensure_ascii=False),
            json.dumps(payload["scope_kinds"], ensure_ascii=False),
            iso_utc(utc_now()),
        ),
    )


def resolve_repo_name(repo_root: Path, explicit_repo: str | None) -> str:
    if explicit_repo:
        return explicit_repo
    cp = _run(["git", "config", "--get", "remote.origin.url"], cwd=repo_root)
    if cp.returncode != 0 or not cp.stdout.strip():
        raise GatesCtlError("ISSUE_SYNC_FAILED", "cannot resolve remote.origin.url; pass --repo OWNER/REPO")
    remote = cp.stdout.strip()
    ssh_match = re.match(r"git@github\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?$", remote)
    https_match = re.match(r"https://github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?$", remote)
    match = ssh_match or https_match
    if not match:
        raise GatesCtlError("ISSUE_SYNC_FAILED", f"unsupported GitHub remote URL: {remote}")
    return str(match.group("repo"))


def gh_json(repo_root: Path, cmd: list[str]) -> Any:
    cp = _run(cmd, cwd=repo_root)
    if cp.returncode != 0:
        raise GatesCtlError("ISSUE_SYNC_FAILED", cp.stderr.strip() or cp.stdout.strip() or "gh command failed")
    try:
        return json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise GatesCtlError("ISSUE_SYNC_FAILED", "invalid JSON from gh command") from exc


def extract_json_after_marker(body: str, marker: str) -> dict[str, Any] | None:
    if marker not in body:
        return None
    suffix = body.split(marker, 1)[1].strip()
    if suffix.startswith("```json"):
        suffix = suffix[len("```json"):].strip()
        if suffix.endswith("```"):
            suffix = suffix[:-3].strip()
    try:
        parsed = json.loads(suffix)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def sync_issue_events(
    conn: sqlite3.Connection,
    repo_root: Path,
    repo_name: str,
    issue_id: str,
    scope_fingerprint: str,
) -> dict[str, Any]:
    issue_payload = gh_json(
        repo_root,
        ["gh", "issue", "view", issue_id, "-R", repo_name, "--json", "number,state,title,body,labels"],
    )
    comments_payload = gh_json(
        repo_root,
        ["gh", "api", f"repos/{repo_name}/issues/{issue_id}/comments?per_page=100"],
    )
    labels = sorted(item.get("name", "") for item in issue_payload.get("labels", []) if isinstance(item, dict) and item.get("name"))
    body_text = str(issue_payload.get("body", ""))
    body_hash = digest_text("issue-body", [body_text, *labels])
    sync_row = {
        "issue_state": str(issue_payload.get("state", "")),
        "labels": labels,
        "body_hash": body_hash,
        "synced_utc": iso_utc(utc_now()),
        "raw": issue_payload,
    }
    conn.execute(
        """
        INSERT INTO issue_sync (repo_root, issue_id, scope_fingerprint, issue_state, labels_json, body_hash, synced_utc, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(repo_root, issue_id, scope_fingerprint) DO UPDATE SET
          issue_state = excluded.issue_state,
          labels_json = excluded.labels_json,
          body_hash = excluded.body_hash,
          synced_utc = excluded.synced_utc,
          raw_json = excluded.raw_json
        """,
        (
            str(repo_root),
            issue_id,
            scope_fingerprint,
            sync_row["issue_state"],
            json.dumps(labels, ensure_ascii=False),
            body_hash,
            sync_row["synced_utc"],
            json.dumps(issue_payload, ensure_ascii=False),
        ),
    )

    imported = 0
    if isinstance(comments_payload, list):
        for comment in comments_payload:
            if not isinstance(comment, dict):
                continue
            body = str(comment.get("body", ""))
            payload = extract_json_after_marker(body, APPROVAL_MARKER)
            if not payload:
                continue
            gate_name = str(payload.get("gate_name", "")).strip()
            decision = str(payload.get("decision", "")).strip()
            role = str(payload.get("role", "")).strip()
            actor = str(payload.get("actor", "")).strip()
            event_scope = str(payload.get("scope_fingerprint", "")).strip()
            if not gate_name or not decision or not role or not actor or not event_scope:
                continue
            event_id = event_id_for(
                "gh",
                [
                    str(comment.get("id", "")),
                    issue_id,
                    gate_name,
                    event_scope,
                    decision,
                    actor,
                    role,
                ],
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO approval_events
                (event_id, repo_root, issue_id, scope_fingerprint, gate_name, decision, actor, role, evidence_ref, source, issued_utc, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    str(repo_root),
                    issue_id,
                    event_scope,
                    gate_name,
                    decision,
                    actor,
                    role,
                    str(payload.get("evidence_ref", f"github-comment:{comment.get('id', '')}")),
                    "github",
                    str(comment.get("created_at", iso_utc(utc_now()))),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            imported += 1

    emit_event(
        conn,
        "sync_issue",
        {
            "repo_root": str(repo_root),
            "issue_id": issue_id,
            "scope_fingerprint": scope_fingerprint,
            "imported_events": imported,
            "issue_state": sync_row["issue_state"],
            "labels": labels,
        },
    )
    return {"imported_events": imported, "issue_state": sync_row["issue_state"], "labels": labels, "body_hash": body_hash}


def get_gate_definition(policy: dict[str, Any], gate_name: str) -> dict[str, Any]:
    gate_defs = policy.get("gate_definitions", {})
    if gate_name not in gate_defs or not isinstance(gate_defs[gate_name], dict):
        raise GatesCtlError("POLICY_INVALID", f"gate `{gate_name}` is not defined in gate_definitions")
    return gate_defs[gate_name]


def latest_approval_event(
    conn: sqlite3.Connection,
    repo_root: Path,
    issue_id: str,
    scope_fingerprint: str,
    gate_name: str,
) -> sqlite3.Row | None:
    row = conn.execute(
        """
        SELECT * FROM approval_events
        WHERE repo_root = ? AND issue_id = ? AND scope_fingerprint = ? AND gate_name = ?
        ORDER BY issued_utc DESC, event_id DESC
        LIMIT 1
        """,
        (str(repo_root), issue_id, scope_fingerprint, gate_name),
    ).fetchone()
    return row


def resolve_lockctl_bin() -> str:
    candidate = LOCKCTL_BIN.strip()
    if not candidate:
        raise GatesCtlError("LOCK_CONFLICT", "lockctl command is empty")
    if "/" in candidate:
        path = Path(candidate).expanduser()
        if path.exists():
            return str(path)
        raise GatesCtlError("LOCK_CONFLICT", f"missing lockctl: {path}")
    resolved = shutil.which(candidate)
    if resolved:
        return resolved
    raise GatesCtlError("LOCK_CONFLICT", f"missing lockctl in PATH: {candidate}")


def verify_lock_scope(repo_root: Path, issue_id: str, files: list[str]) -> dict[str, Any]:
    lockctl = resolve_lockctl_bin()
    problems: list[str] = []
    for path_rel in files:
        cp = _run([lockctl, "status", "--repo-root", str(repo_root), "--path", path_rel, "--format", "json"], cwd=repo_root)
        if cp.returncode != 0:
            problems.append(f"{path_rel}: lockctl status failed")
            continue
        try:
            payload = json.loads(cp.stdout) if cp.stdout.strip() else {}
        except json.JSONDecodeError:
            problems.append(f"{path_rel}: invalid JSON from lockctl")
            continue
        active = payload.get("active", [])
        active_ids = sorted({str(item.get("issue_id")) for item in active if isinstance(item, dict) and item.get("issue_id")})
        if active_ids != [issue_id]:
            if active_ids:
                problems.append(f"{path_rel}: active lock belongs to other issue(s): {', '.join(active_ids)}")
            else:
                problems.append(f"{path_rel}: no active lock for issue #{issue_id}")
    return {"ok": not problems, "problems": problems}


def check_issue_open(repo_root: Path, repo_name: str, issue_id: str) -> dict[str, Any]:
    payload = gh_json(repo_root, ["gh", "issue", "view", issue_id, "-R", repo_name, "--json", "state"])
    state = str(payload.get("state", "")).upper()
    return {"ok": state == "OPEN", "state": state}


def approval_comment_body(payload: dict[str, Any]) -> str:
    return f"{APPROVAL_MARKER}\n{json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)}\n"


def receipt_comment_body(payload: dict[str, Any]) -> str:
    return f"{RECEIPT_MARKER}\n{json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)}\n"


def post_issue_comment(repo_root: Path, repo_name: str, issue_id: str, body: str) -> None:
    cp = _run(["gh", "issue", "comment", issue_id, "-R", repo_name, "--body", body], cwd=repo_root)
    if cp.returncode != 0:
        raise GatesCtlError("ISSUE_SYNC_FAILED", cp.stderr.strip() or cp.stdout.strip() or "gh issue comment failed")


def parse_commit_metadata(message: str) -> dict[str, str]:
    refs = sorted(set(match.group("value") for match in REFS_RE.finditer(message)))
    receipts = sorted(set(match.group("value") for match in RECEIPT_RE.finditer(message)))
    policies = sorted(set(match.group("value") for match in POLICY_RE.finditer(message)))
    if not refs:
        raise GatesCtlError("MISSING_REFS", "commit message does not contain `Refs #<id>`")
    if len(refs) > 1:
        raise GatesCtlError("MULTI_ISSUE", f"commit message references multiple issues: {', '.join(refs)}")
    if not receipts:
        raise GatesCtlError("MISSING_RECEIPT", "commit message does not contain `Gate-Receipt:` trailer")
    if len(receipts) > 1:
        raise GatesCtlError("MISSING_RECEIPT", f"commit message references multiple receipts: {', '.join(receipts)}")
    if not policies:
        raise GatesCtlError("POLICY_INVALID", "commit message does not contain `Gate-Policy:` trailer")
    if len(policies) > 1:
        raise GatesCtlError("POLICY_INVALID", f"commit message references multiple policies: {', '.join(policies)}")
    return {"issue_id": refs[0], "receipt_id": receipts[0], "policy_version": policies[0]}


def commit_message(repo_root: Path, commit: str) -> str:
    cp = _run(["git", "show", "-s", "--format=%B", commit], cwd=repo_root)
    if cp.returncode != 0:
        raise GatesCtlError("GIT_FAILED", cp.stderr.strip() or f"cannot read commit {commit}")
    return cp.stdout


def normalize_commit_sha(repo_root: Path, commit: str) -> str:
    cp = _run(["git", "rev-parse", "--verify", commit], cwd=repo_root)
    if cp.returncode != 0:
        raise GatesCtlError("GIT_FAILED", cp.stderr.strip() or f"cannot resolve commit {commit}")
    return cp.stdout.strip()


def receipt_row(conn: sqlite3.Connection, receipt_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM receipts WHERE receipt_id = ?", (receipt_id,)).fetchone()


def scope_row(conn: sqlite3.Connection, repo_root: Path, issue_id: str, scope_fingerprint: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT * FROM scopes
        WHERE repo_root = ? AND issue_id = ? AND scope_fingerprint = ?
        ORDER BY created_utc DESC
        LIMIT 1
        """,
        (str(repo_root), issue_id, scope_fingerprint),
    ).fetchone()


def build_receipt_gates(
    conn: sqlite3.Connection,
    repo_root: Path,
    repo_name: str,
    issue_id: str,
    stage: str,
    scope_payload: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    required = required_gates_for_stage(stage, scope_payload["scope_kinds"], policy)
    result: list[dict[str, Any]] = []
    for gate_name in required:
        gate_def = get_gate_definition(policy, gate_name)
        gate_kind = str(gate_def.get("kind", "auto"))
        allow_waive = bool(gate_def.get("allow_waive", False))
        allowed_roles = [str(item) for item in gate_def.get("role_required", []) if isinstance(item, str) and item.strip()]
        entry: dict[str, Any] = {
            "gate_name": gate_name,
            "gate_kind": gate_kind,
            "required_roles": allowed_roles,
            "verdict": "blocked",
            "reason": "",
            "evidence_ref": "",
            "source": "",
        }

        if gate_name == "lock-scope":
            lock_result = verify_lock_scope(repo_root, issue_id, scope_payload["files"])
            if lock_result["ok"]:
                entry.update({"verdict": "ok", "reason": "active lockctl leases match issue", "source": "lockctl"})
            else:
                entry.update({"reason": "; ".join(lock_result["problems"]), "source": "lockctl"})
            result.append(entry)
            continue

        if gate_name == "issue-open":
            issue_result = check_issue_open(repo_root, repo_name, issue_id)
            if issue_result["ok"]:
                entry.update({"verdict": "ok", "reason": "issue state is OPEN", "source": "github"})
            else:
                entry.update({"reason": f"issue state is {issue_result['state']}, expected OPEN", "source": "github"})
            result.append(entry)
            continue

        event = latest_approval_event(conn, repo_root, issue_id, scope_payload["scope_fingerprint"], gate_name)
        if event is None:
            entry.update({"reason": "missing approval event for current scope_fingerprint"})
            result.append(entry)
            continue

        decision = str(event["decision"])
        role = str(event["role"])
        if decision == "reject":
            entry.update({"reason": f"gate rejected by {event['actor']}", "source": str(event["source"]), "evidence_ref": str(event["evidence_ref"])})
            result.append(entry)
            continue
        if decision == "waive":
            if allow_waive:
                entry.update({"verdict": "ok", "reason": f"gate waived by {event['actor']}", "source": str(event["source"]), "evidence_ref": str(event["evidence_ref"])})
            else:
                entry.update({"reason": "waive is not allowed for this gate", "source": str(event["source"]), "evidence_ref": str(event["evidence_ref"])})
            result.append(entry)
            continue
        if decision != "approve":
            entry.update({"reason": f"unsupported approval decision: {decision}", "source": str(event["source"]), "evidence_ref": str(event["evidence_ref"])})
            result.append(entry)
            continue
        if gate_kind == "human" and allowed_roles and role not in allowed_roles:
            entry.update({"reason": f"role mismatch: `{role}` not in {', '.join(allowed_roles)}", "source": str(event["source"]), "evidence_ref": str(event["evidence_ref"])})
            result.append(entry)
            continue
        entry.update({"verdict": "ok", "reason": f"approved by {event['actor']}", "source": str(event["source"]), "evidence_ref": str(event["evidence_ref"])})
        result.append(entry)
    return result


def store_receipt(
    conn: sqlite3.Connection,
    repo_root: Path,
    issue_id: str,
    stage: str,
    scope_payload: dict[str, Any],
    policy_version: str,
    gates_payload: list[dict[str, Any]],
) -> dict[str, Any]:
    receipt_id = receipt_id_for(issue_id, stage, scope_payload["scope_fingerprint"], policy_version)
    status = "ok" if all(item.get("verdict") == "ok" for item in gates_payload) else "blocked"
    now_utc = iso_utc(utc_now())
    bound = conn.execute("SELECT 1 FROM commit_bindings WHERE receipt_id = ? LIMIT 1", (receipt_id,)).fetchone()
    existing = receipt_row(conn, receipt_id)
    if existing and bound:
        return {
            "receipt_id": receipt_id,
            "status": str(existing["status"]),
            "created_utc": str(existing["created_utc"]),
            "updated_utc": str(existing["updated_utc"]),
            "gates": json.loads(str(existing["gates_json"])),
        }

    created_utc = now_utc if existing is None else str(existing["created_utc"])
    conn.execute(
        """
        INSERT INTO receipts (receipt_id, repo_root, issue_id, scope_fingerprint, stage, policy_version, status, gates_json, created_utc, updated_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(receipt_id) DO UPDATE SET
          status = excluded.status,
          gates_json = excluded.gates_json,
          updated_utc = excluded.updated_utc
        """,
        (
            receipt_id,
            str(repo_root),
            issue_id,
            scope_payload["scope_fingerprint"],
            stage,
            policy_version,
            status,
            json.dumps(gates_payload, ensure_ascii=False),
            created_utc,
            now_utc,
        ),
    )
    emit_event(
        conn,
        "verify_receipt",
        {
            "receipt_id": receipt_id,
            "repo_root": str(repo_root),
            "issue_id": issue_id,
            "stage": stage,
            "status": status,
            "scope_fingerprint": scope_payload["scope_fingerprint"],
        },
    )
    return {"receipt_id": receipt_id, "status": status, "created_utc": created_utc, "updated_utc": now_utc, "gates": gates_payload}


def json_print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def cmd_plan_scope(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = resolve_repo_root(args.repo_root)
    policy = load_policy(resolve_policy_path(repo_root, args.policy_file))
    files = collect_files(repo_root, args)
    payload = plan_scope_payload(repo_root, args.issue, files, policy)
    stages = list((policy.get("stages", {}) or {}).keys())
    payload["required_gates_by_stage"] = {
        stage: required_gates_for_stage(stage, payload["scope_kinds"], policy)
        for stage in stages
    }
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        sync_policy_to_db(conn, policy)
        upsert_scope(conn, payload)
        emit_event(conn, "plan_scope", payload)
        conn.commit()
    return {"ok": True, **payload}


def cmd_sync_issue(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = resolve_repo_root(args.repo_root)
    repo_name = resolve_repo_name(repo_root, args.repo)
    scope_fingerprint = args.scope_fingerprint.strip()
    if not scope_fingerprint:
        raise GatesCtlError("ISSUE_SYNC_FAILED", "--scope-fingerprint is required")
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        payload = sync_issue_events(conn, repo_root, repo_name, args.issue, scope_fingerprint)
        conn.commit()
    return {"ok": True, "repo_root": str(repo_root), "issue_id": args.issue, "scope_fingerprint": scope_fingerprint, **payload}


def cmd_approve(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = resolve_repo_root(args.repo_root)
    policy = load_policy(resolve_policy_path(repo_root, args.policy_file))
    scope_fingerprint = str(getattr(args, "scope_fingerprint", "") or "").strip()
    files: list[str] = []
    if not scope_fingerprint:
        files = collect_files(repo_root, args)
        scope_fingerprint = plan_scope_payload(repo_root, args.issue, files, policy)["scope_fingerprint"]
    gate_name = args.gate.strip()
    gate_def = get_gate_definition(policy, gate_name)
    decision = args.decision.strip()
    if decision not in {"approve", "reject", "waive"}:
        raise GatesCtlError("POLICY_INVALID", f"unsupported decision: {decision}")
    actor = (args.actor or os.environ.get("USER") or "unknown").strip()
    role = (args.role or ("system" if gate_def.get("kind", "auto") == "auto" else "unknown")).strip()
    evidence_ref = (args.evidence_ref or "").strip()
    issued_utc = iso_utc(utc_now())
    event_id = event_id_for(
        "ap",
        [str(repo_root), args.issue, scope_fingerprint, gate_name, decision, actor, role, evidence_ref, args.source],
    )
    payload = {
        "event_id": event_id,
        "repo_root": str(repo_root),
        "issue_id": args.issue,
        "scope_fingerprint": scope_fingerprint,
        "gate_name": gate_name,
        "decision": decision,
        "actor": actor,
        "role": role,
        "evidence_ref": evidence_ref,
        "source": args.source,
        "issued_utc": issued_utc,
    }
    repo_name = resolve_repo_name(repo_root, args.repo) if args.post_issue else ""
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT OR REPLACE INTO approval_events
            (event_id, repo_root, issue_id, scope_fingerprint, gate_name, decision, actor, role, evidence_ref, source, issued_utc, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                str(repo_root),
                args.issue,
                scope_fingerprint,
                gate_name,
                decision,
                actor,
                role,
                evidence_ref,
                args.source,
                issued_utc,
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        emit_event(conn, "approval_event", payload)
        conn.commit()

    if args.post_issue:
        post_issue_comment(repo_root, repo_name, args.issue, approval_comment_body(payload))
    return {"ok": True, **payload, "posted_issue_comment": bool(args.post_issue)}


def cmd_verify(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = resolve_repo_root(args.repo_root)
    policy = load_policy(resolve_policy_path(repo_root, args.policy_file))
    files = collect_files(repo_root, args)
    scope_payload = plan_scope_payload(repo_root, args.issue, files, policy)
    repo_name = resolve_repo_name(repo_root, args.repo)
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        sync_policy_to_db(conn, policy)
        upsert_scope(conn, scope_payload)
        if args.sync_issue:
            sync_issue_events(conn, repo_root, repo_name, args.issue, scope_payload["scope_fingerprint"])
        gates_payload = build_receipt_gates(conn, repo_root, repo_name, args.issue, args.stage, scope_payload, policy)
        receipt_payload = store_receipt(conn, repo_root, args.issue, args.stage, scope_payload, str(policy["policy_version"]), gates_payload)
        conn.commit()
    return {
        "ok": receipt_payload["status"] == "ok",
        "repo_root": str(repo_root),
        "issue_id": args.issue,
        "stage": args.stage,
        "policy_version": str(policy["policy_version"]),
        "scope_fingerprint": scope_payload["scope_fingerprint"],
        "scope_kinds": scope_payload["scope_kinds"],
        "files": files,
        **receipt_payload,
    }


def fetch_receipt_payload(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    gates_payload = json.loads(str(row["gates_json"]))
    scope = scope_row(conn, Path(str(row["repo_root"])), str(row["issue_id"]), str(row["scope_fingerprint"]))
    files = json.loads(str(scope["files_json"])) if scope else []
    scope_kinds = json.loads(str(scope["scope_kind_json"])) if scope else []
    bindings = conn.execute(
        "SELECT commit_sha, bound_utc FROM commit_bindings WHERE receipt_id = ? ORDER BY bound_utc ASC",
        (str(row["receipt_id"]),),
    ).fetchall()
    approvals = conn.execute(
        """
        SELECT gate_name, decision, actor, role, evidence_ref, source, issued_utc
        FROM approval_events
        WHERE repo_root = ? AND issue_id = ? AND scope_fingerprint = ?
        ORDER BY issued_utc ASC
        """,
        (str(row["repo_root"]), str(row["issue_id"]), str(row["scope_fingerprint"])),
    ).fetchall()
    return {
        "receipt_id": str(row["receipt_id"]),
        "repo_root": str(row["repo_root"]),
        "issue_id": str(row["issue_id"]),
        "scope_fingerprint": str(row["scope_fingerprint"]),
        "stage": str(row["stage"]),
        "policy_version": str(row["policy_version"]),
        "status": str(row["status"]),
        "created_utc": str(row["created_utc"]),
        "updated_utc": str(row["updated_utc"]),
        "files": files,
        "scope_kinds": scope_kinds,
        "gates": gates_payload,
        "bindings": [dict(item) for item in bindings],
        "approvals": [dict(item) for item in approvals],
    }


def cmd_show_receipt(args: argparse.Namespace) -> dict[str, Any]:
    with connect_db() as conn:
        row: sqlite3.Row | None
        if args.receipt_id:
            row = receipt_row(conn, args.receipt_id.strip())
        else:
            commit_sha = normalize_commit_sha(resolve_repo_root(args.repo_root), args.commit)
            binding = conn.execute("SELECT receipt_id FROM commit_bindings WHERE commit_sha = ?", (commit_sha,)).fetchone()
            if binding is None:
                raise GatesCtlError("BINDING_MISMATCH", f"no bound receipt for commit {commit_sha}")
            row = receipt_row(conn, str(binding["receipt_id"]))
        if row is None:
            raise GatesCtlError("MISSING_RECEIPT", "receipt not found")
        return {"ok": True, **fetch_receipt_payload(conn, row)}


def cmd_trailers(args: argparse.Namespace) -> dict[str, Any]:
    with connect_db() as conn:
        row = receipt_row(conn, args.receipt_id.strip())
        if row is None:
            raise GatesCtlError("MISSING_RECEIPT", f"receipt not found: {args.receipt_id}")
        payload = {
            "ok": True,
            "receipt_id": str(row["receipt_id"]),
            "issue_id": str(row["issue_id"]),
            "policy_version": str(row["policy_version"]),
            "trailers": [
                f"Refs #{row['issue_id']}",
                f"Gate-Receipt: {row['receipt_id']}",
                f"Gate-Policy: {row['policy_version']}",
            ],
        }
        return payload


def cmd_bind_commit(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = resolve_repo_root(args.repo_root)
    commit_sha = normalize_commit_sha(repo_root, args.commit_sha)
    metadata = parse_commit_metadata(commit_message(repo_root, commit_sha))
    issue_id = (args.issue or metadata["issue_id"]).strip()
    receipt_id = (args.receipt_id or metadata["receipt_id"]).strip()
    repo_name = resolve_repo_name(repo_root, args.repo) if args.post_issue else ""
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = receipt_row(conn, receipt_id)
        if row is None:
            raise GatesCtlError("MISSING_RECEIPT", f"receipt not found: {receipt_id}")
        if str(row["issue_id"]) != issue_id:
            raise GatesCtlError("BINDING_MISMATCH", f"receipt {receipt_id} belongs to issue #{row['issue_id']}, not #{issue_id}")
        if str(row["policy_version"]) != metadata["policy_version"]:
            raise GatesCtlError("POLICY_INVALID", f"receipt policy `{row['policy_version']}` does not match commit trailer `{metadata['policy_version']}`")
        existing = conn.execute("SELECT receipt_id FROM commit_bindings WHERE commit_sha = ?", (commit_sha,)).fetchone()
        if existing and str(existing["receipt_id"]) != receipt_id:
            raise GatesCtlError("BINDING_MISMATCH", f"commit {commit_sha} already bound to receipt {existing['receipt_id']}")
        conn.execute(
            """
            INSERT OR IGNORE INTO commit_bindings (commit_sha, receipt_id, issue_id, repo_root, bound_utc)
            VALUES (?, ?, ?, ?, ?)
            """,
            (commit_sha, receipt_id, issue_id, str(repo_root), iso_utc(utc_now())),
        )
        emit_event(
            conn,
            "bind_commit",
            {"repo_root": str(repo_root), "issue_id": issue_id, "receipt_id": receipt_id, "commit_sha": commit_sha},
        )
        conn.commit()

    if args.post_issue:
        post_issue_comment(
            repo_root,
            repo_name,
            issue_id,
            receipt_comment_body({"issue_id": issue_id, "receipt_id": receipt_id, "commit_sha": commit_sha, "posted_utc": iso_utc(utc_now())}),
        )

    return {"ok": True, "repo_root": str(repo_root), "issue_id": issue_id, "receipt_id": receipt_id, "commit_sha": commit_sha, "posted_issue_comment": bool(args.post_issue)}


def cmd_audit_range(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = resolve_repo_root(args.repo_root)
    repo_name = resolve_repo_name(repo_root, args.repo)
    cp = _run(["git", "rev-list", "--reverse", args.range], cwd=repo_root)
    if cp.returncode != 0:
        raise GatesCtlError("GIT_FAILED", cp.stderr.strip() or f"invalid range: {args.range}")
    commits = [line.strip() for line in cp.stdout.splitlines() if line.strip()]
    failures: list[str] = []
    checked: list[dict[str, Any]] = []
    with connect_db() as conn:
        for commit_sha in commits:
            try:
                metadata = parse_commit_metadata(commit_message(repo_root, commit_sha))
                row = receipt_row(conn, metadata["receipt_id"])
                if row is None:
                    raise GatesCtlError("MISSING_RECEIPT", f"{commit_sha}: receipt {metadata['receipt_id']} not found")
                if str(row["issue_id"]) != metadata["issue_id"]:
                    raise GatesCtlError("BINDING_MISMATCH", f"{commit_sha}: receipt issue #{row['issue_id']} != trailer issue #{metadata['issue_id']}")
                if str(row["policy_version"]) != metadata["policy_version"]:
                    raise GatesCtlError("POLICY_INVALID", f"{commit_sha}: receipt policy `{row['policy_version']}` != trailer policy `{metadata['policy_version']}`")
                if str(row["status"]) != "ok":
                    raise GatesCtlError("STALE_RECEIPT", f"{commit_sha}: receipt {metadata['receipt_id']} status={row['status']}")
                binding = conn.execute("SELECT receipt_id FROM commit_bindings WHERE commit_sha = ?", (commit_sha,)).fetchone()
                if binding is None or str(binding["receipt_id"]) != metadata["receipt_id"]:
                    raise GatesCtlError("BINDING_MISMATCH", f"{commit_sha}: receipt {metadata['receipt_id']} is not bound to commit")
                if args.target_branch == "dev":
                    issue_state = check_issue_open(repo_root, repo_name, metadata["issue_id"])
                    if not issue_state["ok"]:
                        raise GatesCtlError("ISSUE_SYNC_FAILED", f"{commit_sha}: issue #{metadata['issue_id']} state={issue_state['state']}, expected OPEN")
                checked.append({"commit_sha": commit_sha, **metadata})
            except GatesCtlError as exc:
                failures.append(f"[{exc.code}] {exc.message}")
    if failures:
        raise GatesCtlError("AUDIT_FAILED", "\n".join(failures), payload={"errors": failures, "checked": checked})
    return {"ok": True, "repo_root": str(repo_root), "target_branch": args.target_branch, "range": args.range, "checked": checked}


def cmd_status(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = resolve_repo_root(args.repo_root) if args.repo_root else None
    with connect_db() as conn:
        where: list[str] = []
        params: list[Any] = []
        if repo_root is not None:
            where.append("repo_root = ?")
            params.append(str(repo_root))
        if args.issue:
            where.append("issue_id = ?")
            params.append(args.issue)
        if args.receipt_id:
            where.append("receipt_id = ?")
            params.append(args.receipt_id)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        receipts = conn.execute(
            f"SELECT * FROM receipts {clause} ORDER BY updated_utc DESC LIMIT 200",
            params,
        ).fetchall()
        payload_receipts: list[dict[str, Any]] = []
        for row in receipts:
            item = fetch_receipt_payload(conn, row)
            if args.gate and not any(gate.get("gate_name") == args.gate for gate in item["gates"]):
                continue
            if args.owner and not any(approval.get("actor") == args.owner for approval in item["approvals"]):
                continue
            if args.commit:
                commit_sha = normalize_commit_sha(Path(str(row["repo_root"])), args.commit)
                if not any(binding.get("commit_sha") == commit_sha for binding in item["bindings"]):
                    continue
            payload_receipts.append(item)
    return {"ok": True, "receipts": payload_receipts, "count": len(payload_receipts)}


def cmd_gc(args: argparse.Namespace) -> dict[str, Any]:
    cutoff_sync = iso_utc(utc_now() - timedelta(days=args.sync_ttl_days))
    cutoff_unbound = iso_utc(utc_now() - timedelta(days=args.unbound_ttl_days))
    with connect_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        sync_rows = conn.execute("SELECT issue_id, scope_fingerprint FROM issue_sync WHERE synced_utc < ?", (cutoff_sync,)).fetchall()
        conn.execute("DELETE FROM issue_sync WHERE synced_utc < ?", (cutoff_sync,))
        receipt_rows = conn.execute(
            """
            SELECT receipt_id FROM receipts
            WHERE updated_utc < ?
              AND receipt_id NOT IN (SELECT receipt_id FROM commit_bindings)
              AND status IN ('blocked', 'stale', 'superseded')
            """,
            (cutoff_unbound,),
        ).fetchall()
        if receipt_rows:
            conn.executemany("DELETE FROM receipts WHERE receipt_id = ?", [(str(row["receipt_id"]),) for row in receipt_rows])
        emit_event(
            conn,
            "gc",
            {
                "deleted_issue_sync": len(sync_rows),
                "deleted_receipts": len(receipt_rows),
                "sync_cutoff": cutoff_sync,
                "unbound_cutoff": cutoff_unbound,
            },
        )
        conn.commit()
    return {
        "ok": True,
        "deleted_issue_sync": len(sync_rows),
        "deleted_receipts": len(receipt_rows),
        "sync_cutoff": cutoff_sync,
        "unbound_cutoff": cutoff_unbound,
    }


def build_top_level_epilog() -> str:
    return textwrap.dedent(
        f"""
        Модель gate-runtime:
          - SQLite в {DB_PATH} — runtime truth для receipts, approvals и commit bindings
          - events.jsonl append-only и хранит историю событий для аудита
          - repo-specific policy читается из --policy-file или .agents/policy/gates.v1.yaml
          - `lockctl` используется только для file lease и не хранит gate/worklog state

        Ключевые аргументы:
          --repo-root     абсолютный корень git-репозитория
          --issue         числовой GitHub issue id
          --policy-file   путь к policy YAML
          --files         repo-relative file paths
          --stage         gate stage: commit, push, migration-apply, release-main

        Файлы рантайма:
          GATESCTL_STATE_DIR={STATE_DIR}
          sqlite={DB_PATH}
          events={EVENTS_PATH}

        Примеры:
          gatesctl plan-scope --repo-root /git/punctb --issue 1224 --files .agents/scripts/issue_commit.sh
          gatesctl verify --repo-root /git/punctb --issue 1224 --stage commit --files web/src/app/router/AppRouter.tsx
          gatesctl trailers --receipt-id gr_v1_deadbeefdeadbeef
          gatesctl bind-commit --repo-root /git/punctb --commit-sha HEAD
          gatesctl audit-range --repo-root /git/punctb --target-branch dev --range '@{{upstream}}..HEAD'

        Коды выхода:
          {EXIT_OK}  успех
          {EXIT_COMMAND_ERROR}  ошибка команды или валидации
        """
    ).strip()


def build_parser() -> tuple[argparse.ArgumentParser, dict[str, argparse.ArgumentParser]]:
    parser = RuArgumentParser(
        prog="gatesctl",
        description="Machine-wide runtime для gate receipts, approvals и commit binding.",
        epilog=build_top_level_epilog(),
        formatter_class=RuHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="КОМАНДА")
    commands: dict[str, argparse.ArgumentParser] = {}

    def add_command(name: str, **kwargs: Any) -> argparse.ArgumentParser:
        command = sub.add_parser(name, formatter_class=RuHelpFormatter, **kwargs)
        commands[name] = command
        return command

    def add_repo_issue_scope_flags(command: argparse.ArgumentParser, *, need_stage: bool = False) -> None:
        command.add_argument("--repo-root", help="Абсолютный корень репозитория.")
        command.add_argument("--issue", required=True, help="Числовой GitHub issue id.")
        command.add_argument("--policy-file", help="Путь к policy YAML.")
        command.add_argument("--repo", help="OWNER/REPO для gh-команд.")
        command.add_argument("--files", nargs="*", default=[], help="Список repo-relative путей.")
        command.add_argument("--files-csv", help="CSV со списком путей.")
        command.add_argument("--staged", action="store_true", help="Взять scope из staged files.")
        command.add_argument("--range", help="Взять scope из git range.")
        if need_stage:
            command.add_argument("--stage", required=True, choices=["commit", "push", "migration-apply", "release-main"])
        command.add_argument("--format", choices=("json", "text"), default="json", help="Формат вывода.")

    plan_scope = add_command("plan-scope", help="Рассчитать scope, fingerprint и required gates.")
    add_repo_issue_scope_flags(plan_scope)

    sync_issue = add_command("sync-issue", help="Синхронизировать approvals/labels/comments из GitHub Issue.")
    sync_issue.add_argument("--repo-root", help="Абсолютный корень репозитория.")
    sync_issue.add_argument("--issue", required=True, help="Числовой GitHub issue id.")
    sync_issue.add_argument("--scope-fingerprint", required=True, help="Scope fingerprint для нормализации approvals.")
    sync_issue.add_argument("--repo", help="OWNER/REPO для gh-команд.")
    sync_issue.add_argument("--format", choices=("json", "text"), default="json", help="Формат вывода.")

    approve = add_command("approve", help="Нормализовать gate approval/reject/waive в runtime state.")
    approve.add_argument("--repo-root", help="Абсолютный корень репозитория.")
    approve.add_argument("--issue", required=True, help="Числовой GitHub issue id.")
    approve.add_argument("--policy-file", help="Путь к policy YAML.")
    approve.add_argument("--repo", help="OWNER/REPO для gh-команд.")
    approve.add_argument("--gate", required=True, help="Имя gate.")
    approve.add_argument("--decision", required=True, choices=["approve", "reject", "waive"], help="Решение по gate.")
    approve.add_argument("--actor", help="Кто подтвердил gate.")
    approve.add_argument("--role", help="Роль апрувера.")
    approve.add_argument("--scope-fingerprint", help="Явный scope fingerprint.")
    approve.add_argument("--evidence-ref", help="Ссылка на evidence/artifact.")
    approve.add_argument("--source", default="cli", help="Источник approval event.")
    approve.add_argument("--post-issue", action="store_true", help="Опубликовать structured comment в GitHub Issue.")
    approve.add_argument("--files", nargs="*", default=[], help="Список repo-relative путей.")
    approve.add_argument("--files-csv", help="CSV со списком путей.")
    approve.add_argument("--staged", action="store_true", help="Взять scope из staged files.")
    approve.add_argument("--range", help="Взять scope из git range.")
    approve.add_argument("--format", choices=("json", "text"), default="json", help="Формат вывода.")

    verify = add_command("verify", help="Проверить gates и создать/обновить receipt.")
    add_repo_issue_scope_flags(verify, need_stage=True)
    verify.add_argument("--sync-issue", action="store_true", help="Перед verify подтянуть approvals из GitHub Issue.")

    show_receipt = add_command("show-receipt", help="Показать receipt по id или commit.")
    show_receipt.add_argument("--repo-root", help="Абсолютный корень репозитория.")
    show_receipt.add_argument("--receipt-id", help="Идентификатор receipt.")
    show_receipt.add_argument("--commit", help="Commit SHA/ref для поиска bound receipt.")
    show_receipt.add_argument("--format", choices=("json", "text"), default="json", help="Формат вывода.")

    trailers = add_command("trailers", help="Показать canonical commit trailers для receipt.")
    trailers.add_argument("--receipt-id", required=True, help="Идентификатор receipt.")
    trailers.add_argument("--format", choices=("json", "text"), default="text", help="Формат вывода.")

    bind_commit = add_command("bind-commit", help="Привязать receipt к конкретному commit.")
    bind_commit.add_argument("--repo-root", help="Абсолютный корень репозитория.")
    bind_commit.add_argument("--issue", help="Числовой GitHub issue id.")
    bind_commit.add_argument("--receipt-id", help="Идентификатор receipt; если не передан, берётся из commit trailers.")
    bind_commit.add_argument("--commit-sha", required=True, help="Commit SHA/ref.")
    bind_commit.add_argument("--repo", help="OWNER/REPO для gh-команд.")
    bind_commit.add_argument("--post-issue", action="store_true", help="Опубликовать structured receipt comment в Issue.")
    bind_commit.add_argument("--format", choices=("json", "text"), default="json", help="Формат вывода.")

    audit_range = add_command("audit-range", help="Проверить диапазон коммитов на валидные gate receipts.")
    audit_range.add_argument("--repo-root", help="Абсолютный корень репозитория.")
    audit_range.add_argument("--target-branch", required=True, choices=["dev", "main"], help="Целевая ветка.")
    audit_range.add_argument("--range", required=True, help="Git revision range.")
    audit_range.add_argument("--repo", help="OWNER/REPO для gh-команд.")
    audit_range.add_argument("--format", choices=("json", "text"), default="json", help="Формат вывода.")

    status = add_command("status", help="Показать receipts/bindings/approvals с фильтрами.")
    status.add_argument("--repo-root", help="Абсолютный корень репозитория.")
    status.add_argument("--issue", help="Фильтр по issue id.")
    status.add_argument("--receipt-id", help="Фильтр по receipt id.")
    status.add_argument("--commit", help="Фильтр по commit.")
    status.add_argument("--gate", help="Фильтр по gate name.")
    status.add_argument("--owner", help="Фильтр по actor approval event.")
    status.add_argument("--format", choices=("json", "text"), default="json", help="Формат вывода.")

    gc = add_command("gc", help="Удалить истёкший sync-cache и старые unbound receipts.")
    gc.add_argument("--sync-ttl-days", type=int, default=7, help="TTL issue_sync в днях.")
    gc.add_argument("--unbound-ttl-days", type=int, default=30, help="TTL unbound receipts в днях.")
    gc.add_argument("--format", choices=("json", "text"), default="json", help="Формат вывода.")

    help_cmd = add_command("help", help="Показать общую справку или справку по одной команде.", description="Показать общую справку или справку по одной команде.")
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


def render(payload: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        json_print(payload)
        return
    if "trailers" in payload and isinstance(payload["trailers"], list):
        print("\n".join(str(item) for item in payload["trailers"]))
        return
    print(json.dumps(payload, ensure_ascii=False, indent=2))


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
        if args.command == "plan-scope":
            payload = cmd_plan_scope(args)
        elif args.command == "sync-issue":
            payload = cmd_sync_issue(args)
        elif args.command == "approve":
            payload = cmd_approve(args)
        elif args.command == "verify":
            payload = cmd_verify(args)
        elif args.command == "show-receipt":
            if not args.receipt_id and not args.commit:
                raise GatesCtlError("MISSING_RECEIPT", "use --receipt-id or --commit")
            payload = cmd_show_receipt(args)
        elif args.command == "trailers":
            payload = cmd_trailers(args)
        elif args.command == "bind-commit":
            payload = cmd_bind_commit(args)
        elif args.command == "audit-range":
            payload = cmd_audit_range(args)
        elif args.command == "status":
            payload = cmd_status(args)
        elif args.command == "gc":
            payload = cmd_gc(args)
        else:
            raise GatesCtlError("UNKNOWN_COMMAND", f"unknown command: {args.command}")
        render(payload, getattr(args, "format", "json"))
        return EXIT_OK
    except GatesCtlError as exc:
        payload = {"ok": False, "error": exc.code, "message": exc.message, **exc.payload}
        render(payload, getattr(args, "format", "json"))
        return EXIT_COMMAND_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
