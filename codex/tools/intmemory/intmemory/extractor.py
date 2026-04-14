from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
import hashlib
import re

from .models import ExtractedMemoryItem, ParsedRecord, SessionBrief, SessionDigest, SessionMeta


TOKEN_RE = re.compile(r"(?i)\b(?:authorization|token|secret|api[_-]?key|agent[_-]?key)\b\s*[:=]\s*\S+")
BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-:=+/]+")
LONG_BLOB_RE = re.compile(r"\b[A-Za-z0-9_\-]{80,}\b")
WHITESPACE_RE = re.compile(r"\s+")
SIGNAL_LINE_RE = re.compile(
    r"(?i)(traceback|error|failed|success|created|deleted|changed|"
    r"warning|blocked|pid\s*`?\d+`?|exit code|http|\b[245]\d{2}\b|GET /|POST /|PATCH /|PUT /|DELETE /)"
)


def session_in_scope(cwd: str | None, scope_roots: Iterable[str]) -> bool:
    normalized = normalize_path(cwd)
    if not normalized:
        return False
    for root in scope_roots:
        candidate = normalize_path(root)
        if not candidate:
            continue
        if normalized == candidate or normalized.startswith(f"{candidate}/"):
            return True
    return False


def normalize_path(value: str | None) -> str | None:
    if not value:
        return None
    text = value.replace("\\", "/").strip()
    if len(text) >= 2 and text[1] == ":":
        text = text[0].upper() + text[1:]
    return text.rstrip("/") or None


def derive_repo(cwd: str | None) -> str | None:
    normalized = normalize_path(cwd)
    if not normalized:
        return None
    if normalized.startswith("D:/int/"):
        parts = normalized.split("/")
        return parts[2] if len(parts) > 2 else None
    if normalized.startswith("/int/"):
        parts = normalized.split("/")
        return parts[2] if len(parts) > 2 else None
    return None


def summarize_session(meta: SessionMeta, records: list[ParsedRecord], *, scope_roots: Iterable[str]) -> SessionBrief | None:
    digest = SessionDigest(
        session_id=meta.session_id,
        source_path=str(meta.source_path),
        timestamp=meta.timestamp,
        cwd=meta.cwd,
        repo=derive_repo(meta.cwd),
        thread_name=meta.thread_name,
    )
    for item in extract_items(meta, records, scope_roots=scope_roots):
        if item.chunk_kind == "summary":
            continue
        if item.kind == "task":
            digest.user_messages.append(item.text_content)
        elif item.chunk_kind in {"narrative", "summary"}:
            digest.assistant_messages.append(item.text_content)
        elif item.chunk_kind == "agent_note":
            digest.tool_items.append(item.text_content)
    if not (digest.user_messages or digest.assistant_messages or digest.tool_items):
        return None
    return SessionBrief(
        session_id=digest.session_id,
        path=digest.source_path,
        timestamp=digest.timestamp,
        cwd=digest.cwd,
        repo=digest.repo,
        thread_name=digest.thread_name,
        user_goal=digest.user_messages[0] if digest.user_messages else None,
        assistant_outcome=digest.assistant_messages[-1] if digest.assistant_messages else None,
        tool_highlights=digest.tool_items[:3],
    )


def extract_items(meta: SessionMeta, records: list[ParsedRecord], *, scope_roots: Iterable[str]) -> list[ExtractedMemoryItem]:
    if not session_in_scope(meta.cwd, scope_roots):
        return []
    repo = derive_repo(meta.cwd)
    output: list[ExtractedMemoryItem] = []
    digest = SessionDigest(
        session_id=meta.session_id,
        source_path=str(meta.source_path),
        timestamp=meta.timestamp,
        cwd=meta.cwd,
        repo=repo,
        thread_name=meta.thread_name,
    )
    for record in records:
        item = _extract_single(meta, record, repo=repo)
        if not item:
            continue
        output.append(item)
        if item.kind == "task":
            digest.user_messages.append(item.text_content)
        elif item.chunk_kind == "agent_note":
            digest.tool_items.append(item.text_content)
        else:
            digest.assistant_messages.append(item.text_content)
    summary = digest.build_summary()
    if summary:
        output.append(
            _build_item(
                meta=meta,
                repo=repo,
                line_no=records[-1].line_no if records else 1,
                byte_offset=records[-1].byte_offset if records else 0,
                title=_title_from_text("Session summary", summary),
                text_content=summary,
                kind="fact",
                chunk_kind="summary",
            )
        )
    return output


def _extract_single(meta: SessionMeta, record: ParsedRecord, *, repo: str | None) -> ExtractedMemoryItem | None:
    payload = record.data.get("payload") or {}
    record_type = str(record.data.get("type") or "")
    if record_type == "response_item":
        payload_type = str(payload.get("type") or "")
        if payload_type == "message":
            role = str(payload.get("role") or "")
            text = _message_text(payload.get("content") or [])
            if role == "user":
                text = _normalize_user_text(text)
                if not text:
                    return None
                return _build_item(
                    meta=meta,
                    repo=repo,
                    line_no=record.line_no,
                    byte_offset=record.byte_offset,
                    title=_title_from_text(meta.thread_name or "User task", text),
                    text_content=text,
                    kind="task",
                    chunk_kind="fact",
                )
            if role == "assistant":
                text = _normalize_assistant_text(text)
                if not text:
                    return None
                return _build_item(
                    meta=meta,
                    repo=repo,
                    line_no=record.line_no,
                    byte_offset=record.byte_offset,
                    title=_title_from_text("Assistant outcome", text),
                    text_content=text,
                    kind="fact",
                    chunk_kind="narrative",
                )
        if payload_type == "function_call_output":
            text = _summarize_tool_output(str(payload.get("output") or ""))
            if not text:
                return None
            return _build_item(
                meta=meta,
                repo=repo,
                line_no=record.line_no,
                byte_offset=record.byte_offset,
                title=_title_from_text("Tool result", text),
                text_content=text,
                kind="fact",
                chunk_kind="agent_note",
            )
    if record_type == "event_msg" and str(payload.get("type") or "") == "task_complete":
        text = _normalize_assistant_text(str(payload.get("last_agent_message") or ""))
        if not text:
            return None
        return _build_item(
            meta=meta,
            repo=repo,
            line_no=record.line_no,
            byte_offset=record.byte_offset,
            title=_title_from_text("Task complete", text),
            text_content=text,
            kind="fact",
            chunk_kind="summary",
        )
    return None


def _message_text(content: list[dict]) -> str:
    parts: list[str] = []
    for part in content:
        if str(part.get("type") or "") in {"input_text", "output_text"}:
            text = str(part.get("text") or "").strip()
            if text:
                parts.append(text)
    return "\n\n".join(parts).strip()


def _normalize_user_text(text: str) -> str | None:
    text = sanitize_text(text)
    if not text or len(text) < 20:
        return None
    lowered = text.lower()
    if lowered.startswith("<environment_context>") or lowered.startswith("# agents.md instructions") or lowered.startswith("<instructions>"):
        return None
    return truncate_text(text, 1800)


def _normalize_assistant_text(text: str) -> str | None:
    text = sanitize_text(text)
    if not text or len(text) < 80:
        return None
    lowered = text.lower()
    if lowered.startswith("starting on request") or lowered.startswith("update:"):
        return None
    return truncate_text(text, 1800)


def _summarize_tool_output(output: str) -> str | None:
    if not output.strip():
        return None
    exit_code = None
    match = re.search(r"Process exited with code\s+(-?\d+)", output)
    if match:
        exit_code = int(match.group(1))
    body = output
    marker = "Output:\n"
    if marker in output:
        body = output.split(marker, 1)[1]
    body = sanitize_text(body)
    if not body and exit_code in (None, 0):
        return None
    if not body and exit_code is not None:
        return f"Command finished with exit code {exit_code}."
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        return None
    if exit_code in (None, 0):
        if lines[0].lower().startswith("total output lines:"):
            lines = lines[1:]
        lines = [line for line in lines if "tokens truncated" not in line and len(line) <= 220]
        if not lines:
            return None
        signal_lines = [line for line in lines if SIGNAL_LINE_RE.search(line)]
        if signal_lines:
            lines = signal_lines
        else:
            return None
    text = "\n".join(lines[:6])
    if exit_code not in (None, 0):
        text = f"Command failed with exit code {exit_code}.\n{text}"
    return truncate_text(text, 1200)


def sanitize_text(text: str) -> str:
    cleaned = text.replace("\x00", " ").replace("\ufeff", "").strip()
    cleaned = TOKEN_RE.sub("[redacted-secret]", cleaned)
    cleaned = BEARER_RE.sub("Bearer [redacted]", cleaned)
    cleaned = LONG_BLOB_RE.sub("[redacted-blob]", cleaned)
    return cleaned.strip()


def truncate_text(text: str, limit: int) -> str:
    compact = text.strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1].rstrip()}…"


def _title_from_text(prefix: str, text: str) -> str:
    first_line = text.splitlines()[0].strip()
    compact = WHITESPACE_RE.sub(" ", first_line)
    if len(compact) > 90:
        compact = compact[:89].rstrip() + "…"
    if compact.lower().startswith(prefix.lower()):
        return compact
    return f"{prefix}: {compact}"


def _build_item(
    *,
    meta: SessionMeta,
    repo: str | None,
    line_no: int,
    byte_offset: int,
    title: str,
    text_content: str,
    kind: str,
    chunk_kind: str,
) -> ExtractedMemoryItem:
    timestamp = meta.timestamp or datetime.utcnow().isoformat() + "Z"
    tags = [
        "codex",
        "intmemory",
        f"session:{meta.session_id}",
        f"cwd:{normalize_path(meta.cwd) or 'unknown'}",
        f"week:{_iso_week(timestamp)}",
    ]
    if repo:
        tags.append(f"repo:{repo}")
    source_path = str(meta.source_path)
    normalized = "\n".join([title.strip(), text_content.strip(), source_path, str(line_no), str(byte_offset)])
    source_hash = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
    return ExtractedMemoryItem(
        session_id=meta.session_id,
        timestamp=timestamp,
        cwd=meta.cwd,
        repo=repo,
        title=title,
        text_content=text_content,
        kind=kind,
        chunk_kind=chunk_kind,
        source_path=source_path,
        source_hash=source_hash,
        tags=tags,
        line_no=line_no,
        byte_offset=byte_offset,
    )


def _iso_week(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        week = dt.isocalendar()
        return f"{week.year}-W{week.week:02d}"
    except ValueError:
        return "unknown"
