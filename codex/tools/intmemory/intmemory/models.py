from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class ParsedRecord:
    path: Path
    line_no: int
    byte_offset: int
    data: dict


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
class ExtractedMemoryItem:
    session_id: str
    timestamp: str | None
    cwd: str | None
    repo: str | None
    title: str
    text_content: str
    kind: str
    chunk_kind: str
    source_path: str
    source_hash: str
    tags: list[str]
    line_no: int
    byte_offset: int


@dataclass(slots=True)
class SessionDigest:
    session_id: str
    source_path: str
    timestamp: str | None
    cwd: str | None
    repo: str | None
    thread_name: str | None
    user_messages: list[str] = field(default_factory=list)
    assistant_messages: list[str] = field(default_factory=list)
    tool_items: list[str] = field(default_factory=list)

    def build_summary(self) -> str | None:
        parts: list[str] = []
        if self.user_messages:
            parts.append(f"Task: {self.user_messages[0]}")
        if self.assistant_messages:
            parts.append(f"Outcome: {self.assistant_messages[-1]}")
        elif self.tool_items:
            parts.append(f"Observed: {self.tool_items[-1]}")
        if not parts:
            return None
        return "\n".join(parts)


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
class SearchResult:
    id: int | None
    title: str
    text_content: str
    source_path: str | None
    source_hash: str | None
    chunk_kind: str | None
    tags: list[str]
    rank: float | None
    repo: str | None
    session_id: str | None
    timestamp: datetime | None
