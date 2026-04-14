from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from typing import Iterator

from .models import ParsedRecord, SessionMeta


ROLLOUT_TS_RE = re.compile(r"rollout-(\d{4}-\d{2}-\d{2})T")


def iter_jsonl(path: Path, *, start_offset: int = 0) -> Iterator[ParsedRecord]:
    line_no = 0
    with path.open("rb") as handle:
        if start_offset > 0:
            handle.seek(start_offset)
        while True:
            byte_offset = handle.tell()
            raw = handle.readline()
            if not raw:
                break
            line_no += 1
            text = raw.decode("utf-8-sig", errors="replace").strip()
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            yield ParsedRecord(path=path, line_no=line_no, byte_offset=byte_offset, data=data)


def load_session_meta(path: Path, thread_name: str | None = None) -> SessionMeta | None:
    for record in iter_jsonl(path):
        if record.data.get("type") != "session_meta":
            continue
        payload = record.data.get("payload") or {}
        session_id = str(payload.get("id") or "").strip()
        if not session_id:
            return None
        return SessionMeta(
            session_id=session_id,
            timestamp=_clean_timestamp(payload.get("timestamp")),
            cwd=_clean_string(payload.get("cwd")),
            originator=_clean_string(payload.get("originator")),
            cli_version=_clean_string(payload.get("cli_version")),
            source_path=path,
            thread_name=thread_name,
        )
    return None


def load_session_index(codex_home: Path) -> dict[str, str]:
    index_path = codex_home / "session_index.jsonl"
    if not index_path.exists():
        return {}
    result: dict[str, str] = {}
    for record in iter_jsonl(index_path):
        session_id = str(record.data.get("id") or "").strip()
        thread_name = str(record.data.get("thread_name") or "").strip()
        if session_id and thread_name:
            result[session_id] = thread_name
    return result


def list_session_files(codex_home: Path) -> list[Path]:
    roots = [codex_home / "sessions", codex_home / "archived_sessions"]
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        if root.is_file() and root.suffix == ".jsonl":
            files.append(root)
            continue
        files.extend(path for path in root.rglob("*.jsonl") if path.is_file())
    return sorted(files, key=lambda item: str(item))


def find_session_file(codex_home: Path, session_id: str) -> Path | None:
    for path in list_session_files(codex_home):
        if session_id in path.name:
            return path
    return None


def parse_rollout_date(source_path: str | None) -> datetime | None:
    if not source_path:
        return None
    match = ROLLOUT_TS_RE.search(source_path)
    if not match:
        return None
    try:
        return datetime.fromisoformat(match.group(1)).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def iso_cutoff(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=max(days, 0))


def _clean_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_timestamp(value: object) -> str | None:
    text = _clean_string(value)
    if not text:
        return None
    return text
