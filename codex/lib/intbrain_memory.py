from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Iterator


SESSION_SOURCE = "intbrain.memory.session.v1"
MEMPALACE_SOURCE = "intbrain.memory.mempalace.v1"
CABINET_WORKSPACE_SOURCE = "intbrain.cabinet.workspace.v1"
CABINET_RUNTIME_SOURCE = "intbrain.cabinet.runtime.v1"
DEFAULT_SCOPE_ROOTS = ("D:/int", "/int")
TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".ts", ".tsx", ".js", ".jsx", ".cjs", ".mjs"}
IGNORED_DIRS = {".git", ".next", ".venv", "node_modules", "dist", "build", "out", "coverage"}

TOKEN_RE = re.compile(r"(?i)\b(?:authorization|token|secret|api[_-]?key|agent[_-]?key)\b\s*[:=]\s*\S+")
BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-:=+/]+")
LONG_BLOB_RE = re.compile(r"\b[A-Za-z0-9_\-]{80,}\b")
WHITESPACE_RE = re.compile(r"\s+")
ROLLOUT_TS_RE = re.compile(r"rollout-(\d{4}-\d{2}-\d{2})T")
SIGNAL_LINE_RE = re.compile(
    r"(?i)(traceback|error|failed|success|created|deleted|changed|"
    r"warning|blocked|pid\s*`?\d+`?|exit code|http|\b[245]\d{2}\b|GET /|POST /|PATCH /|PUT /|DELETE /)"
)


@dataclass(slots=True)
class ParsedRecord:
    path: Path
    line_no: int
    byte_offset: int
    data: dict[str, Any]


@dataclass(slots=True)
class SessionMeta:
    session_id: str
    timestamp: str | None
    cwd: str | None
    originator: str | None
    cli_version: str | None
    source_path: Path
    thread_name: str | None = None


@dataclass(slots=True)
class MemoryItem:
    title: str
    text_content: str
    kind: str
    chunk_kind: str
    source: str
    source_path: str
    source_hash: str
    tags: list[str]
    priority: int = 3
    session_id: str | None = None
    timestamp: str | None = None
    cwd: str | None = None
    repo: str | None = None
    line_no: int | None = None
    byte_offset: int | None = None

    def context_payload(self, owner_id: int) -> dict[str, Any]:
        return {
            "owner_id": owner_id,
            "kind": self.kind,
            "title": self.title,
            "text_content": self.text_content,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "chunk_kind": self.chunk_kind,
            "tags": self.tags,
            "source": self.source,
            "priority": self.priority,
        }


@dataclass(slots=True)
class SessionBrief:
    session_id: str
    path: str
    timestamp: str | None
    cwd: str | None
    repo: str | None
    thread_name: str | None
    user_goal: str | None
    assistant_outcome: str | None
    tool_highlights: list[str]


@dataclass(slots=True)
class _SessionDigest:
    session_id: str
    source_path: str
    timestamp: str | None
    cwd: str | None
    repo: str | None
    thread_name: str | None
    user_messages: list[str] = field(default_factory=list)
    assistant_messages: list[str] = field(default_factory=list)
    tool_items: list[str] = field(default_factory=list)

    def summary(self) -> str | None:
        parts: list[str] = []
        if self.user_messages:
            parts.append(f"Task: {self.user_messages[0]}")
        if self.assistant_messages:
            parts.append(f"Outcome: {self.assistant_messages[-1]}")
        elif self.tool_items:
            parts.append(f"Observed: {self.tool_items[-1]}")
        return "\n".join(parts) if parts else None


class IntBrainMemory:
    def __init__(
        self,
        *,
        codex_home: str | Path | None = None,
        state_path: str | Path | None = None,
        scope_roots: Iterable[str] = DEFAULT_SCOPE_ROOTS,
    ) -> None:
        home = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
        self.codex_home = home
        self.state_path = Path(state_path).expanduser() if state_path else home / "memories" / "intbrain-memory" / "state.json"
        self.scope_roots = tuple(scope_roots)
        self.state = _StateStore(self.state_path)
        self.state.load()
        self.session_index = load_session_index(home)

    def extract_session_items(self, *, file_path: str | Path | None = None, since: str | None = None, incremental: bool = True) -> dict[str, Any]:
        paths = [Path(file_path).expanduser()] if file_path else list_session_files(self.codex_home)
        since_dt = parse_since(since)
        summary = _empty_summary(source=SESSION_SOURCE)
        items: list[MemoryItem] = []
        for path in paths:
            summary["files_seen"] += 1
            meta = load_session_meta(path)
            if meta is None:
                continue
            meta.thread_name = self.session_index.get(meta.session_id)
            if since_dt and meta.timestamp:
                meta_dt = _timestamp_to_dt(meta.timestamp)
                if meta_dt and meta_dt < since_dt:
                    summary["files_skipped_since"] += 1
                    continue
            file_size = path.stat().st_size if path.exists() else 0
            start_offset = self.state.get_offset(path) if incremental and not file_path and not since_dt else 0
            if start_offset > file_size:
                start_offset = 0
            if not session_in_scope(meta.cwd, self.scope_roots):
                self.state.set_offset(path, offset=file_size, size=file_size, scope="out_of_scope")
                summary["files_skipped_scope"] += 1
                continue
            records = list(iter_jsonl(path, start_offset=start_offset))
            if not records and start_offset == file_size:
                continue
            extracted = extract_items(meta, records, scope_roots=self.scope_roots)
            summary["files_processed"] += 1
            summary["items_extracted"] += len(extracted)
            for item in extracted:
                if self.state.has_hash(item.source_hash):
                    summary["items_skipped_dedup"] += 1
                    continue
                items.append(item)
            self.state.set_offset(path, offset=file_size, size=file_size, scope="in_scope")
        summary["items"] = [asdict(item) for item in items]
        summary["items_candidate"] = len(items)
        return summary

    def mark_stored(self, items: Iterable[MemoryItem | dict[str, Any]]) -> None:
        for item in items:
            if isinstance(item, dict):
                source_hash = str(item.get("source_hash") or "")
                source_path = str(item.get("source_path") or "")
                session_id = str(item.get("session_id") or "")
            else:
                source_hash = item.source_hash
                source_path = item.source_path
                session_id = item.session_id or ""
            if source_hash:
                self.state.remember_hash(source_hash, source_path=source_path, session_id=session_id)
        self.state.save()

    def recent_work(self, *, days: int = 7, limit: int = 10, repo: str | None = None) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(days, 0))
        repo_norm = (repo or "").strip().lower() or None
        briefs: list[dict[str, Any]] = []
        for path in reversed(list_session_files(self.codex_home)):
            meta = load_session_meta(path)
            if meta is None or not session_in_scope(meta.cwd, self.scope_roots):
                continue
            meta.thread_name = self.session_index.get(meta.session_id)
            meta_dt = _timestamp_to_dt(meta.timestamp)
            if meta_dt and meta_dt < cutoff:
                continue
            brief = self.session_brief(session_id=meta.session_id, session_path=path, repo=repo_norm)
            if brief:
                briefs.append(asdict(brief))
            if len(briefs) >= limit:
                break
        return {"days": days, "count": len(briefs), "items": briefs}

    def session_brief(self, *, session_id: str, session_path: str | Path | None = None, repo: str | None = None) -> SessionBrief | None:
        path = Path(session_path) if session_path else find_session_file(self.codex_home, session_id)
        if path is None:
            return None
        meta = load_session_meta(path, thread_name=self.session_index.get(session_id))
        if meta is None or not session_in_scope(meta.cwd, self.scope_roots):
            return None
        brief = summarize_session(meta, list(iter_jsonl(path)), scope_roots=self.scope_roots)
        if repo and brief and (brief.repo or "").lower() != repo.lower():
            return None
        return brief

    def import_mempalace(self, *, palace_root: str | Path, limit: int | None = None) -> dict[str, Any]:
        root = Path(palace_root).expanduser()
        summary = _empty_summary(source=MEMPALACE_SOURCE)
        items: list[MemoryItem] = []
        if not root.exists():
            summary["missing_root"] = str(root)
            summary["items"] = []
            summary["items_candidate"] = 0
            return summary
        for path in sorted(root.rglob("*")):
            if limit is not None and len(items) >= max(limit, 0):
                break
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml"}:
                continue
            summary["files_seen"] += 1
            text = _read_memory_file(path)
            if not text:
                continue
            item = _mempalace_item(root=root, path=path, text=text)
            if self.state.has_hash(item.source_hash):
                summary["items_skipped_dedup"] += 1
                continue
            summary["files_processed"] += 1
            summary["items_extracted"] += 1
            items.append(item)
        summary["items"] = [asdict(item) for item in items]
        summary["items_candidate"] = len(items)
        return summary

    def inventory_cabinet(self, *, cabinet_root: str | Path, limit: int | None = None) -> dict[str, Any]:
        root = Path(cabinet_root).expanduser()
        summary = _empty_summary(source=CABINET_WORKSPACE_SOURCE)
        summary.update(
            {
                "cabinet_root": str(root),
                "data_roots": {},
                "runtime_roots": {},
                "ignored_dirs": sorted(IGNORED_DIRS),
            }
        )
        items: list[MemoryItem] = []
        if not root.exists():
            summary["missing_root"] = str(root)
            summary["items"] = []
            summary["items_candidate"] = 0
            return summary
        for name in ("data", "server", "cabinetai", "cli"):
            candidate = root / name
            if candidate.exists():
                summary["data_roots"][name] = _count_tree(candidate)
        for name in (".git", ".next", ".venv", "node_modules"):
            candidate = root / name
            if candidate.exists():
                summary["runtime_roots"][name] = _count_tree(candidate)
        for path in _iter_cabinet_source_files(root):
            if limit is not None and len(items) >= max(limit, 0):
                break
            summary["files_seen"] += 1
            text = _read_memory_file(path)
            if not text:
                continue
            item = _cabinet_item(root=root, path=path, text=text)
            if self.state.has_hash(item.source_hash):
                summary["items_skipped_dedup"] += 1
                continue
            summary["files_processed"] += 1
            summary["items_extracted"] += 1
            items.append(item)
        summary["items"] = [asdict(item) for item in items]
        summary["items_candidate"] = len(items)
        return summary

    def import_cabinet(self, *, cabinet_root: str | Path, limit: int | None = None) -> dict[str, Any]:
        return self.inventory_cabinet(cabinet_root=cabinet_root, limit=limit)


def _empty_summary(*, source: str) -> dict[str, Any]:
    return {
        "files_seen": 0,
        "files_processed": 0,
        "items_extracted": 0,
        "items_skipped_dedup": 0,
        "files_skipped_scope": 0,
        "files_skipped_since": 0,
        "source": source,
    }


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
            timestamp=_clean_string(payload.get("timestamp")),
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
    files: list[Path] = []
    for root in (codex_home / "sessions", codex_home / "archived_sessions"):
        if root.is_file() and root.suffix == ".jsonl":
            files.append(root)
        elif root.exists():
            files.extend(path for path in root.rglob("*.jsonl") if path.is_file())
    return sorted(files, key=lambda item: str(item))


def find_session_file(codex_home: Path, session_id: str) -> Path | None:
    for path in list_session_files(codex_home):
        if session_id in path.name:
            return path
    return None


def parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def session_in_scope(cwd: str | None, scope_roots: Iterable[str]) -> bool:
    normalized = normalize_path(cwd)
    if not normalized:
        return False
    for root in scope_roots:
        candidate = normalize_path(root)
        if candidate and (normalized == candidate or normalized.startswith(f"{candidate}/")):
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
    digest = _SessionDigest(
        session_id=meta.session_id,
        source_path=str(meta.source_path),
        timestamp=meta.timestamp,
        cwd=meta.cwd,
        repo=derive_repo(meta.cwd),
        thread_name=meta.thread_name,
    )
    for item in extract_items(meta, records, scope_roots=scope_roots):
        if item.kind == "task":
            digest.user_messages.append(item.text_content)
        elif item.chunk_kind == "agent_note":
            digest.tool_items.append(item.text_content)
        elif item.chunk_kind != "summary":
            digest.assistant_messages.append(item.text_content)
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


def extract_items(meta: SessionMeta, records: list[ParsedRecord], *, scope_roots: Iterable[str]) -> list[MemoryItem]:
    if not session_in_scope(meta.cwd, scope_roots):
        return []
    repo = derive_repo(meta.cwd)
    output: list[MemoryItem] = []
    digest = _SessionDigest(
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
    summary = digest.summary()
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
    return f"{compact[: limit - 1].rstrip()}..."


def _extract_single(meta: SessionMeta, record: ParsedRecord, *, repo: str | None) -> MemoryItem | None:
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
                return _build_item(meta=meta, repo=repo, line_no=record.line_no, byte_offset=record.byte_offset, title=_title_from_text(meta.thread_name or "User task", text), text_content=text, kind="task", chunk_kind="fact")
            if role == "assistant":
                text = _normalize_assistant_text(text)
                if not text:
                    return None
                return _build_item(meta=meta, repo=repo, line_no=record.line_no, byte_offset=record.byte_offset, title=_title_from_text("Assistant outcome", text), text_content=text, kind="fact", chunk_kind="narrative")
        if payload_type == "function_call_output":
            text = _summarize_tool_output(str(payload.get("output") or ""))
            if not text:
                return None
            return _build_item(meta=meta, repo=repo, line_no=record.line_no, byte_offset=record.byte_offset, title=_title_from_text("Tool result", text), text_content=text, kind="fact", chunk_kind="agent_note")
    if record_type == "event_msg" and str(payload.get("type") or "") == "task_complete":
        text = _normalize_assistant_text(str(payload.get("last_agent_message") or ""))
        if not text:
            return None
        return _build_item(meta=meta, repo=repo, line_no=record.line_no, byte_offset=record.byte_offset, title=_title_from_text("Task complete", text), text_content=text, kind="fact", chunk_kind="summary")
    return None


def _message_text(content: list[dict[str, Any]]) -> str:
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
    body = output.split("Output:\n", 1)[1] if "Output:\n" in output else output
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


def _build_item(*, meta: SessionMeta, repo: str | None, line_no: int, byte_offset: int, title: str, text_content: str, kind: str, chunk_kind: str) -> MemoryItem:
    timestamp = meta.timestamp or datetime.now(timezone.utc).isoformat()
    tags = ["codex", "intbrain-memory", f"session:{meta.session_id}", f"cwd:{normalize_path(meta.cwd) or 'unknown'}", f"week:{_iso_week(timestamp)}"]
    if repo:
        tags.append(f"repo:{repo}")
    source_path = str(meta.source_path)
    normalized = "\n".join([title.strip(), text_content.strip(), source_path, str(line_no), str(byte_offset)])
    return MemoryItem(
        session_id=meta.session_id,
        timestamp=timestamp,
        cwd=meta.cwd,
        repo=repo,
        title=title,
        text_content=text_content,
        kind=kind,
        chunk_kind=chunk_kind,
        source=SESSION_SOURCE,
        source_path=source_path,
        source_hash=hashlib.sha1(normalized.encode("utf-8")).hexdigest(),
        tags=tags,
        line_no=line_no,
        byte_offset=byte_offset,
    )


def _mempalace_item(*, root: Path, path: Path, text: str) -> MemoryItem:
    rel = str(path.relative_to(root)).replace("\\", "/")
    title = _title_from_text("MemPalace import", rel)
    content = truncate_text(sanitize_text(text), 4000)
    normalized = "\n".join([title, content, str(path)])
    return MemoryItem(
        title=title,
        text_content=content,
        kind="fact",
        chunk_kind="mempalace_import",
        source=MEMPALACE_SOURCE,
        source_path=str(path),
        source_hash=hashlib.sha1(normalized.encode("utf-8")).hexdigest(),
        tags=["mempalace", "intbrain-memory", f"path:{rel}"],
    )


def _cabinet_item(*, root: Path, path: Path, text: str) -> MemoryItem:
    rel = str(path.relative_to(root)).replace("\\", "/")
    source = CABINET_RUNTIME_SOURCE if rel.startswith(("server/", "data/.cabinet")) else CABINET_WORKSPACE_SOURCE
    title = _title_from_text("Cabinet import", rel)
    content = truncate_text(sanitize_text(text), 4000)
    normalized = "\n".join([title, content, str(path)])
    tags = ["cabinet", "intbrain-cabinet", f"path:{rel}"]
    if rel.startswith("data/"):
        tags.append("cabinet:data")
    if rel.startswith("server/"):
        tags.append("cabinet:runtime")
    return MemoryItem(
        title=title,
        text_content=content,
        kind="fact",
        chunk_kind="cabinet_import",
        source=source,
        source_path=str(path),
        source_hash=hashlib.sha1(normalized.encode("utf-8")).hexdigest(),
        tags=tags,
    )


def _iter_cabinet_source_files(root: Path) -> Iterator[Path]:
    priority_names = {
        "README.md",
        "PRD.md",
        "CABINETAI.md",
        "PROGRESS.md",
        "cabinet-release.json",
        "package.json",
    }
    for path in sorted(root.rglob("*")):
        rel_parts = set(path.relative_to(root).parts)
        if rel_parts & IGNORED_DIRS:
            continue
        if not path.is_file():
            continue
        if path.name in priority_names or path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def _count_tree(root: Path) -> dict[str, int]:
    files = 0
    dirs = 0
    for path in root.rglob("*"):
        if path.is_dir():
            dirs += 1
        elif path.is_file():
            files += 1
    return {"files": files, "dirs": dirs}


def _read_memory_file(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    text = text.strip()
    if not text:
        return None
    if path.suffix.lower() in {".json", ".jsonl"}:
        return _jsonish_text(text)
    return truncate_text(text, 4000)


def _jsonish_text(text: str) -> str:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _title_from_text(prefix: str, text: str) -> str:
    first_line = text.splitlines()[0].strip()
    compact = WHITESPACE_RE.sub(" ", first_line)
    if len(compact) > 90:
        compact = compact[:89].rstrip() + "..."
    if compact.lower().startswith(prefix.lower()):
        return compact
    return f"{prefix}: {compact}"


def _iso_week(value: str) -> str:
    dt = _timestamp_to_dt(value)
    if not dt:
        return "unknown"
    week = dt.isocalendar()
    return f"{week.year}-W{week.week:02d}"


def _timestamp_to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _clean_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class _StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = {"version": 1, "files": {}, "hashes": {}}

    def load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            self.data["version"] = int(raw.get("version") or 1)
            self.data["files"] = dict(raw.get("files") or {})
            self.data["hashes"] = dict(raw.get("hashes") or {})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(self.path)

    def get_offset(self, source_path: Path) -> int:
        record = self.data["files"].get(str(source_path)) or {}
        return int(record.get("offset") or 0)

    def set_offset(self, source_path: Path, *, offset: int, size: int, scope: str) -> None:
        self.data["files"][str(source_path)] = {"offset": max(offset, 0), "size": max(size, 0), "scope": scope}

    def has_hash(self, source_hash: str) -> bool:
        return source_hash in self.data["hashes"]

    def remember_hash(self, source_hash: str, *, source_path: str, session_id: str) -> None:
        self.data["hashes"][source_hash] = {"source_path": source_path, "session_id": session_id}
