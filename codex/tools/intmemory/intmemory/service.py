from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import IntBrainClient
from .config import IntMemoryConfig
from .extractor import session_in_scope, summarize_session, extract_items
from .models import SearchResult, SessionBrief
from .parser import (
    find_session_file,
    iso_cutoff,
    iter_jsonl,
    list_session_files,
    load_session_index,
    load_session_meta,
    parse_rollout_date,
)
from .state import StateStore


class IntMemoryService:
    def __init__(self, config: IntMemoryConfig) -> None:
        self.config = config
        self.state = StateStore(config.state_path)
        self.state.load()
        self.client = IntBrainClient(config)
        self.session_index = load_session_index(config.codex_home)
        self._remote_hash_cache: set[str] = set()

    def sync(
        self,
        *,
        incremental: bool = True,
        since: str | None = None,
        file_path: str | None = None,
        dry_run: bool = False,
        owner_id: int | None = None,
    ) -> dict[str, Any]:
        owner = owner_id if owner_id is not None else self.config.owner_id
        if not dry_run and owner is None:
            raise RuntimeError("INTMEMORY_OWNER_ID is required for live sync")
        paths = [Path(file_path).expanduser()] if file_path else list_session_files(self.config.codex_home)
        since_dt = _parse_since(since)
        summary = {
            "files_seen": 0,
            "files_processed": 0,
            "items_extracted": 0,
            "items_stored": 0,
            "items_skipped_dedup": 0,
            "files_skipped_scope": 0,
            "files_skipped_since": 0,
            "dry_run": dry_run,
            "source": self.config.source_name,
        }
        for path in paths:
            summary["files_seen"] += 1
            meta = load_session_meta(path)
            if meta is None:
                continue
            meta.thread_name = self.session_index.get(meta.session_id)
            if since_dt and meta.timestamp:
                try:
                    meta_dt = datetime.fromisoformat(meta.timestamp.replace("Z", "+00:00"))
                except ValueError:
                    meta_dt = None
                if meta_dt and meta_dt < since_dt:
                    summary["files_skipped_since"] += 1
                    continue
            file_size = path.stat().st_size
            start_offset = self.state.get_offset(path) if incremental and not file_path and since_dt is None else 0
            if start_offset > file_size:
                start_offset = 0
            if not session_in_scope(meta.cwd, self.config.scope_roots):
                if not dry_run:
                    self.state.set_offset(path, offset=file_size, size=file_size, scope="out_of_scope")
                summary["files_skipped_scope"] += 1
                continue
            records = list(iter_jsonl(path, start_offset=start_offset))
            if not records and start_offset == file_size:
                continue
            items = extract_items(meta, records, scope_roots=self.config.scope_roots)
            summary["files_processed"] += 1
            summary["items_extracted"] += len(items)
            for item in items:
                if self.state.has_hash(item.source_hash):
                    summary["items_skipped_dedup"] += 1
                    continue
                if not dry_run and self._exists_in_remote_store(owner=owner, item=item):
                    self.state.remember_hash(item.source_hash, source_path=item.source_path, session_id=item.session_id)
                    summary["items_skipped_dedup"] += 1
                    continue
                payload = {
                    "owner_id": owner,
                    "kind": item.kind,
                    "title": item.title,
                    "text_content": item.text_content,
                    "source_path": item.source_path,
                    "source_hash": item.source_hash,
                    "chunk_kind": item.chunk_kind,
                    "tags": item.tags,
                    "source": self.config.source_name,
                    "priority": 3,
                }
                if not dry_run:
                    self.client.store_context(payload)
                    self.state.remember_hash(item.source_hash, source_path=item.source_path, session_id=item.session_id)
                summary["items_stored"] += 1
            if not dry_run:
                self.state.set_offset(path, offset=file_size, size=file_size, scope="in_scope")
        if not dry_run:
            self.state.save()
        return summary

    def search(
        self,
        *,
        query: str,
        limit: int = 10,
        days: int | None = None,
        repo: str | None = None,
        owner_id: int | None = None,
    ) -> dict[str, Any]:
        owner = owner_id if owner_id is not None else self.config.owner_id
        if owner is None:
            raise RuntimeError("INTMEMORY_OWNER_ID is required for search")
        raw = self.client.retrieve_context({"owner_id": owner, "query": query, "limit": max(limit * 3, limit)})
        cutoff = iso_cutoff(days) if days else None
        repo_norm = (repo or "").strip().lower() or None
        items: list[dict[str, Any]] = []
        for entry in raw.get("items") or []:
            result = _to_search_result(entry)
            if repo_norm and result.repo != repo_norm:
                continue
            if cutoff and result.timestamp and result.timestamp < cutoff:
                continue
            items.append(
                {
                    "id": result.id,
                    "title": result.title,
                    "text_content": result.text_content,
                    "source_path": result.source_path,
                    "chunk_kind": result.chunk_kind,
                    "tags": result.tags,
                    "rank": result.rank,
                    "repo": result.repo,
                    "session_id": result.session_id,
                    "timestamp": result.timestamp.isoformat() if result.timestamp else None,
                }
            )
            if len(items) >= limit:
                break
        return {"query": query, "count": len(items), "items": items}

    def recent_work(self, *, days: int = 7, limit: int = 10, repo: str | None = None) -> dict[str, Any]:
        cutoff = iso_cutoff(days)
        repo_norm = (repo or "").strip().lower() or None
        briefs: list[dict[str, Any]] = []
        for path in reversed(list_session_files(self.config.codex_home)):
            meta = load_session_meta(path)
            if meta is None or not session_in_scope(meta.cwd, self.config.scope_roots):
                continue
            meta.thread_name = self.session_index.get(meta.session_id)
            if meta.timestamp:
                try:
                    meta_dt = datetime.fromisoformat(meta.timestamp.replace("Z", "+00:00"))
                except ValueError:
                    meta_dt = None
                if meta_dt and meta_dt < cutoff:
                    continue
            brief = self.session_brief(session_id=meta.session_id, session_path=path, repo=repo_norm)
            if brief is None:
                continue
            briefs.append(asdict(brief))
            if len(briefs) >= limit:
                break
        return {"days": days, "count": len(briefs), "items": briefs}

    def session_brief(self, *, session_id: str, session_path: Path | None = None, repo: str | None = None) -> SessionBrief | None:
        path = session_path or find_session_file(self.config.codex_home, session_id)
        if path is None:
            return None
        meta = load_session_meta(path, thread_name=self.session_index.get(session_id))
        if meta is None or not session_in_scope(meta.cwd, self.config.scope_roots):
            return None
        brief = summarize_session(meta, list(iter_jsonl(path)), scope_roots=self.config.scope_roots)
        if brief is None:
            return None
        if repo and (brief.repo or "").lower() != repo.lower():
            return None
        return brief

    def _exists_in_remote_store(self, *, owner: int, item: Any) -> bool:
        if item.source_hash in self._remote_hash_cache:
            return True
        query = item.title[:512].strip() or item.text_content[:512].strip()
        if not query:
            return False
        try:
            raw = self.client.retrieve_context({"owner_id": owner, "query": query, "limit": 10})
        except Exception:
            return False
        for entry in raw.get("items") or []:
            source_hash = str(entry.get("source_hash") or "").strip()
            if source_hash:
                self._remote_hash_cache.add(source_hash)
            if source_hash == item.source_hash:
                return True
        return False


def _parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _to_search_result(entry: dict[str, Any]) -> SearchResult:
    tags = [str(item) for item in entry.get("tags") or []]
    repo = None
    session_id = None
    for tag in tags:
        if tag.startswith("repo:"):
            repo = tag.split(":", 1)[1].strip().lower()
        if tag.startswith("session:"):
            session_id = tag.split(":", 1)[1].strip()
    source_path = entry.get("source_path")
    timestamp = parse_rollout_date(str(source_path) if source_path else None)
    return SearchResult(
        id=int(entry["id"]) if entry.get("id") is not None else None,
        title=str(entry.get("title") or ""),
        text_content=str(entry.get("text_content") or ""),
        source_path=str(source_path) if source_path else None,
        source_hash=str(entry.get("source_hash") or "") or None,
        chunk_kind=str(entry.get("chunk_kind") or "") or None,
        tags=tags,
        rank=float(entry["rank"]) if entry.get("rank") is not None else None,
        repo=repo,
        session_id=session_id,
        timestamp=timestamp,
    )
