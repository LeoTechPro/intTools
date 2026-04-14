from __future__ import annotations

import json
from pathlib import Path


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = {
            "version": 1,
            "files": {},
            "hashes": {},
        }

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
        self.data["files"][str(source_path)] = {
            "offset": max(offset, 0),
            "size": max(size, 0),
            "scope": scope,
        }

    def has_hash(self, source_hash: str) -> bool:
        return source_hash in self.data["hashes"]

    def remember_hash(self, source_hash: str, *, source_path: str, session_id: str) -> None:
        self.data["hashes"][source_hash] = {
            "source_path": source_path,
            "session_id": session_id,
        }
